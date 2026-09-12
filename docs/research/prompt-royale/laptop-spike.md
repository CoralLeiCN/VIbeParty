# Prompt Royale laptop spike — 12 September 2026

Status: offline compatibility passed; live capture, topic access and phone playback pending.

## Measured locally

Host: macOS 26.6.2, arm64. Python 3.13.3, uv 0.11.29, Node 24.3.0.
An isolated `/private/tmp/prompt-royale-spike-venv` successfully installs and imports
`reactor-sdk==1.5.1`, `tokenizers==0.23.2`, and `httpx==0.28.1`.
The native Reactor constructor initializes and closes without connecting. No sessions
were created by this check. FFmpeg/ffprobe were absent from PATH at initial inspection; integration subsequently installed 7.1.1.

Helios documents `umt5-xxl` and a 512-token encoder limit; the application accepts at
most 500 full-input tokens. Google tokenizer revision:
`66cb9e7e85526fe440a945569e42c72fb6cbc0ad`. Downloaded tokenizer.json: 16,853,013 bytes;
SHA256 `af904105ce1071b1202bba0059a841f4a7b85b48b6ec179c4948e3483476e0dd` verified.
Encoding includes EOS and never truncates. With the fixed game template and invention topic:

| Player input | Code points | Full-input tokens |
| --- | ---: | ---: |
| A penguin dances on the moon. | 29 | 32 |
| 月の上でペンギンが踊る。 | 12 | 32 |
| 500 repetitions of é | 500 | 523 |
| 500 juggling emoji | 500 | 524 |

The last two must be rejected despite meeting the character bound.

## SDK findings and implementation decisions

The installed 1.5.1 SDK differs from the earlier research: `_recording.py` downloads
fragmented MP4 (initialization segment plus fragments), rather than MPEG-TS. Inspect
actual codecs with ffprobe and prepare the same deterministic five seconds either way.
Its urllib download runs in an asyncio worker thread and can continue writing after
cancellation. The game therefore needs cancellable HTTPX streaming with byte/time bounds.
The `on_raw_frame` callback exposes `timestamp_us` and needs no NumPy. Sender timestamp
deltas measure media received; zero/missing timestamps must fail the capture gate.

Use one scoped token per attempt (`reactor/helios`, max_sessions 1, session cap 60s),
apply exact prompt, round seed and 2x scale before start, receive >=6s media, request the
full recording while connected, download, and confirm termination. A timeout or unknown
creation/termination cannot authorize a replacement session. Official SDK source at 9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d calls create_session once in connect. The token also bounds creation to one. Live behavior remains unverified.

## Topic selection

Selected candidate: OpenAI `gpt-4.1-mini-2025-04-14`, through backend HTTPX Responses API.
Total deadline 10s, max_output_tokens 64, maximum accepted topic 160 code points, no tools,
store false, no automatic request retries, separate maximum 16 calls per process.
Only a generic topic instruction is sent; no names, player prompts, or ballots.
The host confirms the exact suggestion ID. Fixture suggestions are explicitly labelled.
OPENAI_API_KEY was missing on initial inspection. Access and latency are not validated.

## Sources

- [Helios tokenizer guidance](https://docs.reactor.inc/model-api-reference/helios/prompt-guide)
- [Reactor Python API](https://docs.reactor.inc/sdk-reference/python/reactor)
- [Scoped token constraints](https://docs.reactor.inc/authentication)
- [Helios settings](https://docs.reactor.inc/model-api-reference/helios/schema)
- [Published Reactor package](https://pypi.org/project/reactor-sdk/1.5.1/)
- [Google tokenizer](https://huggingface.co/google/umt5-xxl/blob/66cb9e7e85526fe440a945569e42c72fb6cbc0ad/tokenizer.json)
- [OpenAI model](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
- [Responses text generation](https://developers.openai.com/api/docs/guides/text)


## Independent closure verification

The official [SDK source](https://github.com/reactor-team/reactor-client-sdks/tree/9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d)
shows disconnect logging and swallowing termination failures. Prompt Royale independently
uses authenticated GET /sessions/{id}, with Reactor-API-Version and Reactor-API-Accept-Version
set to 1. CLOSED and INACTIVE are terminal; a 404 also establishes absence. Bounded DELETE
followed by another GET can finish owned cleanup. Unknown/missing state remains blocked.
The adapter uses this verified source contract; no live terminal response has yet been observed.
