# VibeParty remaining work

Updated 12 September 2026. This checklist tracks work remaining after the verified portal and three-game fixture release (`4d973a8`, landed on local `main` as `9ed93a1`).

The portal, four-digit room codes, game rules, fixture rounds, continuation and switching are implemented. That release passed 139 backend tests, lint/format/build checks, six portal browser scenarios and connected LAN browser rehearsals. Subsequent integration work now passes 155 backend tests and both connected LAN browser scenarios. Word's three real trials generated output but saved no valid clip; all three sessions are independently confirmed closed. Real provider acceptance and physical-phone rehearsal remain open. Fixed rehearsal clips and simulated provider tests do not count as live generation evidence.

## 1. Trial status and preserved limits

Owner: presenter/operator and portal integration owner.

The user has stopped cross-task live-trial coordination and asked this task to stop listening to other tasks. Do not monitor, message or wait for those tasks, allocate further paid work, or resume trials unless the user restarts that work. Preserve every completed attempt and closure record. This checklist reflects the local integration checkpoint.

- [ ] Record billing information when available. The API key is configured; the user has explicitly waived the dashboard balance and account-wide prior-session precheck for the first bounded Word by Word trial. Those account facts remain unverified, and they do not block this allocated trial.
- [ ] Resolve any uncertain session created by a trial before allocating new work. Independent closure verification remains required.
- [ ] Grant one exclusive game-worktree trial slot at a time in the [trial record](docs/development/live-provider-slots.md), with an identifier, allowed attempts and duration limits.
- [ ] After every trial, record attempts, elapsed time, measured spend, saved evidence and independently confirmed provider shutdown before transferring the slot.
- [ ] Enable each game's live flags only after its required evidence and allocation exist. Keep credentials and session tokens in private configuration; record no secrets in this checklist or research notes.

