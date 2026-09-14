// Controlled experiment with Reactor's unmodified native WebRTC render stage.
// Frames enter at the decoded-frame boundary; no codec, network, or GPU is used.
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "api/environment/environment_factory.h"
#include "api/peer_connection_interface.h"
#include "api/task_queue/task_queue_base.h"
#include "api/task_queue/task_queue_factory.h"
#include "api/video/i420_buffer.h"
#include "api/video/video_frame.h"
#include "rtc_base/logging.h"
#include "system_wrappers/include/clock.h"
#include "video/render/incoming_video_stream.h"

using namespace webrtc;
using Task = absl::AnyInvocable<void() &&>;
constexpr int kFrames = 158;
constexpr int64_t kEpochUs = 1000000;

struct Profile {
  std::string name;
  int batch = 1;
  std::vector<std::pair<int64_t, int64_t>> pauses_us;
};

// A deterministic scheduler for the real IncomingVideoStream task queue.
// All experiment calls are on one thread. Only task execution is delayed;
// the decoded input timeline and frame presentation timestamps are unchanged.
class ManualQueue final : public TaskQueueBase {
 public:
  ManualQueue(SimulatedClock& clock, const Profile& profile)
      : clock_(clock), profile_(profile) {}
  void Delete() override {
    CurrentTaskQueueSetter current(this);
    tasks_.clear();
    // Owned by ManualFactory so the driver may inspect it after stream teardown.
  }
  int64_t NextRunnable() const {
    if (tasks_.empty()) return INT64_MAX;
    int64_t next = std::max(Now(), tasks_.begin()->first.first);
    for (const auto& [start, end] : profile_.pauses_us) {
      if (next >= kEpochUs + start && next < kEpochUs + end) {
        next = kEpochUs + end;
      }
    }
    return next;
  }
  void RunUntil(int64_t target) {
    size_t executions = 0;
    while (NextRunnable() <= target) {
      if (++executions > 100000) throw std::runtime_error("scheduler did not settle");
      AdvanceTo(NextRunnable());
      auto node = tasks_.extract(tasks_.begin());
      CurrentTaskQueueSetter current(this);
      std::move(node.mapped())();
    }
    AdvanceTo(target);
  }
  size_t pending() const { return tasks_.size(); }

 private:
  int64_t Now() const { return clock_.CurrentTime().us(); }
  void AdvanceTo(int64_t target) {
    if (target < Now()) throw std::runtime_error("clock moved backwards");
    clock_.AdvanceTimeMicroseconds(target - Now());
  }
  void PostTaskImpl(Task task, const PostTaskTraits&, const Location&) override {
    tasks_.emplace(std::make_pair(Now(), order_++), std::move(task));
  }
  void PostDelayedTaskImpl(Task task, TimeDelta delay,
                           const PostDelayedTaskTraits&, const Location&) override {
    tasks_.emplace(std::make_pair(Now() + delay.us(), order_++), std::move(task));
  }
  SimulatedClock& clock_;
  const Profile& profile_;
  uint64_t order_ = 0;
  std::map<std::pair<int64_t, uint64_t>, Task> tasks_;
};

class ManualFactory final : public TaskQueueFactory {
 public:
  ManualFactory(SimulatedClock& clock, const Profile& profile) : queue(clock, profile) {}
  std::unique_ptr<TaskQueueBase, TaskQueueDeleter> CreateTaskQueue(
      absl::string_view, Priority) const override {
    if (created_) throw std::runtime_error("unexpected additional task queue");
    created_ = true;
    return std::unique_ptr<TaskQueueBase, TaskQueueDeleter>(&queue);
  }
  mutable ManualQueue queue;
 private:
  mutable bool created_ = false;
};

class Collector final : public VideoSinkInterface<VideoFrame> {
 public:
  void OnFrame(const VideoFrame& frame) override { ids.push_back(frame.id()); }
  std::vector<int> ids;
};

class RenderDropLog final : public LogSink {
 public:
  void OnLogMessage(const std::string& message) override {
    const std::string marker = "WebRTC.Video.DroppedFrames.RenderQueue ";
    auto position = message.find(marker);
    if (position != std::string::npos) {
      drops = std::stoi(message.substr(position + marker.size()));
    }
  }
  std::optional<int> drops;
};

struct Result {
  std::string profile;
  bool smoothing;
  std::vector<int> delivered;
  std::vector<int> missing;
  std::optional<int> render_drops;
  size_t pending;
};

