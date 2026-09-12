# Prompt Royale fixture rehearsal — 12 September 2026

Passed on this macOS arm64 laptop using Chromium / Playwright 1.63.0. These are
fixture and mocked-provider results. No real Helios or topic API request was made.

The full-round browser scenario creates separate playing-host and guest contexts,
first with three players and bundled topics, then four players and a simulated LLM topic.
It verifies regeneration clears confirmation, confirms a fresh suggestion, submits private
scenes, refreshes an unsent draft, checks anonymous stable arena snapshots, and plays all
three/four videos concurrently. After a full group loop, playback is still active and video
positions differ by less than 350 ms. Pause all and Replay all work. A guest refresh retains
tile positions. The four-player flow excludes one clip without moving the other positions,
votes, reaches results, plays again with cleared topic state, and ends the room.

The LAN run also clicked Copy link successfully on non-loopback HTTP, recovered a failed
video response using Retry playback, and retried a simulated NotAllowedError from play().
No uncaught page errors occurred. Desktop viewport: 1280×900; phone layout viewport: 390×844.
This phone-sized Chromium context is not physical Safari/iPhone validation.

Runs:

- localhost:5175: full flow passed after fixing normal seeking incorrectly treated as a stall.
- localhost:5175 after shared portal merge: passed, 29.3 seconds.
- http://10.0.100.107:5175: expanded failure/copy/exclusion flow passed, 29.7 seconds.
- Same LAN origin with the shared room-code migration: three/four-player full flow passed
  in 30.1s with controlled `0042`, manual portal entry, copied/direct game links, surrounding
  whitespace, host refresh, portal continuation and Play again retaining the same code.
  Closing removes the lookup. Both topic modes and coordinated playback still pass.
- A focused admission scenario passed in 1.4s: invalid input stays editable, exact format and
  unavailable messages appear, corrected input joins, and `/join?code=0042` prefills the game
  form without creating membership until the player submits their name.

For controlled browser rehearsal only, the fixture backend was launched with a temporary
`unittest.mock.patch('backend.shared.party.generate_room_code', return_value='0042')` around
`uvicorn.run`, after asserting `Settings().generation_mode == 'fixture'`. There is no production
code override or fixed-code environment setting. `ROYALE_EXPECT_CODE=0042` enables the
browser assertion. The normal backend was restored after rehearsal; API tests instead patch
`secrets.randbelow` to exercise actual shared generation while preserving leading zeros.

The first run after npm replaced the shared dependency tree showed a blank Vite page.
Restarting Vite with `npm run dev -- --force` resolved the stale optimizer state. This was
an environment issue; the production build also passes.

## Evidence

- [Three-player arena](evidence/three-player-arena.png)
- [Four-player arena](evidence/four-player-arena.png)
- [Phone layout](evidence/phone-layout.png)
- [Results with exclusion](evidence/results.png)
- [Editable room-code error](evidence/room-code-error.png)

The fixture files are original FFmpeg synthetic patterns. Each is a five-second, silent,
1280×768 H.264/yuv420p MP4 with faststart. They are visibly labelled and do not claim to
represent submitted scenes. Their SHA256 values can be regenerated from the committed
files; `build_fixtures.py` reproduces the media pipeline without network/provider calls.
