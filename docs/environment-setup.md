# Local environment setup

VibeParty keeps backend configuration and the Reactor API key in a private root `.env`. Git ignores that file. The tracked `example.env` contains the settings and placeholder for the key.

This checkout contains planning documents and configuration only. Setup requires Git and Bash (the versions supplied with macOS work). There is no dependency manifest, backend, or `.env` loader yet, so there are no package installation or server startup commands to run.

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
