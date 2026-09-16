# VibeParty

Three video party games, one laptop, and your friends’ phones. React 19/TypeScript/Vite frontend and Python 3.13/FastAPI backend. The portal preserves each game’s roles: Word by Word has a separate display host and 1–4 players; Prompt Royale has a selectable 1–4 players including its host; Reverse Prompt has exactly 3 including its host.

## Run locally

Install Node 22+, uv, FFmpeg and ffprobe (`brew install ffmpeg` on macOS), then:

```sh
make setup
make start
```

Open `http://localhost:8000`. For phones set `PUBLIC_ORIGIN` and `BROWSER_ORIGIN` in private `.env` to `http://<laptop-LAN-IP>:8000`, then restart and use that address on every device on the same Wi-Fi/hotspot. The demo serves frontend and API from one worker on 0.0.0.0:8000. Server restarts lose rooms. Private clips stay outside the static frontend.

Running `make` also starts the app. For development run `make dev`: backend 8000, Vite 5173 with API proxy. Stop either mode with Ctrl+C. Ports/origins/private paths are configurable; see [environment setup](docs/environment-setup.md).

Local mode is on by default: choose a game, create a room, and copy its join link for friends. Host passwords are optional in this mode; friends open the link and enter their names. Set `LOCAL_MODE=false` in `.env` and restart to require `HOST_PASSCODE` (or Reverse Prompt’s `ORGANIZER_CODE` override) when creating rooms.

Default play uses labelled fixtures/rehearsal. Live generation requires each game’s provider gates, bounded allowance and an exclusive trial slot. Setup installs public tokenizer/model assets but creates no paid provider session or quota. Remote deployment is deferred.

## Check and contribute

```sh
make check
npm --prefix frontend run test:portal  # combined demo must be running
```

[Game testing and video evidence plan](docs/development/testing-and-video-plan.md) describes the Codex browser walkthroughs, per-game checks, and planned video exports.

[Portal evidence and integration status](docs/development/handoffs/portal.md) · [Shared contracts](docs/development/contracts/shared.md) · [Worktree ownership and merge procedure](docs/parallel-development-plan.md) · [All specifications](docs/README.md).
