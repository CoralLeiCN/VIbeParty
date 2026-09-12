# Game testing and video evidence plan

[Documentation index](../README.md) · [Environment setup](../environment-setup.md) · [Existing test evidence](handoffs/portal.md)

Status: agreed approach documented on 12 September 2026. The existing tests and screenshots are available; the new walkthrough capture, video export, and combined report workflow still need implementation. This document records intended checks and deliverables. It adds no new passing test results.

## Outcome

Test Word by Word, Reverse Prompt, and Prompt Royale through complete rounds, then produce a report and a watchable walkthrough for each game. Use the **Codex app's built-in browser** for the walkthroughs and visual inspection. Use the existing automated tests to check game rules, API permissions, timing, and state changes.

The first video deliverable is an MP4 assembled from actual browser screenshots, with captions explaining the steps. Continuous gameplay recording remains a follow-up capability to verify. A screenshot sequence can show the flow, while playback checks must establish that the game videos actually decode, advance, and replay.

Start with the existing labelled fixture/rehearsal modes. A fixture pass establishes that the app flow works with its sample clips and scores. Live AI generation and physical-phone acceptance have their own results and retain the requirements in each game's specification.

## Tools and current gaps

| Component | Responsibility | Current position |
| --- | --- | --- |
| Codex built-in browser and computer use | Navigate the app, enter inputs, click controls, inspect screens, and capture screenshots | Interaction and screenshot controls are available. Independent player sessions and a supported way to save captures for export need verification. |
| Playwright + TypeScript | Repeatable browser assertions against the local app | The [combined scenario](../../frontend/tests/combined.spec.ts) uses isolated host/player contexts. Individual game scenarios and report attachments need adding. |
| pytest | Rules, scoring, ownership, cleanup, deadlines, and provider-failure checks | Existing tests live under `backend/tests/`. Extend them only for meaningful uncovered behavior. |
| FFmpeg + ffprobe | Assemble screenshots into MP4s and inspect exported files | Available on the inspected laptop. A repeatable export script needs adding. |
| Playwright HTML report and a run summary | Make outcomes and evidence easy to review | Current browser configuration uses console output and failure traces. HTML reporting and a summary linking both automated and Codex evidence need adding. |

The current Codex browser controls expose screenshots, navigation, and inspection; continuous recording is not exposed by those controls. Its Playwright-style page controls also do not establish that the repository's Playwright Test suite can run inside it. Keep the browser used for each piece of evidence explicit in the report.

