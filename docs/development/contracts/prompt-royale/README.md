# Prompt Royale API contract

Base `/api/games/prompt-royale`; foundation shared.md defines HTTP origin, JSON, error,
party admission and HttpOnly cookie contracts. Cookie `vp_prompt_royale`, Path=/, SameSite=Lax.

Create: `POST /room` with `{name,passcode}`. Join: `POST /room/join` with `{name,code}`.
Both return an authorized snapshot and opaque cookie. Snapshot: `GET /room`.
Names and room codes never authorize private state or media. Host is also a player.
Room codes follow the shared standard: exactly four ASCII digits as strings, including `0042`.
Creation consumes atomic `reservation.code` and calls `activate()` without an override.
Join throttling runs before `normalize_room_code`, so invalid/non-string attempts also count;
format errors return 422 with the shared message. The shared numeric-keyboard text input
preserves editable raw input, then normalization trims surrounding whitespace before POST.
Refresh, continuation and Play again retain code and roster. End room/expiry retire lookup
and sessions after cleanup. This game has no separate roster-clearing reset; a new party
receives a new allocation, and retirement permits code reuse without restoring membership.

Host commands carry `{command_id,expected_version,round_id}` (round_id null in lobby).
Command IDs deduplicate accepted commands; reuse with changed details conflicts.
Commands return current snapshots, with monotonic revisions scoped to boot_id and room_id.
All host commands require the playing host's cookie.

| Suffix | Additional fields | Allowed phase |
| --- | --- | --- |
| `/room/topic` | mode: bundled or llm; optional bundled topic | lobby |
| `/room/topic/generate` | none | lobby |
| `/room/topic/confirm` | suggestion_id | lobby |
| `/room/start` | none | lobby, confirmed topic and 3–4 present players |
| `/round/exclude` | entry_id, public reason | screening |
| `/round/open-voting` | watched: true | screening |
| `/round/abort` | none | active round |
| `/round/again` | none | results |

Player `POST /round/submission`: `{round_id,prompt}`. Player `POST /round/vote`:
`{round_id,entry_id}` where explicit null means abstention. An exact repeat returns its
accepted confirmation; changed submissions/ballots conflict. Self-votes, excluded targets,
stale rounds and newly arriving ballots at or after the deadline are rejected.

`DELETE /room` with JSON `{}` and the host cookie performs cancellation, independent provider
closure verification, private file/session cleanup, then shared admission release. Returns
`{status:closed|closing,message}`. The same operation is available through shared party close.

Snapshots expose `boot_id,revision,version,server_time,room_id,code,join_url,mode,topic_source,
phase,players,me,round_id,seconds_left,topic,closing,cleanup_pending`. Lobby topic state is
host-only. `me.prompt` and `me.vote` contain only the caller's accepted input. Generation
progress is aggregate status counts; there are no author-to-entry or clip mappings yet.

Screening/voting/results add exactly four arena tiles with fixed position and label. Ready
tiles have opaque `id,url`; empty tiles have neither; excluded tiles retain id/position and
public reason but lose URL. Only voting includes private `own` flags. Only eligible results
tiles add author, prompt, votes and winner. Individual ballots never become public.

Media: `GET /media/{opaque_id}`. Authorized current members can read complete eligible media
only in screening/voting/results, including Range requests. Excluded media and pre-screening
media return 404; missing/wrong-game credentials return 401. Cache-Control is private,no-store.
Media requests count as room activity, but do not refresh host command/poll presence.

Operational settings (private .env and process environment):

- `PROMPT_ROYALE_TOKENIZER`: pinned local tokenizer.json; default game-local .local path.
- `PROMPT_ROYALE_TOPIC_MODE=fixture|live`: independent of video GENERATION_MODE; default fixture.
- `OPENAI_API_KEY`: backend only. Topic model gpt-5.6-luna, reasoning effort none, total timeout 10s,
  max_output_tokens 64, accepted topic 160 code points; `PROMPT_ROYALE_TOPIC_CALLS` at most 16.
- Live requires `GENERATION_MODE=live`, `PROMPT_ROYALE_LIVE_ENABLED=true`, a current
  `PROMPT_ROYALE_LIVE_SLOT`, Reactor key and rehearsed capacity 3 or 4. Default capacity is 0.
- `PROMPT_ROYALE_LIVE_SESSION_STARTS` at most 16 per process. Start reserves admission only
  if remaining allowance covers 2 × player count. Two entry slots, starts at least 6s apart,
  at most two creation attempts/entry. No counter reset on replay or room close.
- Optional `PROMPT_ROYALE_FFMPEG` / `PROMPT_ROYALE_FFPROBE` executable paths.

An unresolved-provider.json file outside disposable clips blocks shared admission on restart.
The operator checks its session IDs in Reactor before removing the marker. Missing IDs require
an account-wide session check. No automatic crash replay or session replacement is attempted.