Result Run(const Profile& profile, bool smoothing) {
  SimulatedClock clock(kEpochUs);
  ManualFactory factory(clock, profile);
  auto environment = CreateEnvironment(&clock, &factory);
  Collector collector;
  RenderDropLog drop_log;
  LogMessage::AddLogToStream(&drop_log, LS_INFO);

  // Match VideoReceiveStream2's actual routing decision. The smoother itself
  // and its drop policy are linked from the unmodified libwebrtc.a archive.
  PeerConnectionInterface::RTCConfiguration config;
  config.set_prerenderer_smoothing(smoothing);
  std::unique_ptr<IncomingVideoStream> smoother;
  VideoSinkInterface<VideoFrame>* receiver = &collector;
  if (config.prerenderer_smoothing()) {
    smoother = std::make_unique<IncomingVideoStream>(environment, 10, &collector);
    receiver = smoother.get();
  }

  auto pixels = I420Buffer::Create(16, 16);
  pixels->InitializeData();
  for (int i = 0; i < kFrames; ++i) {
    const int first_in_batch = i / profile.batch * profile.batch;
    const int64_t arrival_us = kEpochUs + first_in_batch * 1000000LL / 24;
    factory.queue.RunUntil(arrival_us);
    auto frame = VideoFrame::Builder()
                     .set_video_frame_buffer(pixels)
                     .set_id(i + 1)
                     .set_rtp_timestamp(i * 3750)
                     .set_timestamp_ms((kEpochUs + i * 1000000LL / 24 + 100000) / 1000)
                     .build();
    receiver->OnFrame(frame);
    factory.queue.RunUntil(arrival_us);
  }
  factory.queue.RunUntil(kEpochUs + 12000000);
  size_t pending = factory.queue.pending();
  smoother.reset();  // Native destructor emits its own render-drop counter.
  LogMessage::RemoveLogToStream(&drop_log);

  std::vector<int> missing;
  for (int id = 1; id <= kFrames; ++id) {
    if (std::find(collector.ids.begin(), collector.ids.end(), id) == collector.ids.end()) {
      missing.push_back(id);
    }
  }
  if (!std::is_sorted(collector.ids.begin(), collector.ids.end()) ||
      std::adjacent_find(collector.ids.begin(), collector.ids.end()) != collector.ids.end()) {
    throw std::runtime_error("duplicate or reordered output marker");
  }
  if (pending != 0) throw std::runtime_error("test ended before pending delivery completed");
  if (!smoothing && collector.ids.size() != kFrames) {
    throw std::runtime_error("direct delivery lost a frame");
  }
  if (smoothing && (!drop_log.drops || *drop_log.drops != static_cast<int>(missing.size()))) {
    throw std::runtime_error("missing frames do not match native render-drop counter");
  }
  return {profile.name, smoothing, collector.ids, missing, drop_log.drops, pending};
}

void PrintIds(const std::vector<int>& ids) {
  std::cout << '[';
  for (size_t i = 0; i < ids.size(); ++i) {
    if (i) std::cout << ',';
    std::cout << ids[i];
  }
  std::cout << ']';
}

int main() {
  LogMessage::LogToDebug(LS_NONE);
  LogMessage::SetLogToStderr(false);
  std::vector<Profile> profiles = {
      {"steady_24fps", 1, {}},
      {"three_frame_batches", 3, {}},
  };
  for (int duration_ms : {20, 50, 100, 150, 250}) {
    profiles.push_back({"single_pause_" + std::to_string(duration_ms) + "ms", 1,
                        {{990000, 990000 + duration_ms * 1000}}});
  }
  Profile repeated{"repeated_150ms_pauses", 1, {}};
  for (int64_t start = 240000; start < 6500000; start += 500000) {
    repeated.pauses_us.emplace_back(start, start + 150000);
  }
  profiles.push_back(repeated);
  auto batched_repeated = repeated;
  batched_repeated.name = "batches_and_repeated_pauses";
  batched_repeated.batch = 3;
  profiles.push_back(batched_repeated);

  bool first = true;
  std::cout << "{\"experiment\":\"native_decoded_frame_boundary\",\"input_frames\":158,"
               "\"fps\":24,\"results\":[";
  for (const auto& profile : profiles) {
    for (bool smoothing : {true, false}) {
      auto result = Run(profile, smoothing);
      if (!first) std::cout << ',';
      first = false;
      std::cout << "{\"profile\":\"" << result.profile << "\",\"smoothing\":"
                << (smoothing ? "true" : "false") << ",\"delivered\":"
                << result.delivered.size() << ",\"native_render_drops\":";
      if (result.render_drops) std::cout << *result.render_drops;
      else std::cout << "null";
      std::cout << ",\"pending_tasks\":" << result.pending << ",\"delivered_ids\":";
      PrintIds(result.delivered);
      std::cout << ",\"missing_ids\":";
      PrintIds(result.missing);
      std::cout << '}';
    }
  }
  std::cout << "]}\n";
}
