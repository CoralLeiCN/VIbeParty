# LingBot World 2 continuous flow: functional verification

Date: 16 September 2026. Scenario: **WW-CAT-01**, categories-v1.

The user requested one continuous video with automatic category inputs and explicitly excluded visual-quality evaluation. This record covers fixture checks and two successful online LingBot runs, including a complete browser round. Generated visual quality was not evaluated.

## Inputs and flow

One-player fixture round, separate host/player cookies via localhost and 127.0.0.1. Ada owned Place, Character, Action, and Consequence. The browser used the standard category instructions and exact answers:

- Place: Enchanted forest
- Character: A fox wearing a crown
- Action: Dances ballet
- Consequence: Glowing snow begins falling

The scripted video is `backend/games/word_by_word/fixtures/story.mp4`, one 24-second recording with categories at 0, 6, 12, and 18 seconds. It is labelled FIXTURE REHEARSAL / WW-CAT-01 in the app.

## Observed browser results

- Category instructions/examples, submission locking, and private collection: pass.
- All four submissions automatically started one video, without Play/Next/Finish buttons: pass.
- The initial running video reported currentTime 7.50 seconds, paused=false, readyState=4, with no media error.
- Place → Character → Action → Consequence advanced automatically; the phone followed disclosed cards and had no video player: pass.
- Host refresh retained the party and round. After the final refresh improvement, a running round resumed at 18.16 seconds, paused=false, during Consequence: pass.
- Completion reached RESULTS automatically with all four exact answers and contributor names: pass.
- Replay selected the single `story.mp4`; it reported duration=24, currentTime=6.41, paused=false, with no media error: pass.
- Another round retained the same room code, one player, and all four assignments; automatic playback worked again: pass.
- No live provider or image-generation requests were made. Physical phones and generated visual quality were not evaluated.

## Automated results

- Final `UV_CACHE_DIR=/tmp/wbw-uv-cache bash scripts/check.sh`: **206 backend tests passed**, plus Ruff lint/format, frontend ESLint, TypeScript, and production build. This ran after incorporating `main` commit `15629ec`. The existing Prompt Royale tokenizer was restored with its checksum verified.
- Additional checks: Ruff for `scripts/games/word-by-word`, formatting, `git diff --check`, and full FFmpeg decoding of both online recordings passed.
- The spike runner now rejects a saved partial recording after a failure and rejects unconfirmed closure. Three regression cases cover these outcomes and the successful case.
- Ruff lint and format checks: pass. Frontend ESLint and production TypeScript/Vite build: pass. Vite reports its bundle-size advisory after adding hls.js.
- `PORTAL_URL=http://localhost:8057 DEMO_HOST_CODE=test-pass npm --prefix frontend run test:portal`: **6 passed** (16.9 s).
- `PORTAL_URL=http://localhost:8057 DEMO_HOST_CODE=test-pass npm --prefix frontend run test:integration`: **2 passed** (41.2 s), including the three-game sequence, continuous Word by Word playback/refresh/replay, cleanup, and fresh joins.
- `ROYALE_URL=http://localhost:8058 ROYALE_LIVE_E2E=0 frontend/node_modules/.bin/playwright test --config frontend/src/games/prompt-royale/e2e/playwright.config.ts`: **3 passed** (1.3 min), all fixture mode.
- The combined suite initially stopped at Reverse Prompt because the isolated server lacked its scoring-model path; a second invocation started before model warm-up finished. After setting the prepared model path and verifying `/health/ready`, the full suite passed. No application change was needed for these setup failures.
- Frontend Vitest command exits successfully with no unit test files; this is not counted as unit coverage.
- Provider mocks confirm one model-scoped session, one image upload/start, four cumulative prompt updates, automatic pause, saved recording, command-error handling, cancellation, and independent closure. They also verify that only Place enters image generation and future answers stay out of earlier prompts.
- HTTP tests verify host-only HLS/MP4 access, Range requests, stale rounds, seed-file exclusion, and removed manual-reveal endpoints. Real FFmpeg checks verify HLS publication, final ENDLIST, one decodable recording, and a saved interrupted prefix.

