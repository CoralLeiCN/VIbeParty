# Word by Word local checks

Run from the repository root with the locked environment and FFmpeg installed:

```sh
.venv/bin/pytest backend/tests/word_by_word backend/tests/shared -q
.venv/bin/ruff check backend/games/word_by_word backend/tests/word_by_word scripts/games/word-by-word
npm --prefix frontend run build
npm --prefix frontend run lint
```

Use the normal app in Fixture rehearsal mode for `WW-CAT-01`. `make_fixtures.py` creates its single scripted 24-second video. The game automatically plays the stream, introduces all four categories, and saves one replay. Fixture media is labelled and is not model output.

`rehearsal_server.py --scenario partial` starts an explicitly labelled internal fake at localhost:8011. It accepts arbitrary input, interrupts after two categories, and simulates unresolved closure that succeeds on Retry cleanup. `--scenario full` completes all four categories. Add `--code-0042` for a controlled leading-zero code. It never constructs a Reactor provider and uses its own disposable media directory. Because cookies are not isolated by port, use separate hostnames or browser profiles for independent players.

## Live play

Set these in private `.env` and restart:

```dotenv
WORD_BY_WORD_LIVE_ENABLED=true
REACTOR_API_KEY=...
OPENAI_API_KEY=...
WORD_BY_WORD_IMAGE_MODEL=gpt-image-2.5-flare
WORD_BY_WORD_CATEGORY_SECONDS=6
```

OPENAI_API_KEY generates the starting image from Place only. For development with a known setting, configure WORD_BY_WORD_SEED_IMAGE to an existing matching image instead. The host selects Live LingBot World 2. Four private answers trigger one session and automatic prompt updates; no manual video advancement or visual-quality approval is required.

The app enforces three live attempts per process, one task/session at a time, a 180-second deadline, private media, cancellation, and independent session-closure confirmation. No paid retries happen automatically. Private protocol evidence records safe timing and closure fields without credentials or submitted text.

## Optional coordinated protocol spike

The standalone spike consumes a live session. Run it only as part of an allocated live trial:

```sh
.venv/bin/python scripts/games/word-by-word/spike.py \
  --env-file .env --output .local/word-live/TRIAL-ID \
  --slot ALLOCATED-TRIAL-ID --previous-session-closed
```

The output directory must be new. It runs `WW-CAT-01` by default: one seed image, one LingBot session, four cumulative prompts, one MP4, and verified cleanup. An optional `--contributions-json` supplies four different accepted strings. `--account-precheck-waived` is retained for an explicitly authorized coordinated trial. Setup and ordinary tests make no paid requests. The spike records protocol behavior; visual model evaluation is not required.
