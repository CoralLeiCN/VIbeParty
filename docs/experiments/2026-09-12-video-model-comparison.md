# Helios vs FastH3: price, generation speed, and 480p

Researched 12 September 2026. Repository revision: `7b6303b`. Scope: the two scene-generation models currently used by VibeParty, using the existing Reactor account, with 480p sufficient for viewing quality.

**Finding:** Helios costs **$0.102 per session minute** and FastH3 costs **$0.42**, making FastH3 **4.12× the price for equal billable time**. Neither API documents an exact native 480p generation setting. Helios can emit its native **640×384** with super-resolution disabled; FastH3's landscape canvas is **1344×768**. Producing a 480p file by resizing that output does not create a cheaper provider rate. [Live pricing API](https://api.reactor.inc/pricing), [Helios schema](https://docs.reactor.inc/model-api-reference/helios/schema), [FastH3 schema](https://docs.reactor.inc/model-api-reference/fast-h3/schema).

**Speed conclusion:** there is enough evidence to compare price, but no measured Helios/FastH3 speed winner at 480p. Earlier FastH3 trials show short clip builds taking approximately 3.4–6.0 seconds after setup, with additional startup and capture time. One earlier five-second export completed in 16.49 seconds. Those are historical measurements at the provider's larger canvas, not a new 480p benchmark. Helios has no successful live timing result in the checked repository. See the timing table below.

## Models in this project

| Model | Current use | Source |
| --- | --- | --- |
| `reactor/helios` | Prompt Royale; streaming scene generation, currently requesting `sr_scale: "2x"` | [Helios adapter](../../backend/games/prompt_royale/helios.py) |
| `reactor/fast-h3` | Word by Word; connected clips with predecessor conditioning | [Word by Word adapter](../../backend/games/word_by_word/live.py) |
| `reactor/fast-h3` | Reverse Prompt; independent clips in a session retained through relay turns | [Reverse Prompt adapter](../../backend/games/reverse_prompt/reactor_video.py) |

VEED/Fabric appears in older research as an optional presenter asset service. It is not one of the two scene generators implemented above.

## Existing account checks

At **15:45:42 UTC**, the public Reactor pricing endpoint returned the rates saved in [pricing.json](evidence/2026-09-12-video-models/pricing.json). The existing root `.env` credential then returned HTTP 200 and a JWT for each model's separately scoped token request. Each request specified one allowed session, a 60-second maximum session duration, and a 60-second token expiry. No JWT or API key was saved in these documents. [Sanitized account preflight](evidence/2026-09-12-video-models/account-preflight.json).