## Provider setup

LingBot model: `reactor/lingbot-world-2`, Python SDK 1.5.1. Default category interval: six seconds. The initial image comes from Place using `gpt-image-2.5-flare`, or an explicit local `WORD_BY_WORD_SEED_IMAGE` development override.

Reactor's current public model catalog and documentation index did not expose a still-image generation API. The implementation therefore retains the separate seed-image generator. Sources checked: [Reactor model catalog](https://www.reactor.inc/models), [documentation index](https://docs.reactor.inc/llms.txt), [LingBot World 2 contract](https://www.reactor.inc/models/lingbot-world-2/api), and [OpenAI image generation](https://developers.openai.com/api/docs/guides/image-generation).

## Online results

**Pass: two online WW-CAT-01 runs.** Each used one real LingBot session and the four exact standard answers. Both sessions were independently confirmed closed before completion was reported. The protocol trial ran first; the browser trial ran only after its closure. No quality retries or further live sessions were made. Actual spend was not measured.

1. Protocol trial `lingbot-online-20260916-01`: all four updates at 0, 6.292, 12.542, and 18.833 seconds; generation completed, one 25.000-second MP4 saved, exit status 0, closure confirmed. Private raw evidence remains under `.local/word-by-word-live-2026-09-16/trial-01/`.
2. Browser trial: one player named Live Tester owned all four slots. Submitted Consequence → Character → Place → Action through the browser forms. Accepted values locked; the host showed only 3/4 participation during collection. The fourth submission automatically started one live stream. Initial playback reported currentTime=4.623, paused=false, readyState=4, no media error. The round completed automatically with all four cards. The buffered tail continued through RESULTS (currentTime=24.253, duration=25.125, paused=false). The phone showed the four disclosed cards and no video. After closure and host refresh, Replay selected the one saved MP4 (duration=25.125, currentTime=0.307, paused=false, readyState=4, no media error). Host console warnings/errors: none.

The browser test used an isolated local server on port 8056 with separate localhost/127.0.0.1 cookies. This verifies the app's real provider path and replay, not physical-phone networking. The earlier fixture test also verified refresh during active streaming and rematches.

| Category | Accepted prompt / update time in the browser recording |
| --- | --- |
| Place | Enchanted forest / 0.000 s |
| Character | A fox wearing a crown / 6.417 s |
| Action | Dances ballet / 12.625 s |
| Consequence | Glowing snow begins falling / 18.917 s |

These timestamps mark accepted prompt updates, not measured visual response latency. Visual effects and quality are outside acceptance as requested.

Saved result: [continuous live video](evidence/2026-09-16-lingbot-ww-cat-01.mp4), [sanitized evidence](evidence/2026-09-16-lingbot-ww-cat-01.json), and [starting image](evidence/2026-09-16-lingbot-seed.png). The MP4 is 8,389,890 bytes and fully decodes with FFmpeg. Raw session identifiers, credentials, cookies, and test logs are excluded from tracked evidence.

Both runs used the supported `WORD_BY_WORD_SEED_IMAGE` override. The built-in imagegen tool generated the seed from Place only; the app's automatic OpenAI image endpoint was covered by protocol tests but was not called online because no OpenAI API key was configured. Normal live play needs an OpenAI key or a matching configured image.

Seed-generation prompt (built-in tool):

> Use case: illustration-story. Asset type: starting image for a LingBot World 2 continuous video test, scenario WW-CAT-01. Primary request: Enchanted forest. Wide landscape establishing shot of an enchanted forest clearing, playful illustrated style, fixed wide camera, room for a character to enter later. Depict only this setting. No main character, no animals, no story event, no snowfall, no text, no captions, no logos. Save the resulting image for use as the video seed.
