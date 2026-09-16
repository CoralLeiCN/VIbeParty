# Word by Word starting images: WBW-001/002/003

Date: 16 September 2026. Scenario: **WW-CAT-01**, current four-slot demo.

The host chooses the image source in the live lobby for each round. Upload, Codex, API and configured-file sources are independent. Source selection is locked once collection starts. Generation begins after all four answers are accepted, using only the first joined player's Place answer.

## Real Codex verification

Codex CLI `0.153.4` reported an existing ChatGPT login and enabled image generation. An initial isolated `codex exec` experiment produced an image. The implemented `CodexImageGenerator` then completed one independent run using its actual schema, restricted environment, tool restrictions, timeout, artifact validation and cleanup. No OpenAI API key was supplied and the login was not modified.

- Place: `Enchanted forest`.
- Prompt: fixed wide illustrated establishing-scene instructions, no main character or story event, no text/captions, followed by the Place answer as JSON scene data. No Character, Action or Consequence answer entered the image request.
- Output: `.local/wbw-verification/seed.png`, 1536×1024 PNG, 3,065,380 bytes, completed in 49 seconds. This private artifact is not committed.
- Inspection: illustrated forest clearing with room for a character; no fox, ballet, or falling snow. This observation is not a video-quality evaluation.
- The adapter copied and validated the artifact into its requested directory and removed the invocation's original generated-image directory.
- [Sanitized artifact metadata and checksum](evidence/2026-09-16-starting-images.json).

The image was generated using Codex's built-in image tool. Its fixed prompt is defined in `backend/games/word_by_word/images.py:image_prompt`; the final scene-data value was `"Enchanted forest"`.

## Browser rehearsal

An isolated server on localhost:8017 used the real application UI, API, room rules, image validation and `LingBotProvider`, with fake Reactor HTTP/SDK and capture adapters. It showed a persistent “WW-CAT-01 browser rehearsal — simulated video transport” label. This server made no real Reactor request.

One player, Ada, owned Place, Character, Action and Consequence. The host selected Live LingBot World 2, checked the Codex-ready explanation, selected the unavailable API option, then selected Upload. The following checks passed:

1. Start was disabled until the source was ready and the selected player had joined.
2. The host uploaded the real Codex-generated forest PNG through the file chooser. The private preview and “Image ready for this round” appeared; Start became enabled.
3. After host refresh, choosing live mode again restored the selected upload and preview.
4. The accepted answers were submitted in order **Consequence → Action → Character → Place**, using the exact standard texts: `Glowing snow begins falling`, `Dances ballet`, `A fox wearing a crown`, `Enchanted forest`.
5. The provider evidence recorded `seed_source: upload`, four ordered steps and confirmed simulated closure. The results displayed the exact accepted answers in Place → Character → Action → Consequence order.
6. Another round kept the player, reset the source choice to Codex and removed the old upload. Selecting Upload again required a new image and kept Start disabled.

The fake capture deliberately does not supply playable video, so a playback error in this rehearsal was expected. Live video quality and replay were not evaluated. The server and browser tab were stopped after verification.

## Automated verification

The backend tests exercise:

- Host-only upload, preview and source selection; Origin protection; 10 MiB request cap; stale-round rejection; locked selection after start; rematch cleanup.
- Real image decoding for JPEG, PNG and WebP, phone-photo orientation, metadata removal, corrupt/unsupported content, animation and pixel limits.
- Explicit source precedence, including ignoring a configured image when Codex or API was selected; image acceptance before video start.
- Place-only generation after reversed submission order, with the later answers remaining private on preparation failure.
- A real local test subprocess exercising the Codex argv/stdin/schema protocol, output-file boundaries, missing output, failed execution, timeout, cancellation, process termination, artifact cleanup and credential filtering.
- Distinct readiness messages for missing CLI, missing ChatGPT login and unavailable image support.

`UV_CACHE_DIR=/tmp/wbw-uv-cache bash scripts/check.sh` passed: Ruff checks and formatting, frontend lint/build, and **231 backend tests**. The focused Word by Word suite has **59 passing tests**. Existing warnings were the frontend bundle-size advisory and FastAPI/Starlette test-client deprecations. The browser rehearsal above covers the visible changes.

No live LingBot session or OpenAI Images API request was run for this change. Their protocol ordering is covered with mocks; the earlier online LingBot results remain in [the continuous-flow record](2026-09-16-lingbot-continuous-flow.md). Actual billing/usage consumption for the two Codex image runs was not measured.