Token issuance verifies that the credential works and those token restrictions were accepted. It does **not** establish GPU availability, a positive credit balance, successful video generation, or an account-specific discount. The available browser displayed a signed-out Reactor page. The billing documentation directs users to the dashboard for balance and spend; programmatic usage reporting is still described as forthcoming. Account balance, actual settled spend, and account-wide active sessions therefore remain unverified. [Billing and usage tracking](https://docs.reactor.inc/resources/billing).

This investigation has opened **zero video sessions** and submitted **zero generation requests** so far. The resolution question is pending: whether “480p only” permits generation at the models' supported resolutions followed by a 480p export. Until that is answered, this report contains current research and earlier measurements, without claiming a new generation benchmark.

## Pricing

The live response uses USD and 10,000 credits per dollar:

| Billing unit | Helios | FastH3 |
| --- | ---: | ---: |
| Credits per session second | 17 | 70 |
| USD per session second | $0.0017 | $0.0070 |
| USD per session minute | $0.102 | $0.420 |
| USD per session hour | $6.12 | $25.20 |
| 10 seconds of billable session time | $0.017 | $0.070 |
| 30 seconds of billable session time | $0.051 | $0.210 |
| 60 seconds of billable session time | $0.102 | $0.420 |

The first two rows are observed rates; the remaining rows are arithmetic. The public model pages agree with the API. FastH3's page also shows a struck-through former price of $0.75/minute; use the current $0.42 rate. [Pricing snapshot](evidence/2026-09-12-video-models/pricing.json), [Helios price](https://www.reactor.inc/models/helios/info), [FastH3 price](https://www.reactor.inc/models/fast-h3/info).

Billing begins at `ready`, continues during generation, playback, and idle time while the GPU is held, and ends when the owned session terminates. Connecting/waiting time is not billed. The calculation is `billable session seconds × model rate`; five seconds of saved video does not determine the charge. No separate resolution tier appears for either model in the captured catalog. [Billing rules](https://docs.reactor.inc/resources/billing).

At equal session duration, choosing Helios reduces the listed model charge by **75.7%**. FastH3 would need to use less than **24.3% of Helios's billable time** for the same job to cost less. This is a break-even calculation, not an observed speed advantage.

For the current Reverse Prompt flow, keeping FastH3 ready throughout both 30-second thinking turns adds approximately **$0.42 per round** in idle usage alone, before generation and capture. This follows from the [current retained-session design](../research/reverse-prompt/session-reuse.md) and the live rate. Closing between turns would trade that idle cost for reconnect latency; it is a possible later design decision, not a change made by this research.

## What 480p means for these APIs

| Requirement | Helios | FastH3 |
| --- | --- | --- |
| Exact native generation at 480 pixels high | No documented setting | No documented setting |
| Native output at or below 480 pixels high | **640×384**, using `set_sr_scale({"sr_scale": "off"})` | No documented landscape option |
| Current application output | 1280×768 through 2× super-resolution | 1344×768 |
| Controls exposed by the model | Super-resolution `off`, `2x`, `4x`; native model generation stays 640×384 | `set_canvas` selects aspect (`16:9`, `1:1`, `9:16`, `4:3`); no documented arbitrary pixel resolution parameter |
| Possible 480p viewing file | Scale 640×384 to **800×480**, preserving 5:3 | Scale 1344×768 to **840×480**, preserving 7:4 |
| Effect on listed provider rate | No separate cheaper rate documented | No separate cheaper rate documented |

Sources: [Helios overview](https://docs.reactor.inc/model-api-reference/helios/overview), [Helios super-resolution command](https://docs.reactor.inc/model-api-reference/helios/schema#set_sr_scale), [FastH3 canvas command](https://docs.reactor.inc/model-api-reference/fast-h3/schema#set_canvas).

FastH3 labels the landscape preset `16:9`, but 1344÷768 is **7:4**. Preserve the actual pixel geometry when exporting; do not stretch it to 854×480. If a standard 854×480 player is required, letterbox the resized frames. Helios's native image is below 480p; scaling it to 480 pixels high adds no native scene detail.

For a cost-focused low-resolution trial, Helios with super-resolution off is the available candidate. Avoiding its 2× enlargement may reduce transport and local processing work, but any generation-speed improvement must be measured. FastH3 can supply a 480p viewing file only through a separate resize in the documented workflow; that still uses its supported larger generation canvas.

## Generation speed: published claims and existing measurements

Reactor describes Helios as a real-time continuous stream. It emits chunks of 33 frames at 24 fps: **1.375 seconds of video per chunk**. That describes media duration, not time to build a chunk or time to the first useful frame. [Helios overview](https://docs.reactor.inc/model-api-reference/helios/overview), [Helios specifications](https://www.reactor.inc/models/helios/info).

FastH3's model page advertises approximately **1.0× real-time generation**, 24 fps, and clips between 5.167 and 14.375 seconds. Its banner also says “2× faster”; neither claim is a measured first-request latency for this account. A completed clip must then be played and captured to produce the MP4 used by our games. [FastH3 specifications](https://www.reactor.inc/models/fast-h3/info), [FastH3 workflow](https://docs.reactor.inc/model-api-reference/fast-h3/overview).

The repository contains these real FastH3 trial results from earlier on 12 September. They used SDK 1.5.1 and the larger landscape output. “Total” follows the original trial's timing boundary; it is not the billable duration.

| Earlier trial | Startup/setup | Clip build after setup | Total attempt | Saved result |
| --- | ---: | ---: | ---: | --- |
| [Word 001](../research/word-by-word/evidence/2026-09-12-word-001.json) | 8.407 s | 4.522 s | 14.066 s | Capture gate rejected missing frame count; no saved clip |
| [Word 002](../research/word-by-word/evidence/2026-09-12-word-002.json) | 5.985 s | 5.958 s | 12.728 s | Capture rejected absent frame IDs; no saved clip |
| [Word 003](../research/word-by-word/evidence/2026-09-12-word-003.json) | 7.549 s | 4.387 s | 38.415 s | 156/158 frames received; capture timed out; no valid export |
| [Reverse 001](../research/reverse-prompt/evidence/2026-09-12-reverse-001.json) | 7.051 s | **3.409 s derived** | **16.490 s** | Valid silent five-second MP4, 120 captured frames from a 124-frame clip, 1344×768 |

For Reverse 001, the stored `generated_seconds: 10.460` runs from attempt start and **includes** its `startup_seconds: 7.051`. Subtracting them yields 3.409 seconds for enqueue/build after setup; it is not a directly recorded model-only inference timer. Completion was 10.460 seconds from attempt start. The [trial report](../research/reverse-prompt/fasth3-switch.md#first-real-capture) records successful full decode and sampled frames showing the requested red balloon moving past a blue tower. Actual settled spend was unmeasured.

The next [Reverse 002 attempt](../research/reverse-prompt/evidence/2026-09-12-reverse-002.json) failed before saving the first clip, with no usable timing diagnosis. It must remain visible as a failed attempt, but cannot contribute a speed number. These trials are a small integration-debugging sample with different prompts and capture paths, so they do not establish a production failure rate, average latency, or percentile.

Prompt Royale's [Helios laptop spike](../research/prompt-royale/laptop-spike.md) verifies offline SDK compatibility only and explicitly leaves live capture pending. A valid measured Helios build time or comparison ratio cannot be inferred from it.

## Reproducible next comparison

If 480p is a delivery requirement and resizing is accepted, run an isolated comparison using the existing key, keeping production model selections unchanged:

1. Use Helios at `sr_scale: "off"` and FastH3 at its supported landscape canvas. Save the actual source dimensions as well as the final 480-pixel-high dimensions. Keep audio out of the viewing files; FastH3 still generates audio jointly, so this does not establish a provider discount.
2. Use the [standard scenario instructions](../games/word-by-word/test-scenarios.md), scenario **WW-CAT-01**, and the existing four-slot mapping: **Place → Character → Action → Consequence**. Exact contributions: `Enchanted forest`, `A fox wearing a crown`, `Dances ballet`, `Glowing snow begins falling`. Use the project's [cumulative prompt assembly](../../backend/games/word_by_word/providers.py), preserving capitalization and omitting future contributions from earlier steps. Record seed 42 if supported, SDK version, and the actual accepted clip length.
3. Apply the four additions in order. For FastH3, use the previous clip's ID for continuity; for Helios, update the continuous scene prompt after the previous addition is visibly established. These are model-specific workflows, so report that difference rather than treating their event timers as identical.
4. Record separate times for request-to-ready, prompt/enqueue-to-first-relevant-frame, prompt/enqueue-to-build-complete where exposed, capture duration, 480p export preparation, and time to a validated playable file. For Helios, distinguish generated chunk events from delivered frames. For FastH3, distinguish `clip_generated` from playback. Record closed-session proof and ready-to-terminal time for estimated cost.
5. Review each reveal at 480p: forest recognizable; crowned fox appears; same crowned fox performs ballet; luminous snow appears while the fox, crown, action, and forest remain visible. Record missing details and visible stalls. The earlier red-balloon test does not establish these results.
6. Start with one four-step session per model, run serially, and do not retry ambiguous submissions. Limit each provider session to 120 seconds and terminate the owned session on completion or failure; independently confirm CLOSED/INACTIVE or 404 before another session. At the current rates, two sessions each held ready for the full cap would cost **$1.044 combined**. This is a proposed trial ceiling based on enforced duration, not money already spent or a committed quote.
7. A successful single pair is an exploratory result. For the existing Word by Word acceptance sequence, subsequently run **WW-CAT-01 twice and WW-CAT-02 once per model** and report individual values, medians, and ranges. Those runs would have a combined model-time ceiling of **$3.132** at 120 seconds per session. They would still be too small for a defensible p95. Further paid samples require an agreed scope.

If the requirement is strictly native generation at 480p or below, Helios at 384p is the only documented option among these two. The FastH3 cell should remain **unsupported**, rather than being populated with a resized 768p timing.

## Decision and limitations

**For lower cost and adequate small-screen resolution, prioritize evaluating Helios at native 384p with super-resolution off.** Its listed session rate is 75.7% lower, and it avoids producing enlarged frames for a small viewing target. This is a price-and-resolution recommendation; a successful live capture and visual review are still required before relying on it in the demo.

**FastH3 remains the current choice where the app uses explicit queued clips and predecessor continuation.** One earlier short export succeeded, while other integration trials failed. Keeping its API for those flows avoids assuming Helios is a drop-in replacement. A 480p export alone would reduce local file/transfer size, with no documented change to FastH3's generation rate.

New head-to-head timing, 480p visual acceptance, provider balance and settled costs remain open. The account preflight and current price snapshot are complete. This report makes no application configuration changes.
