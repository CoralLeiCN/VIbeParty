# Word by Word API

Shared prefix: `/api/games/word-by-word`. `integration.py` exports the frozen shared boundary. Cookie: `vp_word_by_word`, HttpOnly, SameSite=Lax, Path=/, HTTP demo. Names and room codes never authorize actions. Every mutation requires the configured Origin and JSON.

| Method + suffix | Body / behavior |
| --- | --- |
| POST `/host` | `{}` in local mode; `{passcode}` when `LOCAL_MODE=false`. Creates a separate host display; the same host cookie resumes. Another browser cannot take the existing host role. |
| POST `/join` | `{code,name}`. Accepts up to the host-selected 1–4 players, join order preserved. Existing player cookie resumes even when full. |
| POST `/room/settings` | `{round_id,player_count}`. Host only, lobby only, strict integer 1–4 (default 3). Rejects a count below the joined roster, stale rounds, and pending cleanup. |
| GET `/state` | Explicit role projection below. Does not update inactivity. |
| POST `/round/start` | `{round_id,mode:"fixture"}` or live after the live gate. Requires exactly the selected player count. Freezes roster, four round-robin slots, 45-second collection. Duplicate/stale start conflicts. |
| POST `/contribution` | `{round_id,slot_index,text}`. Owner only; 1–120 Unicode code points after Unicode White_Space trimming. Same accepted text succeeds again; changed text conflicts. Fourth accepted input starts exactly one generation task. |
| POST `/reveal/next` | `{round_id,expected_reveal_index}`. Host only. Initial index -1 means Play; current expected index prevents duplicate Next advancement. After the last clip, changes to RESULTS. |
| GET `/clips/{round_id}/{index}` | Host cookie and disclosed index required, including Range requests. Saved H.264 MP4, no-store. No static media mount, no future URLs. |
| POST `/round/end` | `{round_id}`. Host cancels work, keeps only the disclosed public prefix. |
| POST `/round/new` | `{round_id}`. RESULTS only; new ID, cleared files/text, same roster order and selected player count. Blocks active generation/unconfirmed closure. |
| POST `/room/reset` | `{round_id}`. LOBBY/RESULTS; clears roster/replay, rotates resolver code atomically, keeps host cookie and selected player count. Same guards. |
| POST `/provider/cleanup` | `{round_id}`. Host retries only unpaid cleanup after generation ended; cannot generate. |
| POST shared `/api/party/close` | Host auth, guarded cancellation/closure, private cleanup, then shared admission release. Unconfirmed closure returns `closing`. |

A snapshot includes role, room code/join URL, ordered public names, selected `player_count`, `round_id`, monotonic room `revision`, phase/mode, server time and fixed deadlines, collected count, saved count, highest disclosed index, result/message, cleanup flags and remaining live attempts. The **host** gets only disclosed cards and disclosed clip URLs. A **player** additionally gets only their own assignments/accepted text; never clip URLs. Credential/provider IDs, prompts, raw frame data and file paths are never returned.

Before Play, even a completed generation has `cards:[]`, `clips:[]`, `disclosed_index:-1`. After the first Play:

```json
{"cards":[{"index":0,"category":"Place","text":"a moonlit forest","contributor":"Ada"}],"clips":[{"index":0,"url":"/api/games/word-by-word/clips/example-round/0","duration":6}],"disclosed_index":0}
```

Only a player's own assignment contains `fixture_text` during the explicit fixture rehearsal. Its fixed contributions are `a moonlit forest`, `a fox in a tiny hat`, `They start breakdancing.`, and `Confetti rains from the sky.` in category order. Arbitrary fixture input is rejected; no live failure falls back to fixtures.

State-changing decisions use the game lock. Shared coordinator calls and provider/file I/O occur outside it. Generation, cleanup, deadline and expiry tasks are retained. Total generation is bounded at 120 seconds, per-step at 30 seconds; no paid retry. The live attempt counter belongs to the Game/process, not the room, so close/reset never replenish it. Initial live gate is explicitly blocked pending real capture evidence and an operator-granted trial slot.

## Four-digit room codes

Word adopts `docs/shared/room-code-spec.md` and the shared helpers. All codes are four ASCII digit strings, including `0042`. Creation uses `reservation.code`/`activate()`, same-roster rematches keep it, and roster-clearing reset uses `parties.rotate_code(game_id)` to retire the previous lookup atomically. The join endpoint first rate-limits the request, then passes the raw JSON code to shared `normalize_room_code`; missing/non-string/malformed codes return422 with the exact shared format message, without coercion. Browser joining uses `RoomCodeInput` and normalization before POST, preserves invalid text for correction, and does not auto-join a supplied link.