No paid trial or Reverse Prompt campaign initialization had been performed at this checkpoint. Reactor bills while a session holds a GPU, including idle time; a dropped connection alone does not establish that billing stopped. See [Reactor billing](https://docs.reactor.inc/resources/billing).

Coordination update, 12 September: Word completed three separately allocated attempts. The first exposed compact completion metadata; the second exposed absent frame IDs/timestamps. Both adapter corrections are integrated. The third received 156 of 158 advertised frames and hit its 30-second step deadline without a valid saved clip. All three sessions are independently confirmed `CLOSED`, all slots are released, and no fourth attempt is allocated. Elapsed times were 14.066, 12.728 and 38.415 seconds; actual spend remains unmeasured. Reverse subsequently completed one independent capture, then its full-relay attempt failed on the first generation. Two Reverse attempts are consumed, seven remain, and the quota records both closed with no unresolved session. No further attempts are allocated; coordination is stopped.

## 2. Word by Word real generation

Owner: Word by Word game owner, with integration coordinating the slot.

- [x] Integrate the later Word diagnostics and real-trial metadata corrections, including `2fbd4a9` and `853fe02`. These follow the fixture release and are not part of `4d973a8`.
- [x] Run the first bounded trial and two separately allocated follow-ups on the laptop/network: one session per attempt, a 180-second provider cap, 120-second application deadline and 30-second step deadline. Each failed before saving a valid clip; all sessions closed.
- [ ] Resolve the measured capture shortfall: trial 003 received 156 of 158 advertised frames, with absent optional identifiers. Investigate callback boundaries/transport delivery or a reliable provider export. Preserve the accepted capture requirement until an explicit revision is agreed; then obtain a new allocation and prove a complete four-clip chain.
- [ ] Inspect the four saved clips for correct capture boundaries, six-second duration and additive continuity: previous scene elements should persist when a new contribution is added.
- [ ] Prove that the complete cumulative prompt supports the accepted 120-code-point Unicode contribution limit within FastH3's token bound. The owner checked the newer published 800-character cap: the maximum cumulative prompt is 732 code points. The separate 1,024-token compatibility gate remains open. Do not shorten accepted text silently.
- [ ] Complete the specified two forest/fox/dance/confetti trials and one group-selected variation, recording timing and actual spend.
- [ ] Confirm provider termination independently and play the saved sequence after termination without further generation.
- [ ] Verify real failure/stop behavior: preserve usable saved clips, discard late results and block rematch/switching while cleanup is unresolved.

Acceptance: the required trials produce playable, correctly ordered additive clips within the limits, with prompt compatibility and provider closure documented. See the [Word handoff](docs/development/handoffs/word-by-word.md) and [trial runbook](scripts/games/word-by-word/README.md).

## 3. Prompt Royale real video and topics

Owner: Prompt Royale game owner, with integration coordinating the slot.

- [ ] Run the allocated Helios capture spike and verify real recording availability, download, deterministic five-second MP4 preparation and independent session closure. The initial requested slot is one session with a 60-second provider cap.
- [ ] Complete live rounds with three players, then four players, including the playing host. Measure whether generation scheduling and recovery finish within the round's deadlines.
- [ ] Verify the real clips play together in the stable anonymous arena, including pause, replay, blocked-playback recovery and a failed-video retry.
- [ ] Verify bounded generation recovery, voting/exclusions and cleanup using actual provider output. Record attempts and cost; replay must not create new sessions.
- [ ] Configure `OPENAI_API_KEY` privately for automatic topic suggestions. It was absent in the integration worktree at the last check; bundled topics already work.
- [ ] Run the live topic spike: useful output, length limits, timeout handling, regeneration, explicit confirmation and stale-result rejection. Track its separate call allowance.
- [ ] Set the rehearsed live capacity only after the corresponding three/four-player device checks pass.

Acceptance: both topic modes and full live rounds work on the intended devices within the configured allowances. See the [Prompt handoff](docs/development/handoffs/prompt-royale.md) and [runbook](scripts/games/prompt-royale/README.md).

## 4. Reverse Prompt provider switch and real relay

Owner: Reverse Prompt game owner, with integration coordinating the persistent campaign.

The user selected MiniMax FastH3 through Reactor for Reverse Prompt. The replacement and compact-event correction are integrated from `cfc422c` and `9e71dbb`; shared technical/environment references are aligned. It passes local tests and one independent real capture; full relay and physical-device acceptance remain open.

- [x] Review and integrate the game-owned FastH3 replacement: enqueue a clip, wait for generation, explicitly play it, and capture a private MP4. Preserve a fresh independent session per relay step, current-prompt-only input, role privacy, attempt accounting and cleanup guards.
- [x] Align the technical specification and shared environment descriptions with FastH3. The locked SDK supports this route; no new dependency or model-selector setting is needed.
- [x] Initialize one nine-attempt campaign at `/Users/coral/.codex/worktrees/5a4f/VIbeParty/.local/vibeparty-persistent/reverse-prompt/quota.json`. Every worktree must use that exact `REVERSE_PROMPT_QUOTA_FILE`; never initialize another campaign or replenish this one. Slot `2026-09-12-reverse-001` consumed one attempt and is closed; a later first relay generation consumed one more attempt. Seven remain, with no unresolved session or further allocation.
- [x] Complete one independent real FastH3 capture: 124 declared source frames, 120 captured/encoded frames, five-second 24 fps silent H.264, 1344×768, 1,953,399 bytes; total 16.490 seconds. The provider session is independently confirmed closed. Saved playback/visual review is recorded by the game owner.
- [ ] Record real frame timing, visual quality, dimensions, file size, total latency, remaining attempts and independently confirmed provider closure.
- [ ] Complete a full live relay using three fresh sessions, each receiving only the current player's prompt. Check that B and C see only their permitted clue at each step.
- [ ] Score the real final guesses with the already verified local MiniLM model. Confirm that author A remains unscored and that inference failure produces an unscored reveal.
- [ ] Run the allocated forced-failure trial and verify an unscored result, owned encoder cancellation, persistent attempt consumption and cleanup blocking when closure is uncertain.
- [ ] Complete the remaining live/event-device portions of DEMO-02, DEMO-07 and DEMO-08, then update the evidence checklist.

The proposed first campaign sequence is one capture, a three-attempt full relay and one forced-failure attempt; only the first capture passed. The live relay failed on its first generation; its remaining two attempts were cancelled when coordination stopped. Full-relay and forced-failure verification remain unfinished. Replacement tests now verify full and compact completion metadata, queue lookup without another enqueue, matching playback, 120 supplied frames becoming an ordered five-second MP4, cancellation and persistent cleanup. Offline scoring also passes. Word's real frame shortfall reinforces the need to measure Reverse's actual playback/capture; supplied-frame tests do not pass that gate. See the [Reverse handoff](docs/development/handoffs/reverse-prompt.md), [laptop evidence](docs/research/reverse-prompt/laptop-verification.md) and [runbook](scripts/games/reverse-prompt/README.md).

## 5. Physical-phone and combined live rehearsal

Owner: presenter and all game owners; integration records the combined result.

- [ ] Connect the laptop and physical phones to the event Wi-Fi/hotspot. Confirm firewall/network access and keep the laptop awake.
- [ ] Configure the current laptop LAN origin and open it on every device. Use the combined frontend/API server on port 8000; development uses API 8000 and frontend 5173.
- [ ] Complete Word by Word with a separate laptop host and three/four player phones, Prompt Royale with three/four players including its host, and Reverse Prompt with exactly three players including author A.
- [ ] Verify Safari and Chrome playback on the actual phones, especially Prompt Royale's simultaneous arena and saved replay in every game.
- [ ] Check numeric code entry and leading zeros, copied links, direct entry, refresh, background/foreground, reconnect and authorized continuation.
- [ ] Complete the consecutive portal walkthrough with real generated clips: host, join, finish, Back to games, Continue party, close, wait for confirmed cleanup, switch and rejoin.
- [ ] Verify old codes, cookies and private media do not authorize access after the relevant reset/closure, and no late generation result crosses into the next party.
- [ ] Exercise stopping/closing during a real generation and verify that provider shutdown and attempt accounting remain correct.

Desktop Chromium contexts at phone dimensions have passed; they do not establish physical-device compatibility.

## 6. Final integration and release evidence

Owner: portal integration owner.

- [ ] Fix failures found by real-provider/device trials in the owning game worktree and integrate committed milestones with normal merges while those branches remain active.
- [ ] Re-run affected game/shared checks after changes, plus the final connected browser rehearsal when shared behavior changes.
- [ ] Update game handoffs and the [portal evidence](docs/development/handoffs/portal.md) with actual live results, devices tested, timing, attempts, spend, provider closure and commit SHAs.
- [ ] Enable only the live modes/capacities supported by that evidence, preserve persistent quota/closure records and restore the normal random-code demo command.
- [ ] Commit and land the resulting verified live milestone on `main`.

Remote hosting, public deployment, TLS/domain setup and optional visual extras remain deferred. Keep the provider specifications and trial plans aligned with the accepted Reverse Prompt FastH3 change.

## 7. Planned walkthrough videos and test reports

The newer [testing and video evidence plan](docs/development/testing-and-video-plan.md) is preserved from `main`. Its new deliverables are planned, not completed by the existing screenshots and test results.

- [ ] Verify independent player sessions and screenshot export in the Codex built-in browser, then capture the specified fixture walkthrough for each game. Use the new Word category scenario IDs and record actual inputs when reviewing older fixed examples.
- [ ] Add independently runnable game browser scenarios and put Word contributions through visible forms, retaining the combined switching check.
- [ ] Implement capture manifests, FFmpeg screenshot-walkthrough exports, HTML test reports and a combined run summary; inspect all three exported videos. Continuous recording remains a separate capability to verify.
