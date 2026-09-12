# Local environment setup

VibeParty keeps backend configuration and the Reactor API key in a private root `.env`. Git ignores that file. The tracked `example.env` contains the settings and placeholder for the key.

Install Git, Bash, Node.js 22+ (24 works), uv and Python 3.13. `uv sync` can provision Python. Install FFmpeg and ffprobe (macOS: `brew install ffmpeg`) before video spikes. From the repository root:

```sh
bash scripts/setup.sh
bash scripts/dev.sh       # API 8000 + Vite 5173; open http://localhost:5173
bash scripts/check.sh     # Python checks + frontend lint/build
bash scripts/demo.sh      # one worker, no reload; frontend + API on :8000
```

The demo builds the frontend before starting. Stop development before using the same API port. Override `BACKEND_PORT`, `FRONTEND_PORT`, `BROWSER_ORIGIN`, `PUBLIC_ORIGIN` in the process environment or root `.env`; use `API_PROXY_TARGET` only for an explicit proxy override. For B/C/D development use ports 8011/5174, 8012/5175, 8013/5176 respectively. The dev command defaults its browser origin to the frontend port. Export BROWSER_ORIGIN for a different development hostname. For the demo set both origins to `http://<laptop-LAN-IP>:8000`. No secret uses a VITE_ variable.

Relative private media paths resolve against this worktree: `<MEDIA_ROOT>/<game-id>/clips`. Persistent Reverse Prompt quota and model paths are outside media, allocated deliberately and preserved across cleanup/restarts. A new worktree does not replenish the shared account allowance. Dependency lockfiles are shared-owner files; request updates through the handoff.

## Local target for the portal and all games

Build and run the portal, Word by Word, Prompt Royale, and Reverse Prompt on the host laptop. The combined demo uses one FastAPI process with one Uvicorn worker serving the built frontend and API over HTTP. Remote deployment, domains, Caddy, and TLS setup are deferred. The commands above install the locked dependencies, build the frontend, and start the local server.

Use `http://localhost:8000` for laptop-only checks. For group play, bind the server to `0.0.0.0:8000`, set `PUBLIC_ORIGIN=http://<laptop-LAN-IP>:8000`, and open that LAN URL on the host and phones connected to the same Wi-Fi or hotspot. A phone's `localhost` points to that phone. Verify the laptop firewall and network permit device connections, and keep the laptop awake. Use the configured browser origin for Origin checks and omit Secure on the local HTTP session cookies; keep HttpOnly and each game's SameSite setting.

Verify the Reactor SDK, FFmpeg, and Reverse Prompt's CPU scoring dependencies on the actual laptop OS/architecture during the initial spikes. The pinned native versions below have been verified on this Mac; repeat this check on a different laptop. If a dependency requires Linux, evaluate a local container or VM on the same laptop only when the spike establishes that need; verify port forwarding and phone/provider connectivity in that local runtime. This does not require a hosted server.

Live video needs outbound internet access to Reactor; Prompt Royale's live topic suggestions need its selected LLM. Word by Word and Reverse Prompt use FastH3; Prompt Royale uses Helios. Reverse Prompt's integrated replacement selects fixed `reactor/fast-h3` through the existing locked SDK. No new model-selector setting or dependency is needed. Preload Reverse Prompt's pinned model during setup so scoring is local. Keep its persistent quota/model files outside disposable clip directories. The root `example.env` covers common settings; each game’s handoff documents its provider-specific settings and setup commands. Each parallel worktree uses its own ports and private configuration as described in the [parallel development plan](parallel-development-plan.md#6-worktree-and-runtime-isolation).

## Prepare the original checkout

Create `.env` in the original repository folder you added to Codex, before creating new worktrees. On this machine that folder is `/Users/coral/repos/VIbeParty`.

From that folder, run:

```sh
umask 077
cp -n example.env .env
chmod 600 .env
```