Playwright can [record test pages](https://playwright.dev/docs/videos) and produce an [HTML report](https://playwright.dev/docs/test-reporters) in its own test runtime. If recording is added there, configure every manually created host/player context, close contexts even after failures, and attach the saved files. Those recordings would be additional automated-test evidence. The Codex walkthrough continues to use the built-in browser.

## Run preparation and browser sessions

Use a dedicated local test server with a fresh room, separate disposable media, and a recorded commit and working-tree status. Preserve persistent quota/model data. Run scenarios sequentially because the application supports one active party at a time. Close only the test run's own party and stop only the server process started for that run.

For fixture runs, explicitly select fixture/rehearsal in the app and set `GENERATION_MODE=fixture`, all three game live-enable flags to `false`, and `PROMPT_ROYALE_TOPIC_MODE=fixture`. Check the visible fixture label before starting. Follow [environment setup](../environment-setup.md) for the exact public/browser origin, ports, credentials, and dependencies. Keep credentials out of exported evidence.

Use synthetic names such as Alex, Bailey, Casey, and Drew. Start with a host viewport of 1360×1000 and phone views of 390×844. Record the actual dimensions and verify layout at 320, 768, and 1360 pixels where the portal's existing responsive checks apply. Set and restore the Codex viewport through its supported controls; verify whether that setting is shared across tabs before attempting different sizes together.

| Game | Primary full round | Additional roster check | Independent sessions required |
| --- | --- | --- | --- |
| Word by Word | Separate display host plus 3 players | Separate host plus 4 players | 4, then 5 |
| Reverse Prompt | Host/author A plus guests B and C | Reject an extra player | 3 |
| Prompt Royale | Playing host plus 2 guests | Playing host plus 3 guests; reject a fifth player | 3, then 4 |

Before a Codex multiplayer walkthrough, establish that supported browser sessions keep identities separate. Create the host and named guests, refresh each view, and verify that names, roles, and private inputs remain attached to the correct participant after other participants join or act. Multiple tabs alone do not prove session isolation.

If the built-in browser cannot provide independent identities, record that limitation and leave its full multiplayer walkthrough incomplete. Continue the existing isolated Playwright checks and the Codex views that can be verified. Resolve the session setup before claiming that Codex completed every player's flow; keep authentication and origin checks intact.

Keep the active player view available while interacting and account for the game's existing deadlines. In particular, Prompt Royale has a 30-second host-presence rule and a 10-second vote. Verify background-tab behavior and arrange timely actions before recording a full round. Editing delays belong in the exported walkthrough, not in the live test's timers.

## Scenarios and pass criteria

Each checkpoint records the action, expected outcome, observed outcome, participant, and evidence reference. Use `PASS`, `FAIL`, `BLOCKED`, or `NOT RUN`. A failure includes the first failing step and reproduction details. An unavailable session or capture capability is `BLOCKED`; it must not turn into a pass because another layer succeeded.

### Shared portal and recovery

| Check | Required outcome |
| --- | --- |
| Discover and host | All three game cards lead to the correct host flow and explain the correct player roles. |
| Join paths | Generic room-code entry, copied join link, and direct game join work. Leading zeros survive entry and refresh; invalid and closed codes show actionable messages. |
| Refresh and continuation | Host and guest retain their identities and accepted state. Back to games → Continue party returns to the active game and phase. |
| Rematch and close | Rematch preserves each game's roster/roles and code as specified. Closing or switching retires the old code and prevents old media access. |
| Switch all games | Complete Word by Word → Reverse Prompt → Prompt Royale in one server run, with fresh joins between parties and no stale player/clip state crossing games. |
| Visual usability | Text wraps, controls remain reachable, keyboard focus is visible, and the checked viewports have no horizontal overflow. |

Keep the existing combined test for game switching. Add independently runnable game scenarios so one game's failure does not hide the other games' results.

### Word by Word

Source: [game rules and acceptance](../games/word-by-word/game-spec.md).

Use the [standard category scenarios](../games/word-by-word/test-scenarios.md) for category rehearsals, fixture preparation, and live model evaluations. Follow their exact answers and mapping to the current four slots, and record the scenario ID and fixture version. Existing fixed-example recordings must identify their actual inputs and assets when they predate those scenarios.

1. Host a fixture round and join three players. Verify that the host occupies no player slot and the first player receives two of the four contributions.
2. Submit all four fixed examples through the visible phone controls. The current combined test submits these through API calls; the walkthrough must exercise the forms. Verify acceptance and locking, with only aggregate progress visible to the host before reveal.
3. Reach the ready state. Confirm that future contributions and clips stay hidden until the host advances the reveal.
4. Play each addition in order, watch the clip, and verify exact contribution text, contributor names, and the disclosed prefix on phones. Finish with four ordered cards.
5. Replay saved clips, refresh the host and a phone, and use portal continuation. Another round retains the roster/code; Reset party clears the roster and changes the code.
6. Repeat the assignment check with four players. Exercise an early end and a controlled partial/failed round; results contain only the permitted disclosed history.

Capture: lobby, private assignment, accepted contribution, ready state, every reveal addition, completed story, and rematch lobby. Include at least one player view. Check clip advancement and replay separately from the still images.

Free-text validation, Unicode preservation, missing-input deadlines, duplicate commands, and slot/media authorization use the existing automated checks or explicit test fakes. Fixed-example footage does not establish arbitrary-input generation or visual continuity from a live model.

### Reverse Prompt

Source: [game rules and acceptance](../games/reverse-prompt/game-spec.md).

1. Create a rehearsal party as A and join B and C. Verify the three roles and start the round.
2. Submit A's scene using the UI. Verify that B receives the first private clue while C sees the appropriate waiting screen.
3. Submit B's interpretation, then C's interpretation after C receives the next clue. Confirm that private text and earlier clues stay hidden from participants who should not see them.
4. Show the final clip to all three. Submit separate final guesses as B and C; A remains unscored. One accepted guess does not reveal the other player's answer prematurely.
5. Verify the ordered three prompt/video cards, both guesses, and the fixture's expected sample scores of 88 and 46. Play and replay all three clips. The automated scorer checks establish real scoring behavior separately from these sample values.
6. Refresh, continue from the portal, and reset to the lobby. The roster, roles, and room code remain; the previous round's content is cleared. Close the party and verify its code/media are retired.

Capture: roster, A's accepted scene, B and C's clue/interpretation screens, final guess acceptance, full reveal, and reset lobby. Private-role screenshots are test evidence; display their role labels clearly in the walkthrough.

### Prompt Royale

Source: [game rules and acceptance](../games/prompt-royale/game-spec.md).

1. Complete a three-player round, then a four-player round. Use a bundled topic in one and a generated fixture topic in the other. Confirm that Generate another clears confirmation and Start requires the current topic to be confirmed.
2. Enter every private scene through its browser form. Refresh one unsent draft, then check that accepted submissions stay locked and private.
3. Reveal the eligible clips together in the arena. Verify that labels and positions match across participants and remain stable through voting and results. The unused tile in a three-player round is not a candidate.
4. Use Play arena, Pause all, and Replay all. Observe every eligible clip through at least one full loop. Clips should play together within each screen; cross-device frame-perfect synchronization is not required.
5. Open voting after viewing. Verify that self/excluded entries cannot be selected, accepted ballots lock, and totals/authors/prompts remain hidden until results. Complete the vote within the existing deadline.
6. Check totals and the winner or tie against the submitted ballots. Individual ballots remain private. Play again retains the roster/code and clears the topic, prompts, ballots, and old media.

Capture: lobby/topic confirmation, private submission, three- and four-entry arenas, playback controls, voting, results, and rematch. Arrange screenshots so capture does not cause an accidental vote timeout or host absence.

### Failure and playback checks

Use targeted, controlled tests for invalid input, duplicate actions, unauthorized commands/media, expired codes, refresh, backend restart, missing submissions, provider failure, playback failure, and stale callbacks after reset. Reuse the existing suites and game rehearsal harnesses where they cover the requirement. Label any deliberate fake or injected failure in the result.

Verify video elements have decoded dimensions, advancing playback time, and no media error; check pause/replay behavior and watch for freezes or blank frames. A static screenshot or successful MP4 export alone cannot establish playback quality. Run host and real phone Safari/Chrome checks before declaring the event demo ready.

## Captures, video export, and reports

For each screenshot, save an original image and a manifest entry with game, scenario, step, participant/role, actual viewport, capture timestamp, caption, and intended display duration. Verify the saved file can be decoded before proceeding with export. Check the resulting UI state after actions before capturing it; use elapsed timestamps to measure the test itself.

Assemble a separate `walkthrough.mp4` for each game with FFmpeg. Use a 1920×1080 canvas, H.264/yuv420p output, and aspect-preserving scaling with padding. Keep phone text readable; prefer a focused phone view when several panels would make text too small. Start with a title identifying the game, fixture/rehearsal mode, run ID, and “Screenshot walkthrough.” Add brief step and participant captions, outside the captured app content.

Hold each screenshot long enough to read, initially around 2–4 seconds and longer for detailed results. These are presentation durations. Preserve real capture timestamps in the manifest, and do not infer game latency or simultaneous device activity from the edited sequence. Keep original captures alongside the MP4. If continuous recording becomes supported, retain the raw recordings and identify any cuts in the edited walkthrough.

Proposed artifact layout, under the already ignored `.local/` directory:

```text
.local/test-runs/<run-id>/
  summary.md
  results.json
  automated/                 # command logs and Playwright report/attachments
  word-by-word/
    captures/
    manifest.json
    walkthrough.mp4
  reverse-prompt/
    captures/
    manifest.json
    walkthrough.mp4
  prompt-royale/
    captures/
    manifest.json
    walkthrough.mp4
```

The summary identifies the commit and local changes, test mode, origin, browser/device and versions, viewports, start/end times, command exit codes, and every scenario's status. Link to the exact captures, video, logs, and any available trace for a failed step. Keep automated-test results, Codex observations, capture/export results, and live/device checks identifiable. Preserve failed runs; a successful rerun gets a new run ID.

Use ffprobe to check each MP4's codec, dimensions, duration, and video stream. Open and watch the export to verify image order, readable captions, aspect ratio, and absence of blank/missing frames. A game can pass while export fails; report both outcomes. A complete fixture evidence run requires all required fixture checks, all three walkthroughs, and a readable summary.

## Existing commands and implementation order

The following commands exist today. Install dependencies through [environment setup](../environment-setup.md), including the browser binaries needed by the existing Playwright tests.

```sh
# Repository root; run checks before starting the capture session.
bash scripts/check.sh

# Start the combined app using the dedicated fixture configuration described above.
bash scripts/demo.sh
```

In another terminal, with that server idle between suites:

```sh
npm --prefix frontend run test:portal
npm --prefix frontend run test:integration
```

Set `PORTAL_URL` to the configured server origin and `DEMO_HOST_CODE` to the test server's host code when they differ from the test defaults. The existing controlled-code server in [scripts/rehearsal_room_codes.py](../../scripts/rehearsal_room_codes.py) supports a separate `0042` acceptance run; follow the [handoff instructions](handoffs/portal.md#four-digit-code-acceptance). Record the selected server/harness in the run summary.

Implement in this order:

1. Verify built-in browser session isolation, viewport behavior, screenshot saving, and responsiveness during timed multiplayer phases. Record the supported setup and remaining limitations.
2. Add independent automated scenarios for each game, retaining the combined switch test. Move Word by Word contributions through its UI for full browser coverage.
3. Create the Codex walkthrough procedure and capture manifest, exercising the checkpoints above. The walkthrough is a Codex task using its browser tools.
4. Add the FFmpeg export script, file validation, HTML report attachments, and run summary. Produce and inspect one fixture walkthrough for each game.
5. Package test-server startup, automated checks, and export into a repeatable command with cleanup and clear failure exit codes. A proposed name is `test:video`; it does not exist yet. Document how the command consumes Codex captures, since an npm command alone does not establish access to the built-in browser tools.
6. Verify a supported continuous capture method if smooth recordings are needed, then complete live-provider and physical-phone checks under the existing game acceptance requirements and [provider trial procedure](live-provider-slots.md).

Historical results remain in the [portal handoff](handoffs/portal.md), [Word by Word rehearsal](../research/word-by-word/fixture-rehearsal-2026-09-12.md), [Reverse Prompt verification](../research/reverse-prompt/laptop-verification.md), and [Prompt Royale rehearsal](../research/prompt-royale/fixture-rehearsal.md). Attach new results to the revision actually tested.
