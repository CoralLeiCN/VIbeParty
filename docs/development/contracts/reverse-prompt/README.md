# Reverse Prompt game contract

The shared contract owns admission, same-origin transport, lifecycle exports, and error envelopes. The game owns its phases, role projections, private media, submissions, scoring, and persistent guard.

Implemented route prefix: `/api/games/reverse-prompt`.

| Method / suffix | Input | Result |
| --- | --- | --- |
| POST `/room` | `organizer_code`, `name`, `mode` (`rehearsal` or `live`) | Create A and Strict/HttpOnly opaque cookie; existing authenticated entry resumes. |
| POST `/join` | `code`, `name` | Claim B then C, only in lobby; fourth rejected. |
| GET `/state` | Cookie | Authorized snapshot; no identity means 401. |
| POST `/start` | `round_id` (lobby ID) | A only; three players; scorer and generation capacity ready. |
| POST `/submit` | `round_id`, `phase`, `step`, UUID `submission_id`, `text` | Immutable receipt, local validation before accepting. |
| POST `/reset` | `round_id` | A only; invalidate round before cleanup; roster preserved. |
| GET/HEAD `/media/{media_id}` | Cookie; optional Range | Authorize current role/phase before resolving local file. |

New host admission returns503 `host_not_configured` when the configured organizer code is empty, whitespace-only, or a known placeholder (`change-me`, `changeme`, `your-passcode`, case-insensitive). An explicitly supplied `ORGANIZER_CODE` overrides `HOST_PASSCODE`, including an empty override that must block admission. Invalid submitted credentials against a configured code return403.

Room codes follow [the shared standard](../../../shared/room-code-spec.md): exactly four ASCII digits stored and transmitted as strings, including `0042`. Creation uses the shared atomic `reservation.code` and `activate()` without an explicit code. Join uses the shared `RoomCode` validator and trims surrounding whitespace only; missing/non-string/malformed values return422 `Enter a 4-digit room code.` Valid unknown codes return404 `That party isn't available. Check the code with your host.` The create/join limiter runs before body validation, including malformed direct requests. The UI uses `RoomCodeInput`, the shared validator and a text field with numeric keyboard; it never pads, truncates or converts digits to a number.

Round Reset preserves the roster and code. Close party retires the lookup and membership; a new party receives a newly generated code. The game has no roster-clearing in-place reset requiring code rotation. Cookies and separate room IDs continue to authorize state/actions/media; the four-digit code alone grants none of those permissions.

Join checks the active code and closing state before reusing an existing member's session. A valid but different code returns404 even with a current cookie. A retry with the correct active code resumes that member without adding a player.

Every lobby/round has a new random `round_id`. Snapshots include `room_id`, `round_id`, monotonic `revision`, `phase`, `step`, public roster, requester role, requester accepted text, allowed media, and public progress. Only reveal includes the complete chain and both guesses. Rehearsal snapshots expose only the current player's scripted input; the label and sample-score explanation remain visible throughout.

Clue permissions: V0 only B during step1 relay; V1 only C during step2 relay; V2 everyone during guessing/scoring; all clips during reveal; no clips in other phases. Media filenames/provider URLs are never identities. GET, HEAD, full and range access all apply the same permissions with `Cache-Control: private, no-store`.

Submission receipt key is player + UUID within the current round. Same ID and normalized body returns the original receipt even after advancement; a conflicting body, occupied slot, wrong actor/phase/step, or stale round returns409. Invalid format/length/token count returns422 without a receipt or slot mutation. A cannot guess. Both B and C explicitly submit final guesses.

Reset rotates the round ID immediately, enters cleanup, cancels generation, and waits for owned work. No stale callback can publish to the new round. Uncertain provider closure keeps the persistent guard and shared blocker active; reset, party closure, restart, and game switching cannot clear it. The operator must verify termination separately.

Live generation: exactly one attempt per accepted prompt, one fresh creator-owned MiniMax FastH3 (`reactor/fast-h3`) session, model-scoped single-session token capped90s; no prior context. The persistent attempt is consumed and unresolved marker written before contacting Reactor. One failed generation ends the round unscored without exposing its private chain.

Capture uses the SDK's decoded `main_video` frames, not the optional recording service. The first120 accepted frames become five seconds at24fps in a silent H.264/yuv420p MP4 with faststart. A bounded16-frame queue fails on overflow; payload/dimension changes and invalid available timestamps fail closed. Known duplicate identities are ignored; zero metadata is treated as absent identity. The retained encoder process is killed and awaited on cancellation. Provider terminal verification and local ffprobe/decode validation must succeed before publication. No browser screen capture or automatic new-session retry is involved.

Scoring: normalized `[P0, guess_B, guess_C]` in one CPU MiniLM batch. Validate3 finite nonzero384-dimensional vectors. Rounded clamped cosine scores; exact normalized guesses100; ties share winners. Failure/15s deadline yields complete reveal with no scores/ranking. A retained inference worker prevents overlapping inference after timeout. Rehearsal uses explicitly labelled fixed sample scores.

FastH3 generation uses confirmed settings, a current-text-only enqueue for5.167 seconds, matching clip identity and generated event, then explicit playback. Compact completion messages preserve acknowledged frame metadata; a single read of the matching existing queue item can supply a missing count without another enqueue. Capture starts on its matching start event and stores the first120 frames as five seconds of silent1344×768 H.264. A short playback or ambiguous/failed command is unscored; no continuation or retry. Private media authorization applies to the saved file as before. See [provider evidence](../../../research/reverse-prompt/fasth3-switch.md).
