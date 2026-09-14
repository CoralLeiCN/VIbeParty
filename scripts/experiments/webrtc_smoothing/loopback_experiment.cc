// Local H.264 or VP8 / RTP / WebRTC experiment using Reactor's C++ adapter.
// No Reactor account, server, model, camera, microphone, or paid session is used.
#include "reactor_webrtc.cpp"
#include <atomic>
#include <chrono>
#include <deque>
#include <future>
#include <iostream>
#include <stdexcept>
#include <thread>

using namespace std::chrono_literals;

struct Ice { std::string mid; int line; std::string candidate; };
struct Peer {
  std::mutex mutex;
  std::deque<Ice> ice;
  std::vector<void*> tracks;
  std::vector<int> ids;
  std::atomic<bool> connected{false};
  int stall_ms = 0;
  int invalid_markers = 0;
  int stalls = 0;
  void* pc = nullptr;
};

void Frames(void* userdata, const uint8_t* bgra, int width, int height) {
  auto& peer = *static_cast<Peer*>(userdata);
  int id = 0;
  for (int bit = 0; bit < 8; ++bit) {
    int x = (2 * bit + 1) * width / 16;
    if (bgra[(height / 2 * width + x) * 4] > 128) id |= 1 << bit;
  }
  size_t count;
  {
    std::lock_guard lock(peer.mutex);
    peer.ids.push_back(id);
    if (id < 1 || id > 158) ++peer.invalid_markers;
    count = peer.ids.size();
  }
  // Controlled slow native sink; independent of networking and the sender.
  if (peer.stall_ms && count % 24 == 0) {
    ++peer.stalls;
    std::this_thread::sleep_for(std::chrono::milliseconds(peer.stall_ms));
  }
}

void* MakePeer(void* factory, Peer& peer, bool smoothing) {
  auto* rf = static_cast<ReactorFactory*>(factory);
  ReactorPcCallbacks callbacks{};
  callbacks.userdata = &peer;
  callbacks.on_connection_change = [](void* p, int state) {
    static_cast<Peer*>(p)->connected = state == 2;
  };
  callbacks.on_ice_candidate = [](void* p, const char* mid, int line, const char* candidate) {
    auto& state = *static_cast<Peer*>(p);
    std::lock_guard lock(state.mutex);
    state.ice.push_back({mid ? mid : "", line, candidate ? candidate : ""});
  };
  callbacks.on_track = [](void* p, void* track) {
    auto& state = *static_cast<Peer*>(p);
    reactor_webrtc_video_track_add_sink(track, p, Frames);
    std::lock_guard lock(state.mutex);
    state.tracks.push_back(track);
  };

  // Same construction as Reactor's adapter, with an explicit experimental
  // smoothing setting. CPU adaptation is disabled equally in both arms.
  auto rpc = std::make_unique<ReactorPeerConnection>();
  rpc->factory = rf->factory;
  rpc->observer = std::make_unique<ReactorPcObserver>(callbacks);
  webrtc::PeerConnectionInterface::RTCConfiguration config;
  config.sdp_semantics = webrtc::SdpSemantics::kUnifiedPlan;
  config.set_cpu_adaptation(false);
  config.set_prerenderer_smoothing(smoothing);
  webrtc::PeerConnectionDependencies dependencies(rpc->observer.get());
  auto result = rf->factory->CreatePeerConnectionOrError(config, std::move(dependencies));
  if (!result.ok()) throw std::runtime_error("peer creation failed");
  rpc->pc = result.MoveValue();
  peer.pc = rpc.release();
  return peer.pc;
}

std::string Sdp(void* pc, bool offer) {
  std::promise<std::string> promise;
  auto future = promise.get_future();
  auto ok = [](void* p, const char*, const char* sdp) {
    static_cast<std::promise<std::string>*>(p)->set_value(sdp);
  };
  auto fail = [](void* p, const char*) {
    static_cast<std::promise<std::string>*>(p)->set_exception(
        std::make_exception_ptr(std::runtime_error("SDP creation failed")));
  };
  if (offer) reactor_webrtc_peer_connection_create_offer(pc, &promise, ok, fail);
  else reactor_webrtc_peer_connection_create_answer(pc, &promise, ok, fail);
  if (future.wait_for(5s) != std::future_status::ready) std::terminate();
  return future.get();
}

