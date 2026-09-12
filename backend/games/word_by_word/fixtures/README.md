# Scripted fixture assets

These four original illustrated clips were generated locally by `scripts/games/word-by-word/make_fixtures.py`. They are prerecorded fixtures, not Reactor output. Each is six seconds, 640×360, H.264/yuv420p MP4 with fast-start metadata and no audio. The colored strip identifies the scripted art; the UI supplies the full fixture label and exact text.

| File | Required accepted contribution |
| --- | --- |
| 0.mp4 | a moonlit forest |
| 1.mp4 | a fox in a tiny hat |
| 2.mp4 | They start breakdancing. |
| 3.mp4 | Confetti rains from the sky. |

They are backend package data and are never statically served. The fixture provider copies them into the private current-round directory and validates them before advancing. HTTP access still requires a host session and prior disclosure. Regenerate with:

```sh
.venv/bin/python scripts/games/word-by-word/make_fixtures.py backend/games/word_by_word/fixtures
```
