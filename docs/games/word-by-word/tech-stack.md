# Word by Word: technical stack

[Game specification](game-spec.md) · [Test scenarios](test-scenarios.md)

Updated 16 September 2026 for one continuously streamed LingBot World 2 story.

## Runtime

One FastAPI process owns room state, accepted contributions, the model session, timing, and media. React uses the existing cookie-backed API and polls once per second. The host plays one HLS presentation through hls.js, with native HLS as a browser fallback; phones show contribution forms and revealed cards.

The backend uses the existing pinned `reactor-sdk==1.5.1`. `StreamCapture` retains at most one decoded BGRA frame and sends paced 24-fps output to FFmpeg. Output is silent H.264/yuv420p with one-second keyframes and an event HLS playlist. Source bursts replace the retained frame and short gaps repeat it. The encoder has a ten-second source-stall limit, five-second pipe timeout, and a bounded round lifetime. It does not evaluate picture quality.

FFmpeg atomically publishes transport fragments and the playlist inside the private round directory. At completion it closes the playlist and remuxes it to `story.mp4`. The browser keeps the HLS source through the final buffered frames, then Replay selects the one MP4. Source media is limited to 1920×1080 and replay to 80 MiB.

## Configuration

```dotenv
REACTOR_API_KEY=...
WORD_BY_WORD_LIVE_ENABLED=true
OPENAI_API_KEY=...
WORD_BY_WORD_IMAGE_MODEL=gpt-image-2.5-flare
WORD_BY_WORD_CATEGORY_SECONDS=6
```

The OpenAI Images API produces one PNG from Place alone before opening Reactor. No later answers enter that request. Generation uses low quality, landscape dimensions, and no automatic retries. For a known development setting, `WORD_BY_WORD_SEED_IMAGE` can instead point to an existing image matching Place; relative paths resolve against this worktree. Do not include future contributions in that image. The live option reports missing configuration in the lobby.

Keep credentials on the backend. No new user permission or visual-approval step is part of the game.

## Provider sequence

1. Prepare the starting image; open one token-scoped `reactor/lingbot-world-2` session.
2. Upload the image and await `image_accepted`.
3. Send the Place prompt and await `prompt_accepted`; send `start` once and await `generation_started`.
4. Publish the stream after its first HLS fragment is available. Record Place at media time zero.
5. At each interval, send the complete scene description through the next category. Keep generation active throughout. Await prompt acceptance and record the update's media offset.
6. After the final interval, pause generation, finalize the recording, and close the provider. Verify CLOSED/INACTIVE or 404 using the session API; a disconnect acknowledgment alone does not clear the closure guard.

The prompt builder uses only accepted answers through the current category, fixed illustrated style, a wide camera, and continuity instructions. It never truncates the 120-code-point answers. SDK `command_error` events, command timeouts, and transport errors stop the run. There is no vision evaluator or quality retry.

[Reactor model contract](https://www.reactor.inc/models/lingbot-world-2/api) · [OpenAI image API](https://developers.openai.com/api/docs/guides/image-generation)

## State and API

`LOBBY → INPUT → GENERATING → STREAMING → RESULTS`. The provider task advances categories and phase on the server. Host refresh and phone polling are read-only and cannot duplicate generation.

`Round` stores the disclosed index, category media offsets, whether a stream is published, and an optional single recording. Public snapshots are explicitly assembled; undisclosed text never enters host snapshots or other players' assignments. Original accepted text and contributors are retained on the cards.

| Endpoint | Purpose |
| --- | --- |
| `POST /host`, `/join` | Cookie-backed admission. |
| `GET /state` | Role-specific state, disclosed cards, and host playback URLs. |
| `POST /room/settings`, `/round/start` | Player count and round start. |
| `POST /contribution` | Private, owned, idempotent contribution submission. |
| `POST /round/end`, `/round/new`, `/room/reset` | Cancel, rematch, and reset. |
| `POST /provider/cleanup` | Retry independent closure confirmation. |
| `GET /media/{round_id}/{filename}` | Host-only playlist, published HLS fragments, or finalized MP4. |

The `/reveal/next` and per-clip endpoints are removed. Media filenames are allowlisted; seed images, temporary files, obsolete round IDs, traversal paths, and missing/future fragments cannot be fetched. Media routes preserve Range support and no-store caching. There is no static media mount.

## Verification

`backend/tests/word_by_word` covers the session protocol with a fake Reactor, place-only image input, ordered updates, rejected commands, cancellation, independent closure, real FFmpeg streaming/recording, room rules, and private media routes. The WW-CAT-01 fixture supplies one scripted 24-second video. Browser checks verify automatic playback, refresh, all four categories, replay, and mobile cards. Visual quality of generated content is not an acceptance gate.