void SetSdp(void* pc, const char* type, const std::string& sdp, bool local) {
  std::promise<bool> promise;
  auto future = promise.get_future();
  auto complete = [](void* p, const char* error) {
    static_cast<std::promise<bool>*>(p)->set_value(error == nullptr);
  };
  if (local) reactor_webrtc_peer_connection_set_local_description(pc, type, sdp.c_str(), &promise, complete);
  else reactor_webrtc_peer_connection_set_remote_description(pc, type, sdp.c_str(), &promise, complete);
  if (future.wait_for(5s) != std::future_status::ready) std::terminate();
  if (!future.get()) throw std::runtime_error("SDP application failed");
}

void ForwardIce(Peer& from, Peer& to) {
  std::deque<Ice> candidates;
  { std::lock_guard lock(from.mutex); candidates.swap(from.ice); }
  for (const auto& ice : candidates) {
    reactor_webrtc_peer_connection_add_ice_candidate(
        to.pc, ice.mid.c_str(), ice.line, ice.candidate.c_str(), nullptr, nullptr);
  }
}

std::vector<ReactorStatEntry> Stats(void* pc) {
  std::promise<std::vector<ReactorStatEntry>> promise;
  auto future = promise.get_future();
  reactor_webrtc_peer_connection_get_stats(pc, &promise,
      [](void* p, const ReactorStatEntry* entries, int count) {
        std::vector<ReactorStatEntry> copy;
        if (entries && count > 0) copy.assign(entries, entries + count);
        static_cast<std::promise<std::vector<ReactorStatEntry>>*>(p)->set_value(std::move(copy));
      });
  if (future.wait_for(5s) != std::future_status::ready) std::terminate();
  return future.get();
}

class DropLog : public webrtc::LogSink {
 public:
  std::atomic<int> total{0};
  std::atomic<int> observations{0};
  void OnLogMessage(const std::string& message) override {
    if (std::getenv("SMOOTHING_TRACE")) std::cerr << message;
    std::string marker = "WebRTC.Video.DroppedFrames.RenderQueue ";
    auto at = message.find(marker);
    if (at != std::string::npos) {
      total += std::stoi(message.substr(at + marker.size()));
      ++observations;
    }
  }
};