`cp -n` preserves an existing configuration. Open `.env` in your editor and set `REACTOR_API_KEY` to your Reactor key. Keep credentials in this file and backend environment variables. The [local configuration guide](README.md#local-configuration) covers the other settings, including fixture mode and the LAN origin for phone play.

Check that Git ignores the file without displaying its contents:

```sh
git check-ignore .env
```

## Configure Codex worktree setup

The repository includes these files:

- [`.worktreeinclude`](../.worktreeinclude) tells Codex to copy the ignored root `.env` when it creates a local managed worktree.
- [`.codex/environments/environment.toml`](../.codex/environments/environment.toml) defines the **VibeParty** local environment and its setup command.
- [`scripts/setup-worktree.sh`](../scripts/setup-worktree.sh) prepares `.env` and can also be run manually in an existing worktree.

Keep these files on the branches you use to start new worktrees. In the Codex app settings, open **Local environments** for this project and select the **VibeParty** environment. Its setup script is:

```sh
cd "${CODEX_WORKTREE_PATH:-.}"
bash scripts/setup-worktree.sh
```

When starting a task, choose **Worktree** and the **VibeParty** local environment so Codex runs the setup automatically. If you configure the environment through the settings editor, use the command above and save it for this project.

Codex's [local environment documentation](https://learn.chatgpt.com/docs/environments/local-environment) describes automatic setup scripts. Its [worktree documentation](https://learn.chatgpt.com/docs/environments/git-worktrees#copy-ignored-local-files-into-managed-worktrees) describes `.worktreeinclude`: copying applies to local managed worktrees, skips source symlinks, and preserves existing destination files. CLI-created and remote worktrees need the setup script run on their host, with a source `.env` available there.

## What the script does

1. Verifies that Git ignores `.env` and preserves an existing regular `.env` file.
2. If `.env` is missing, copies it from the original checkout found through Git. Paths are discovered automatically, so the script works when another developer clones the project elsewhere.
3. If the original checkout has no `.env`, creates one from `example.env` and reports that it is using fixture defaults. This does not provide an API key; fill in the original checkout's `.env` for future worktrees.
4. Restricts `.env` permissions to its owner. It never sources the file or prints its contents.

Each worktree gets an independent copy. Changing a worktree's settings does not change the original checkout. Later changes to the original `.env` apply to newly created worktrees; update existing copies explicitly when needed. Rerunning setup preserves them.

For an existing worktree, run this from its root:

```sh
bash scripts/setup-worktree.sh
```

If you keep the source somewhere else, set its path for the setup command:

```sh
VIBEPARTY_ENV_SOURCE="/absolute/path/to/private.env" bash scripts/setup-worktree.sh
```

An explicitly configured source must exist. An existing destination `.env` is still preserved. Keep the real key out of the setup script, environment TOML, and `example.env`.

## Verified native dependencies

FFmpeg/ffprobe 7.1.1 are installed on the demo laptop. The shared `live` extra pins reactor-sdk 1.5.1 and tokenizers 0.23.2; `scoring` pins the native versions verified by Reverse Prompt (sentence-transformers 6.0.1, torch 2.14.0, transformers 5.17.0, huggingface-hub 1.31.0, numpy 2.5.3). Setup/start/check commands install both extras. To install only the lightweight shell use `uv sync --frozen`. Model downloads and persistent quota initialization use the game-owned setup command and are never done on startup. Paid trials require a coordinator allocation and confirmed closure before slot transfer. The [trial record](development/live-provider-slots.md) records the current allowance and any explicit user waiver of account prechecks.

`bash scripts/setup.sh` also runs explicit game-asset setup: it verifies/downloads Prompt Royale’s pinned tokenizer when integrated, downloads a missing pinned MiniLM model, and runs the scorer with sockets blocked. An existing checksum manifest is verified by the offline check; existing model files are not rewritten. These public asset downloads happen during setup only. Quota initialization and paid provider trials are separate operator actions.
