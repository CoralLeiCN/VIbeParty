# Word by Word: Reactor and VEED research

> Current choice (16 September 2026): [LingBot World 2 with one continuous stream](../../games/word-by-word/tech-stack.md). The FastH3 and Helios comparisons below document earlier research. Visual quality is trusted and is not an implementation gate. See the [online verification and saved video](2026-09-16-lingbot-continuous-flow.md).

Researched: 12 September 2026. Scope: the [Consequences-inspired Word by Word game](consequences.md). This is a review of public vendor documentation and API schemas, not a completed integration or a measurement of generation quality. No authenticated generation, account quota check, or paid trial was performed.

Later playback/capture guidance: [FastH3 with smoothing on](../../shared/fast-h3-smoothing.md) is the shared implementation guide. It links the subsequent live diagnostics and native experiments, and describes the proposed timestamp-aware replay path and remaining acceptance work.

## Recommendation

**Evaluate Reactor for the evolving scene. Use VEED only where a narrator or finished-video editing adds value.** Reactor documents both continuous prompt steering through Helios and connected clips through FastH3. These support the continuous and segmented options evaluated here. VEED's Fabric API documents talking-character generation from an image and audio, while its Subtitles API processes an existing video. These are useful supporting roles; the reviewed VEED APIs do not establish arbitrary live additions to a shared scene. This recommendation is our assessment of the documented interfaces. [Helios](https://docs.reactor.inc/model-api-reference/helios/overview), [FastH3](https://docs.reactor.inc/model-api-reference/fast-h3/overview), [Fabric API](https://fal.ai/models/veed/fabric-1.0/api), [Subtitles API](https://fal.ai/models/veed/subtitles/api).

**Hackathon specification decision:** the [demo game spec](../../games/word-by-word/game-spec.md) selects four private contributions, each a word, phrase, or short sentence up to 120 characters, followed by a host-controlled additive reveal. Each complete contribution maps to one segment. The single-word sequences below remain minimal research examples. The [simplified technical plan](../../games/word-by-word/tech-stack.md) selects FastH3 with server-side capture and local clips in one FastAPI process. Helios and VEED are deferred from the demo build. See [before and after](../../games/word-by-word/simplification.md). These are design selections, not completed provider trials.

The key experiment is visual continuity: can “forest → fox → dancing → snow” retain the forest and the same fox while visibly adding the action and weather? A command being accepted is not evidence that its word appeared correctly.

For future runs, use the [standard category test scenarios](../../games/word-by-word/test-scenarios.md), recorded on 12 September 2026. They define the shared themes, player categories, exact example answers, expected effects, and result record. The short sequences below remain illustrative research examples; the category scenarios supply the current acceptance inputs.

## Fit to the game

| Game requirement | Reactor | VEED | Assessment |
| --- | --- | --- | --- |
| Apply contributions while one video continues | Helios accepts prompt changes during generation. | No equivalent live scene-steering contract was verified. | Helios is the later continuous-playback candidate. |
| Reveal one new segment per contribution | FastH3 can continue a clip from another clip's final frame. | Fabric generates talking-character clips, not a general continuation of the forest scene. | Test FastH3 first for the selected staged reveal. |
| Preserve earlier additions | History/reference conditioning and continuation inputs are documented; semantic preservation needs testing. | Reusing an avatar image can support a consistent narrator. | Neither establishes a guarantee that arbitrary objects and actions persist. |
| Narrate category prompts or the final story | Helios outputs video only; FastH3 also generates audio. | Fabric animates a supplied character to supplied audio. | VEED is an optional host, not required for gameplay. |
| Show exact words and contributor names | The app should render these from accepted contributions. | Subtitles accepts our own SRT for a finished replay. | Keep live labels in the app; consider VEED after the round. |