int main(int argc, char** argv) {
  if (argc != 3 && argc != 4) return 2;
  std::string codec_name = argc == 4 ? argv[3] : "H264";
  if (codec_name != "H264" && codec_name != "VP8") return 2;
  if (std::string(argv[1]) != "on" && std::string(argv[1]) != "off") return 2;
  bool smoothing = std::string(argv[1]) == "on";
  int stall_ms = std::stoi(argv[2]);
  if (stall_ms < 0 || stall_ms > 250) return 2;
  webrtc::LogMessage::LogToDebug(webrtc::LS_NONE);
  webrtc::LogMessage::SetLogToStderr(false);
  DropLog drops;
  webrtc::LogMessage::AddLogToStream(&drops, webrtc::LS_INFO);
  ReactorFactoryOptions options{};
  options.size = sizeof(options);
  char error[512]{};
  void* factory = reactor_webrtc_factory_create(&options, error, sizeof(error));
  if (!factory) throw std::runtime_error("factory creation failed");
  Peer sender, receiver;
  receiver.stall_ms = stall_ms;
  MakePeer(factory, sender, true);
  MakePeer(factory, receiver, smoothing);
  void* video = reactor_webrtc_video_track_create(factory, "experiment-video");
  if (!video || !reactor_webrtc_peer_connection_add_track(sender.pc, video)) {
    throw std::runtime_error("video source creation failed");
  }
  auto* rf = static_cast<ReactorFactory*>(factory);
  std::vector<webrtc::RtpCodecCapability> codecs;
  for (const auto& codec : rf->factory->GetRtpSenderCapabilities(webrtc::MediaType::VIDEO).codecs) {
    if (codec.name == codec_name) codecs.push_back(codec);
  }
  if (codecs.empty()) throw std::runtime_error("requested codec unavailable");
  for (auto& transceiver : static_cast<ReactorPeerConnection*>(sender.pc)->pc->GetTransceivers()) {
    if (!transceiver->SetCodecPreferences(codecs).ok()) throw std::runtime_error("codec selection failed");
  }
  reactor_webrtc_peer_connection_set_bitrate(sender.pc, 1000000, 3000000, 5000000, error, sizeof(error));
  auto offer = Sdp(sender.pc, true);
  SetSdp(sender.pc, "offer", offer, true);
  SetSdp(receiver.pc, "offer", offer, false);
  auto answer = Sdp(receiver.pc, false);
  SetSdp(receiver.pc, "answer", answer, true);
  SetSdp(sender.pc, "answer", answer, false);
  for (auto& transceiver : static_cast<ReactorPeerConnection*>(sender.pc)->pc->GetTransceivers()) {
    auto parameters = transceiver->sender()->GetParameters();
    for (auto& encoding : parameters.encodings) encoding.max_framerate = 24;
    if (!transceiver->sender()->SetParameters(parameters).ok()) {
      throw std::runtime_error("frame-rate configuration failed");
    }
  }
  auto deadline = std::chrono::steady_clock::now() + 10s;
  while (!sender.connected || !receiver.connected) {
    ForwardIce(sender, receiver);
    ForwardIce(receiver, sender);
    if (std::chrono::steady_clock::now() >= deadline) throw std::runtime_error("local connection timeout");
    std::this_thread::sleep_for(10ms);
  }
  std::this_thread::sleep_for(200ms);
  constexpr int width = 1344, height = 768;
  std::vector<uint8_t> pixels(width * height * 4, 255);
  auto start = std::chrono::steady_clock::now();
  for (int id = 1; id <= 158; ++id) {
    std::this_thread::sleep_until(start + std::chrono::microseconds((id - 1) * 1000000LL / 24));
    for (int y = 0; y < height; ++y) {
      for (int x = 0; x < width; ++x) {
        auto level = (id & (1 << (x * 8 / width))) ? 235 : 20;
        auto index = (y * width + x) * 4;
        pixels[index] = pixels[index + 1] = pixels[index + 2] = level;
      }
    }
    reactor_webrtc_video_track_push_frame(video, pixels.data(), width, height);
  }
  std::this_thread::sleep_for(2s);
  auto stats = Stats(receiver.pc);
  auto sent_stats = Stats(sender.pc);
  uint32_t decoded = 0, decoder_drops = 0, sent = 0;
  int32_t packets_lost = 0;
  for (const auto& stat : stats) if (stat.kind == 0 && stat.stream_kind == 1) {
    decoded += stat.frames_decoded;
    decoder_drops += stat.frames_dropped;
    packets_lost += stat.packets_lost;
  }
  for (const auto& stat : sent_stats) if (stat.kind == 1 && stat.stream_kind == 1) sent += stat.frames_sent;
  reactor_webrtc_peer_connection_destroy(sender.pc);
  reactor_webrtc_peer_connection_destroy(receiver.pc);
  for (void* track : sender.tracks) reactor_webrtc_media_stream_track_destroy(track);
  for (void* track : receiver.tracks) reactor_webrtc_media_stream_track_destroy(track);
  reactor_webrtc_media_stream_track_destroy(video);
  reactor_webrtc_factory_destroy(factory);
  webrtc::LogMessage::RemoveLogToStream(&drops);
  std::cout << "{\"experiment\":\"local_webrtc\",\"codec\":\"" << codec_name
            << "\",\"smoothing\":"
            << (smoothing ? "true" : "false") << ",\"sink_stall_ms\":" << stall_ms
            << ",\"injected_stalls\":" << receiver.stalls
            << ",\"source_frames\":158,\"frames_sent\":" << sent
            << ",\"frames_decoded\":" << decoded
            << ",\"decoder_drops\":" << decoder_drops
            << ",\"packets_lost\":" << packets_lost
            << ",\"render_drop_log_entries\":" << drops.observations.load()
            << ",\"native_render_drops\":";
  if (drops.observations) std::cout << drops.total.load();
  else std::cout << "null";
  std::cout << ",\"delivered\":" << receiver.ids.size()
            << ",\"invalid_markers\":" << receiver.invalid_markers << ",\"delivered_ids\":[";
  for (size_t i = 0; i < receiver.ids.size(); ++i) {
    if (i) std::cout << ',';
    std::cout << receiver.ids[i];
  }
  std::cout << "]}\n";
  if (decoded == 0 || receiver.ids.empty() || receiver.invalid_markers) return 3;
  if (smoothing && !drops.observations) return 4;
}
