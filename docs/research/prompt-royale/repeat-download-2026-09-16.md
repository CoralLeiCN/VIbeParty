# Same-generation repeated download test — 16 September 2026

**Follow-up:** The boundary control was subsequently tested on and off in four
hosted sessions. Disabled runs reached 158 non-black callbacks after allowing late
frames; enabled runs reached 155 and 156. Recording downloads still remained HTTP
202. See the [flush comparison](flush-control-live-test-2026-09-16.md).

The user proposed downloading the same generation three times to help distinguish
network delivery problems from problems in the source video. Three download attempts
against one fixed recording all remained HTTP 202 (not ready). No downloaded files
were produced, so this test cannot compare bytes or decoded frames and cannot identify
the cause of earlier live-stream losses.

## Corrected comparison

The comparison used exactly one new generation, the existing fixed penguin prompt,
seed 42 and a six-second request. During playback, after receiving video for three
seconds, the probe called `request_clip(2)` once. It then reused that exact descriptor
for all three downloads, without another recording request or regeneration between
copies. This was a two-second excerpt of the generation, not a full-generation export.

The accepted recording markers were 1.233333333333333–3.233333333333333. Downloads
started after playback finished. The HTTP client enforced per-request timeouts and a
ten-second bound for each download, and retained response status codes without URLs
or credentials.

| Copy | Result | Observed duration | Media saved |
| --- | --- | ---: | --- |
| 1 | Repeated HTTP 202, then timeout | 10.002 s | None |
| 2 | Repeated HTTP 202, then timeout | 10.001 s | None |
| 3 | Repeated HTTP 202, then timeout | 10.003 s | None |

There were 12 HTTP 202 responses across the three attempts. No playlist reached 200,
and no media segments were downloaded. The ordinary local-capture path still produced
a playable five-second MP4; that file is not a downloaded server recording.

Final live receiver statistics reported zero video packet loss, zero NACKs, 157 decoded
frames and zero decoder-reported drops. The observer saw 155 raw callbacks; its count
is not a verified unique source-frame count. The connection's earlier frames and black
markers can also contribute to decoder counters.

The session completed and was independently confirmed closed after 53.129 seconds:
`67f12eaf-40fa-42eb-ab2e-c024429a7239`. Evidence:
`.local/vibeparty/prompt-royale/spike/20260915T233435Z-eebb230f/evidence.json`.
The UTC timestamp is 15 September; the local London date was 16 September.

## What the result supports

- The recording API accepted a request, but acceptance did not establish that a
  downloadable recording was available.
- The client could reach the recording endpoint and receive responses. The endpoint
  reported unfinished media throughout the observed retry window.
- This test does not explain why the recording was not ready. Disabled or faulty
  recording, publication delays and other provider behavior remain possibilities.
- HTTP downloads and the live WebRTC stream use different delivery mechanisms.
  Even three successful identical HTTP downloads would establish repeatable file
  delivery for that sample, not rule out loss or adaptation on the live connection.
- Replaying the exact built clip is not a documented alternative: FastH3's schema
  explicitly says clips in history are not playable again. History retains the last
  frame for continuation. No repeat-play command was sent in this experiment.

## Correction: end-of-clip control exists

The current [FastH3 schema](https://docs.reactor.inc/model-api-reference/fast-h3/schema)
documents `set_flush_on_clip_end`. `enabled: false` holds the last frame at clip
boundaries instead of cutting to black. Our first hosted session advertised that
command in `get_state.valid_commands` and reported `flush_on_clip_end: true` both
before and after playback.

The earlier claim that there is no client control for this behavior was too broad.
The [public source/manifest](https://github.com/reactor-team/infinite-livestream/tree/main/fast-h3)
we inspected does not match the full interface advertised by this hosted session.
The public manifest still disables recording, while the hosted API accepted a recording
request. Neither observation establishes successful recording output.

This experiment did not toggle `set_flush_on_clip_end`. Its presence and documented
last-frame behavior do not establish that it drains every source frame or fixes the
large live deficit. The earlier offline drain experiment remains evidence about the
inspected source/runtime combination, not proof of the hosted implementation.

## Preliminary attempts and cleanup

Two earlier single-generation attempts preceded the corrected comparison. They are
not additional copies of its source generation:

1. Session `c2e88105-da66-4caf-9e8a-6bf360eedfcf` requested a full-session recording
   after playback ended. The request was accepted, but the SDK download timed out.
   It had no HTTP-status instrumentation, so that failure alone does not establish
   the provider's response. Evidence: `20260915T233019Z-d571742e`.
2. Session `259cd20e-9ea7-42dd-acad-195d592341de` requested an excerpt during playback.
   A local diagnostic argument-order mistake put the recording URL and JWT into the
   wrong fields. The URL-origin check rejected all three attempts before HTTP requests
   were made. The mistake was corrected using named arguments and checked before the
   final run. Evidence: `20260915T233336Z-f95d99f1`.

All three sessions were independently confirmed closed. No game capture setting was
changed and no report was sent externally. Diagnostic programs and the fetched official
schema are retained in `.local/reactor-repeat-download/`.

The general recording/download API is described in
[Reactor's recording documentation](https://docs.reactor.inc/concepts/recordings).