Sources for the capabilities above: [Helios overview](https://docs.reactor.inc/model-api-reference/helios/overview), [Helios command reference](https://www.reactor.inc/models/helios/api), [FastH3 overview](https://docs.reactor.inc/model-api-reference/fast-h3/overview), [Fabric schema](https://fal.ai/models/veed/fabric-1.0/api), and [Subtitles schema](https://fal.ai/models/veed/subtitles/api). The fit assessments are design judgments.

## Reactor

### Helios: continuous scene changes

The documented model identifier is `reactor/helios`. Its API exposes `set_prompt`, `start`, `pause`, `resume`, reference-image conditioning, snapshots, and rewind. Prompt updates apply at a chunk boundary; `set_prompt` replaces the active prompt. `chunk_complete` reports the prompt used for a completed chunk. [Command reference](https://www.reactor.inc/models/helios/api).

Reactor lists 33-frame chunks and a 24 fps frame rate. That represents about **1.375 seconds of video per chunk**, calculated from those figures, not a measured response time. GPU allocation, generation, transport, and playback buffering can add delay. [Helios overview](https://docs.reactor.inc/model-api-reference/helios/overview), [model specifications](https://www.reactor.inc/models/helios/info).

The prompt guide recommends adding one new action, object, or event per update and briefly reinforcing the existing background. It documents a 512-token encoder limit with silent truncation beyond it and recommends staying below roughly 500 tokens. [Prompt guide](https://docs.reactor.inc/model-api-reference/helios/prompt-guide).

**Proposed use:** maintain the accepted scene facts in our backend, then compose a concise update containing the new contribution and the relevant earlier facts. Keep the original player contributions separately. Start with fixed templates rather than an unconstrained prompt-writing model, so supporting instructions cannot replace player choices or invent future contributions. Validate prompt length before sending it.

Illustrative effective prompts, written for this project:

| Reveal | Effective scene instruction |
| --- | --- |
| Forest | “A forest clearing, wide fixed camera, playful illustrated style.” |
| Fox | “A fox enters the same forest clearing. Keep the camera and illustrated style.” |
| Dancing | “The same fox is dancing in the forest clearing. Keep its appearance and the fixed camera.” |
| Snow | “Snow begins falling around the same dancing fox in the forest clearing. Keep the fox, its dance, and the camera.” |

These are test prompts, not validated outputs. For a continuous public stream, do not send answers ahead of their public reveal. In the selected privately pregenerated approach, each step receives only facts through that step, and no future asset is released to players. Track command acceptance, generated identity, and displayed video separately so labels do not imply that a visual change has already happened.

### FastH3: successive clips that continue the scene

`reactor/fast-h3` documents a queue of generated clips with native audio and explicit playback control. `starting_frame` accepts an uploaded still; `continue_from_clip_id` uses another clip's last frame to start a continuation. The documentation separates building a clip from playing it. [FastH3 overview](https://docs.reactor.inc/model-api-reference/fast-h3/overview).

**Selected use:** generate the forest clip, then use it as the parent for a clip that introduces the fox, and continue that chain for dancing and snow. Track each contribution against its captured asset and reveal only the eligible clip. Last-frame conditioning still needs a continuity test; it does not prove the model remembers every earlier fact.

The original schema link was unavailable, but the [FastH3 API page](https://www.reactor.inc/models/fast-h3/api) was retrieved during follow-up research. Its implications are incorporated in the [technical plan](../../games/word-by-word/tech-stack.md#5-reactor-integration-contract), including clip duration, generic SDK use, command reconciliation, and capture before replay. Account access and runtime behavior remain untested.

### Other Reactor options considered

- **X2:** takes a live source-video track, including a playing clip or a repeated still, and returns edited video; its prompt can change during the stream. This is worth testing if the product starts with a fixed scene to edit. It is not a documented automatic feedback loop that accumulates its own previous edits. [X2 API](https://www.reactor.inc/models/x2/api).
- **LongLive-2.0:** supports soft shot changes and hard cuts. The reviewed release takes text only and limits one scene to 48 chunks, approximately 58 seconds; a soft shot does not extend that scene limit. This suits a short directed story, but hard cuts would need careful treatment if we promise preservation of one scene. [LongLive overview](https://docs.reactor.inc/model-api-reference/longlive-v2/overview).

### Integration implications

Reactor has JavaScript/React and Python SDKs and streams media over WebRTC. This fits the proposed browser client and Python backend, but requires a session controller rather than treating the main reveal as a single queued MP4 job. [Documentation index](https://docs.reactor.inc/llms.txt), [Python quickstart](https://docs.reactor.inc/quickstart).

Authentication exchanges a server-held API key at `POST https://api.reactor.inc/tokens`. The documented token constraints include model selection, session count, and maximum session duration. A session-scoped token also permits session operations such as uploads, clips, and logs. **It is not established as a read-only spectator credential.** [Authentication](https://docs.reactor.inc/authentication).

Multiple connections can share a session, and the creator owns its lifecycle. Default account limits are five concurrent sessions and ten new sessions per minute; shared connections count as one session. Confirm the actual hackathon account's quotas. [Sessions](https://docs.reactor.inc/concepts/sessions), [rate limits](https://docs.reactor.inc/resources/rate-limits).

**Selected architecture:** use one server-controlled generation session per room. Capture segments privately and authorize each stored asset at its scheduled reveal; do not give provider credentials or direct session access to players. A removed player loses future server access. This preserves a shared scene and avoids a generation session per phone.

For Reactor's recording/export path, recording must be enabled for the chosen model. Reactor documents recent clips and full recordings, requested while the session is ready; the returned URLs expire after 24 hours. Its Python download helper produces MPEG-TS, while the JavaScript helper assembles MP4. The demo instead plans direct SDK frame capture into private local MP4 files; recording export remains an alternative to investigate if capture fails. [Recordings](https://docs.reactor.inc/concepts/recordings).

Reactor screens submitted text and reference images and can terminate a session for a policy violation. That is a session-ending failure to handle; it does not establish that every output frame is reviewed before reaching our display. Continuous playback therefore needs a defined output-checking approach under the existing app requirements. [Content moderation](https://docs.reactor.inc/resources/content-moderation).

## VEED

### Fabric 1.0: an optional narrator or game host

The verified fal endpoint is `veed/fabric-1.0`. Its input schema requires `image_url`, `audio_url`, and a `resolution` of `480p` or `720p`; the result is a video file. The endpoint documents queue submission, status, results, and optional webhooks. It does not expose the mutable scene prompt or previous-scene video input needed for the main game. [Fabric API schema](https://fal.ai/models/veed/fabric-1.0/api).

VEED's help center directs developers to fal.ai for authentication and billing, using a fal account and API key. That route does not require a VEED editor account. [Fabric API help](https://support.veed.io/en/articles/15230480-veed-fabric-1-0-api).

**Proposed use:** a fictional mascot explains “give us a place” or reads the completed sentence at the final reveal. Reuse a prepared introduction across rounds; keep dynamically generated narration outside the critical path. The verified endpoint needs audio, so text-to-speech is a separate step unless a different documented endpoint is selected. Keep private words out of narration until their reveal.

The partner listing describes VEED as “interactive avatars.” The reviewed interactive-avatar page describes selecting a character, providing a script, and creating a video. It does not supply a live conversational/WebRTC API contract. Ask the partner whether hackathon access includes a separate real-time avatar product before planning around one. [Interactive-avatar page](https://www.veed.io/tools/ai-avatar/interactive-avatar).

### Subtitles: exact words in the replay

The documented `veed/subtitles` endpoint accepts a video and subtitle styling. `srt_content` or `srt_file_url` bypasses transcription and uses supplied text. [Subtitles schema](https://fal.ai/models/veed/subtitles/api).

**Proposed use:** after the reveal, create SRT from the actual contribution/reveal timeline and caption the saved video. This preserves spelling and contributor attribution. A silent Helios scene does not need speech recognition. Live captions and turn indicators should remain immediate app UI; a cloud subtitle render should not delay the next word. VEED's help center describes this API as a completed-video workflow hosted through fal. [Subtitles help](https://support.veed.io/en/articles/15230204-veed-subtitles-api).

### OpenEdit: demo production and replay polish

OpenEdit composes and renders video locally, with editing, captions, overlays, and transitions. It is a separate agent-driven workflow, not evidence that the complete VEED web editor is available as a hosted application API. [OpenEdit help](https://support.veed.io/en/articles/16342833-how-to-use-openedit-veed-s-agent-driven-video-editor).

The current repository lists Apple Silicon Mac and Windows x64 support, requires a desktop session, and says Linux is planned. The help article still lists only Apple Silicon/macOS 26, so those pages are not aligned. **Recommendation:** consider it for preparing the hackathon demo or polishing a replay on a workstation, not as an assumed dependency of the proposed containerized Python backend. [OpenEdit repository](https://github.com/veedstudio/open-edit).

## Pricing, access, and documentation discrepancies

These are published figures observed during research, not quotes for our account. Currency is USD. No hackathon credits or paid access were verified.

| Service | Published basis | Example / limitation |
| --- | --- | --- |
| Reactor Helios | Model page lists **$0.102 per session minute**, or 17 credits/second. | A 90-second billable session would be **$0.153** at that rate, before our hosting costs. [Model page](https://www.reactor.inc/models/helios/info). |
| Reactor session billing | Time holding the GPU is billed, including idle time after `ready` and recoverable disconnects. | Pausing generation is not stopping the meter. Terminate the owned session at the end and enforce a duration cap. [Billing](https://docs.reactor.inc/resources/billing). |
| VEED Fabric 1.0 | Help center says **$0.05 per generated second**; product page lists **$0.08 at 480p / $0.15 at 720p**, with higher Fast rates. | A ten-second standard clip is **$0.50, $0.80, or $1.50** under those conflicting published figures. Confirm the exact fal endpoint's rate; do not budget using the cheapest claim. [Help](https://support.veed.io/en/articles/15230480-veed-fabric-1-0-api), [product pricing](https://www.veed.io/ai/fabric-1-0-api). |
| VEED Subtitles | Help center lists **$0.10/minute** for basic styles up to 1080p, **$0.20/minute** for dynamic styles, and a **one-minute minimum per job**. | A 20-second replay would incur at least the applicable one-minute charge under that schedule. [Subtitles pricing](https://support.veed.io/en/articles/15230204-veed-subtitles-api). |
| OpenEdit | Editing pipeline is described as free; hosted transcription and generation have separate usage conditions. | Workstation/render time still exists. [OpenEdit help](https://support.veed.io/en/articles/16342833-how-to-use-openedit-veed-s-agent-driven-video-editor). |

Additional discrepancies to resolve before integration:

- **Fabric duration:** the help center says up to one minute per call; the product page still says 30 seconds at launch. Verify the selected endpoint's current audio-duration limit. [Help](https://support.veed.io/en/articles/15230480-veed-fabric-1-0-api), [product page](https://www.veed.io/ai/fabric-1-0-api).
- **VEED API scope:** a VEED marketing article describes a broad editing REST API, while Subtitles help says there is no full-editor API. Treat the endpoint schemas and explicitly available OpenEdit tooling as the integration evidence; do not build against the marketing example without a confirmed contract. [Marketing article](https://www.veed.io/learn/best-video-api), [Subtitles FAQ](https://support.veed.io/en/articles/15230204-veed-subtitles-api).
- **Reactor Python reconnection:** billing examples show `disconnect(recoverable=True)`, but the Sessions page says Python `disconnect()` is non-recoverable and directs callers to `reconnect()`. Pin and inspect the installed SDK before writing recovery code. [Billing](https://docs.reactor.inc/resources/billing), [Sessions](https://docs.reactor.inc/concepts/sessions).
- **Reactor current catalog rate:** the public pricing endpoint is documented, but its live JSON response could not be retrieved from this research environment. The Helios figure above comes from the model page; verify both Helios and FastH3 prices in the endpoint/dashboard before a paid comparison. [Pricing endpoint documentation](https://docs.reactor.inc/resources/billing#fetch-pricing-programmatically).

## Proposed prototype and decision test

Keep this as research until access and a trial budget are available. The following is a proposed evaluation, not completed validation.

1. Verify the selected FastH3 capture and predecessor contract with the [standard category scenarios](../../games/word-by-word/test-scenarios.md). Run `WW-CAT-01` twice and `WW-CAT-02` once, or record a named alternative from that catalog for the variation. Map the theme to Place and Scene change to Consequence for the four-slot demo, and retain the exact example answers. The older forest/fox/dancing/snow example above remains useful for diagnosing an effect addition.
2. Collect privately before opening the session. Generate and capture privately, sending only facts through the step being built. Use fixed style and minimal camera movement; withhold future assets and metadata from viewers.
3. Record startup, per-step build/capture time, visible word effects, prior details lost, transition stalls/cuts, shutdown, actual billable duration, and cost. Measure decoded media and viewer playback, not just API acknowledgements.
4. Apply the demo specification's continuity and privacy checks. Aim for roughly two minutes under the tested configuration, with a 120-second build limit and manual host reveal. These are application targets, not vendor performance claims.
5. Exercise refresh, rejected input, and one simulated provider timeout/ambiguous command. Verify bounded exits, hidden future words, saved-prefix playback, and session termination. Do not substitute model output or automatically reroll. A server restart may lose the demo room; distributed recovery is outside scope.
6. Defer Helios steering and VEED host/caption trials until after the hackathon demo works. Keep their research here without adding integrations to the demo build.

Questions for the partners: Which models/endpoint versions and credits are included? Are session spectators restricted from commands and hidden logs? What are the real quotas, current rates, recording settings, retention/deletion controls, and output-moderation options? Does VEED provide a separate live-avatar SDK for this event?

This research supports **FastH3 as the first integration candidate for the selected staged reveal**, without establishing that additive scene preservation works reliably. The [demo game spec](../../games/word-by-word/game-spec.md) and [simplified technical plan](../../games/word-by-word/tech-stack.md) record the decisions; dated live trial results must establish whether the selected implementation meets them.
