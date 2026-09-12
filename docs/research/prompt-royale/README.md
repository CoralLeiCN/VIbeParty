# Prompt Royale: Reactor and VEED integration research

Researched: 12 September 2026. Scope: [Prompt Royale](../../games/prompt-royale/game-spec.md), with the proposed [Python backend](../../backend-spec.md). This is documentation research using public vendor sources, including a live read of Reactor's public pricing endpoint. No authenticated generation, SDK installation, or performance benchmark was run. Recommendations below are design proposals, not implemented features.

Implementation decision following this research, updated after hackathon simplification: **3–4 players, one room, one FastAPI process, in-memory state, asyncio tasks, polling, and private local clips**. Allow one retry for a confirmed transient failure, with at most two creation attempts per entry and no deadline extension. The [demo stack](../../games/prompt-royale/tech-stack.md) is authoritative; the [before-and-after comparison](../../games/prompt-royale/simplification.md) records the removed infrastructure. Larger-group comparisons below are future exploration, not enabled capacity. See the [dedicated game limitations](../../games/prompt-royale/game-spec.md#hackathon-limitations-and-future-exploration).

## Recommendation

Use **Reactor Helios as the selected generator for competing clips** and **VEED Fabric as optional pre-rendered host media**. Validate one capture, then three and four players. Add the host assets after the core round works. Keep the hackathon cap at four; explore larger groups and shared scheduling after the event.

Prompt Royale credits **[Quiplash by Jackbox Games](https://store.steampowered.com/app/351510/Quiplash/)** for its creative prompt-and-vote inspiration. Here, the entertaining answer is a generated scene. That makes a scene generator central to the game; a talking presenter can explain the topic and introduce the reveal without deciding the winner.

| Product | Verified capability | Proposed role | Assessment |
| --- | --- | --- | --- |
| Reactor / Helios | Text-steered live video, with optional reference images. [Model documentation](https://docs.reactor.inc/model-api-reference/helios/overview). | Generate an isolated scene for each accepted prompt, then capture a fixed-length entry. | Strong candidate for the core game; requires a stream-to-clip adapter and live validation. |
| Reactor / LongLive-2.0 | Text-only video with shot transitions and cuts. [Model documentation](https://docs.reactor.inc/model-api-reference/longlive-v2/overview). | Alternative to benchmark before choosing the round's model. | Plausible candidate, especially for a later multi-shot format. |
| VEED / Fabric 1.0 | Image and audio inputs produce a talking video. [Endpoint schema](https://fal.ai/models/veed/fabric-1.0/api). | Animate a recurring mascot for instructions, voting cues, and celebrations. | Useful optional presentation layer. |
| VEED / live avatars | VEED's API page links to a live-avatar waitlist. [API page](https://www.veed.io/api). | A host that responds during the party. | Conditional on partner access and a demonstrated integration. |

## What Prompt Royale needs

The current hackathon specification has 3–4 players, one shared topic, 60 seconds for private submissions, one approximately five-second landscape clip per accepted entry, a 2×2 arena showing all clips playing together on repeat, and 10 seconds for voting from the same grid. Before starting, the host chooses a bundled topic or requests an LLM-generated suggestion, labelled as such, and confirms it or generates another if the group has played it before. The topic LLM remains to be selected and validated; this research covers the video providers. The 180-second video generation deadline includes queueing and media preparation. Authors and prompts stay hidden until results; ballots are counted by the application.

The provider choice must preserve equal generation settings, anonymous entries, replayable clips, and a reveal that works with sound muted. VibeParty should own the room state machine and voting rules. An animated host must remain optional so an unavailable host asset cannot block a round.

## Reactor: generating the contest entries

### Model and prompt fit

Helios connects as `reactor/helios`. Its output is video only, with a native size of 640×384 and default 2× output of 1280×768. This is landscape at 5:3; use a matching player or consistent letterboxing. A reference image is optional, so the existing text-only game can use it without adding an image-generation stage. [Helios overview](https://docs.reactor.inc/model-api-reference/helios/overview).

The documented controls include `set_prompt`, `set_seed`, `set_sr_scale`, `start`, and `pause`. Set the seed before starting. Freeze the model, scale, rendering template, capture policy, and seed policy for the whole round; never expose steering, rewind, or reroll controls to contestants after submission. A fresh session per entry is the initial proposal to avoid carrying visual history between contestants. [Helios schema](https://docs.reactor.inc/model-api-reference/helios/schema).

Helios's prompt guide warns that its text encoder truncates beyond 512 tokens and recommends staying within about 500. Validate the entire effective prompt, including the fixed template, before accepting it. Its guide also suggests expanding short inputs with an LLM; for this contest, preserve player wording and use only the same fixed rendering instructions for everyone. Teach players to describe one visible action in a clear setting. Do not secretly improve selected answers. [Prompt guide](https://docs.reactor.inc/model-api-reference/helios/prompt-guide).

LongLive-2.0 is another text-only candidate, with documented 1280×704 output at 24 fps. Its multi-shot features are unnecessary for an initial five-second entry. Defer a model comparison until after the demo unless Helios fails the initial capture spike; do not switch individual failed entries to another model. [LongLive overview](https://docs.reactor.inc/model-api-reference/longlive-v2/overview).

### Turning a live session into a ballot entry

Reactor supports a recent-duration clip or full-session recording when recording is enabled for the model. `request_clip(5)` requests recent session history; it does not generate a five-second video on demand. Capture must happen while the connection is ready. Python's `download_clip` helper saves MPEG-TS, whereas the JavaScript helper assembles MP4. The Python path therefore needs a remux step, with codec validation before browser playback. Recording URLs expire after 24 hours; Reactor says these clips are deleted then and are not used for training. [Recording documentation](https://docs.reactor.inc/concepts/recordings).

Simplified demo task sequence:

1. Claim the entry once under the room lock, acquire a local entry slot, and check the start interval, deadline, and call allowance. The demo is the only active consumer of the account during play.
2. Create a fresh duration-capped session, record its ID in memory when known, and apply the frozen settings and accepted text.
3. Start generation. Collect enough actual media for the fixed capture window; do not equate five seconds of wall-clock waiting with five seconds of valid video.
4. Request the clip, download its segments, and close the owned session promptly. Initially complete the download before disconnecting; benchmark whether earlier termination safely preserves download access.
5. Remux and validate duration, dimensions, codecs, and content. If needed, trim by the same deterministic rule for every entry. Never choose the funniest segment after inspecting an entry.
6. Save the MP4 in a private local directory with opaque identifiers. Authorize all completed eligible clips together when arena screening begins, then freeze the remaining eligible entries when the host opens voting.

The exact capture start, warm-up allowance, and handling of chunk boundaries need a live spike. A confirmed transient capture failure may retry once after the old session is known ended, within the existing deadline and call allowance. Reuse the existing recording/source for download or preparation retries. If recovery fails or cannot fit, mark the entry unavailable. Never offer a reroll of a successful clip.

### Backend implications

Reactor is a stateful streaming connection, so its session is not interchangeable with a batch provider job. A bounded asyncio task owns each session inside the single demo process. Track session ID, settings, capture status, termination, and timing in memory and concise operational logs. Celery, durable leases, outboxes, and crash recovery are deferred; a process restart ends the round and must not restart paid requests.

The Python SDK supports `async with`, a `max_session_duration_seconds` constructor option, and `disconnect()` to terminate a session it created. Use provider-enforced duration limits as well as the application deadline, and clean up in a `finally` path. Do not leave a live connection running throughout voting. [Python SDK reference](https://docs.reactor.inc/sdk-reference/python/reactor).

Keep provider credentials and sessions inside the backend. Python can exchange a server-held API key for a scoped JWT automatically; explicitly minted tokens can restrict model access and session count. Browser clients need only game snapshots and authorized clip playback, which also prevents private previews and unauthorized steering. [Authentication](https://docs.reactor.inc/authentication).

No exactly-once session-creation guarantee was established in this research. An ambiguous connection failure blocks new live starts until the operator checks session status; never automatically create a replacement. The simplified counter does not refund the attempted call. A late clip must never join an already-open ballot.

## VEED: hosting the party

### Publicly documented integration

VEED directs developers to fal.ai, which supplies authentication, billing, and Python/JavaScript clients. A VEED editor subscription is not the prerequisite for this API. [VEED's Fabric help article](https://support.veed.io/en/articles/15230480-veed-fabric-1-0-api).

The `veed/fabric-1.0` schema requires `image_url`, `audio_url`, and `resolution` (`480p` or `720p`), returning a `video` file. It does not expose a text-only scene-generation input. A dynamic scripted host therefore needs a separate text-to-speech step, or a supplied recording, plus a fixed mascot image. The API documents queued submission, status lookup, result retrieval, and optional webhooks. Keep its `FAL_KEY` server-side and persist the returned request ID. [Fabric API schema](https://fal.ai/models/veed/fabric-1.0/api).

This makes Fabric a good fit for a character delivering instructions. It does not directly replace the current scene generator: turning every contestant's answer into a speaking character would change what people create and judge.

### Proposed host behavior

| Moment | Host contribution | Information allowed |
| --- | --- | --- |
| Lobby | Explain the rules with a reusable introduction. | Public rules only. |
| Topic reveal | Introduce the selected topic after host confirmation where required; keep its text on screen. | Shared topic, never private submissions. |
| Generation | Play a short reusable transition once. | Public completion count, if needed; no invented progress. |
| Arena screening and voting | Introduce the full grid of anonymous clips and invite votes when the host opens voting. | Public phase and entry labels; no commentary ranking the clips. |
| Results | Celebrate the winners or a tie. | Final server-calculated results, after voting closes. |

Pre-render a small library of instructions and transition clips with Fabric, and show dynamic topics, names, and scores as ordinary UI text. This uses VEED visibly without adding render latency to each round. Provide the same words as captions or visible text. If a host clip fails, continue using the text UI.

A later dynamic host can render from a deterministic script assembled from already-public state. It should have no authority to close ballots, invent scores, or choose winners. Reusable host media should contain no room-specific data; room-specific generated media follows the app's expiry policy.

VEED also lists subtitle, lip-sync, and background-removal APIs. Captioning or compositing a presenter could be useful later, but transforming every anonymous contest entry adds work and can change what voters judge. Keep that processing out of the first contest pipeline. [VEED API catalog](https://www.veed.io/api).

### Live avatars and an optional game variant

The public site exposes a **Live Avatar API Waitlist**, rather than a verified integration contract in the pages reviewed. A hackathon introduction may unlock access, but it does not establish SDK availability, latency, price, or recording support. Ask the partner for a runnable example and test it before putting a live host on the demo's required path. [VEED API page](https://www.veed.io/api).

An alternative future mode could be closer to Quiplash: everyone completes a sentence, and the same mascot delivers each answer using Fabric and one fixed voice. That would need an explicit rules update for audio, captions, answer length, and timing. It is a possible extension, not the implementation recommended for the current video-scene contest.

## Cost, capacity, and waiting time

### Reactor

The unauthenticated [Reactor pricing endpoint](https://api.reactor.inc/pricing) was successfully read on 12 September 2026. Its `helios` and `longlive-v2` rows both returned `amount_per_sec_usd: "0.0017"`, in USD per session-second. This is a point-in-time observation, not a locked quote.

Billing starts at `ready` and continues while the GPU is held, including idle time; termination stops it. The bill is based on session time, not the duration of the saved clip. Programmatic usage reporting is described as forthcoming, so reconcile estimates against the dashboard during the prototype. [Pricing and billing](https://docs.reactor.inc/resources/billing).

Illustrative model charges at the observed rate, excluding retries and other infrastructure. Eight-entry rows are future sizing examples beyond the four-player hackathon cap:

| Entries | Assumed billed seconds per entry | Calculation | Model charge |
| --- | --- | --- | --- |
| 3 | 20 | 3 × 20 × $0.0017 | $0.102 |
| 4 | 20 | 4 × 20 × $0.0017 | $0.136 |
| 8 | 20 | 8 × 20 × $0.0017 | $0.272 |
| 8 | 60 | 8 × 60 × $0.0017 | $0.816 |

These durations are planning examples, not measured performance. Four entries at a 60-second provider cap imply $0.408 of first-attempt model exposure at the observed rate. With one replacement attempt for every entry, the demo's four-player bound is $0.816; for three players it is $0.612. The eight-player equivalent of $1.632 is future sizing only. The separate 16-start demo-run allowance is also $1.632 at this rate and covers at most two four-player rounds if every entry uses a replacement. Actual costs include billable session ownership and other infrastructure.

Reactor documents default account limits of five concurrent sessions and ten new sessions per minute, with a burst of three followed by roughly one token every six seconds. Connecting and waiting sessions also consume concurrency slots. Limits are shared across keys and models; check the actual account quota. [Rate limits](https://docs.reactor.inc/resources/rate-limits).

Consequently, eight fresh sessions cannot all begin simultaneously under the defaults. Future multi-room play needs a scheduler across rooms and games, handling both concurrency and creation rate. With an otherwise idle account and available slots, the eighth start cannot occur before roughly 30 seconds under that token-bucket model; busy slots or GPU allocation may add more delay. The demo instead uses two local entry slots, a conservative start interval, exclusive account use during play, and a 180-second total deadline including retries. A confirmed pre-creation 429 may use the single retry after Retry-After and local start pacing, only if time and allowance remain.

Reactor advertises sub-second round-trip latency, but that is not a measurement of cold allocation, a finished clip, or an eight-entry round. Benchmark these separately. [Platform overview](https://docs.reactor.inc/overview).

### VEED / fal

Observed published rates and illustrative output charges:

| Fabric tier | USD per output second | Five-second segment | 30 seconds of host material |
| --- | --- | --- | --- |
| Standard 480p | $0.08 | $0.40 | $2.40 |
| Standard 720p | $0.15 | $0.75 | $4.50 |
| Fast 480p | $0.10 | $0.50 | $3.00 |
| Fast 720p | $0.20 | $1.00 | $6.00 |

Rates come from the [standard Fabric model page](https://fal.ai/models/veed/fabric-1.0) and [Fast model page](https://fal.ai/models/veed/fabric-1.0/fast). Calculations exclude voice generation, asset creation, storage, taxes, and retries. Reusing already-rendered host material avoids another Fabric generation charge on each replay. Output length is not render latency.

There is a documentation discrepancy: VEED's help article lists $0.05/second and a one-minute maximum, while other VEED pages give different prices and longer durations. Use the selected fal endpoint and account billing for implementation; verify limits in a smoke test instead of carrying the help article's figures into the budget. [Help article](https://support.veed.io/en/articles/15230480-veed-fabric-1-0-api), [VEED product guide](https://www.veed.io/learn/best-image-to-video-api).

## Data and failure behavior

Reactor screens submitted text and reference images and may terminate a violating session. Previously accrued session charges still apply. Map this to the entry's rejection/failure outcome; it must not restart automatically with rewritten content. The reviewed input-moderation description does not establish that every recorded output is safe for screening. The supervised demo uses host Exclude clip/Abort controls and makes no automated output-review claim; a separate review service is deferred. [Reactor moderation](https://docs.reactor.inc/resources/content-moderation).

fal distinguishes stored request JSON from generated media. Request payloads default to 30-day retention; it documents separate controls for payload storage and media expiry. Its CDN links are public by default, and v3 objects support access controls; input uploads require their own ACL settings. Configure and verify these controls before sending room-specific host material, and serve final assets through application authorization. Copying a file to private storage alone does not remove the provider's copy. [Data retention](https://fal.ai/docs/documentation/model-apis/media-expiration), [File access controls](https://fal.ai/docs/documentation/model-apis/file-access-controls).

For the initial demo, use an owned mascot and generic scripts. Send no player identity or hidden answer to the host pipeline. A VEED failure must not affect clip eligibility or scores; a Reactor failure follows the existing rule that a round needs at least two eligible clips to be scored.

## Suggested integration spike and decision gates

This is proposed validation work; none of these outcomes has been measured yet.

| Step | Evidence to collect | Decision |
| --- | --- | --- |
| Confirm access | Reactor key/model access, recording enabled, actual quotas and rates; fal key and Fabric availability; any separate live-avatar offer. | Do not promise partner-specific capabilities from the event listing alone. |
| Capture one entry | Exact prompt preserved, five seconds of usable video, successful Python download/remux, phone playback, session termination. | Proceed with Reactor only when the complete file path works. |
| Run three then four entries | Queue delay, time to ready, first media, capture/download/preparation time, valid-entry count, total round time, observed cost. | Validate hackathon capacity without exceeding four players; investigate larger groups after the event. |
| Rehearse the arena | Four clips playing together in the 2×2 grid on phone Safari/Chrome and the projected host screen; group replay/pause, loading failures, fixed positions, and the 10-second vote. | Validate simultaneous playback separately from clip generation; these checks remain unrun. |
| Compare output quality, later | Same visual joke prompts on Helios and LongLive; human assessment of recognizable action, topic fit, and entertainment. | Defer comparison unless the selected Helios integration fails. |
| Exercise demo failures | Process restart, ambiguous creation, rejected prompt, transient failure then retry success/exhaustion, repeated browser command, late result. | Restart clears the room; no automatic crash replay, third attempt, or late ballot entry. Verify bounded session cleanup and reuse of saved media. |
| Add VEED host library | Legible character, accurate speech/captions, reusable assets, text fallback, no private content. | Enable as optional presentation after the contest loop works. |

The first implementation should therefore be **Reactor-generated entries → private recorded clips → simultaneous arena screening → application voting**, with **VEED host segments around that flow**. Dynamic live hosting can follow once its access and operating characteristics are demonstrated.
