# VibeParty remaining work

Updated 12 September 2026. This checklist tracks work remaining after the verified portal and three-game fixture release (`4d973a8`, landed on local `main` as `9ed93a1`).

The portal, four-digit room codes, game rules, fixture rounds, continuation and switching are implemented. The release passed 139 backend tests, lint/format/build checks, six portal browser scenarios and connected LAN browser rehearsals. Real provider acceptance and physical-phone rehearsal remain open. Fixed rehearsal clips and simulated provider tests do not count as live generation evidence.

## 1. Account readiness and trial coordination

Owner: presenter/operator and portal integration owner.

- [ ] Confirm the Reactor account's available credits and record the agreed trial allowance. The API key is configured, but the available dashboard session required sign-in and its balance was not verified.
- [ ] Confirm that previous provider sessions have ended. Resolve any uncertain session before allocating new work.
- [ ] Grant one exclusive game-worktree trial slot at a time in the [trial record](docs/development/live-provider-slots.md), with an identifier, allowed attempts and duration limits.
- [ ] After every trial, record attempts, elapsed time, measured spend, saved evidence and independently confirmed provider shutdown before transferring the slot.
- [ ] Enable each game's live flags only after its required evidence and allocation exist. Keep credentials and session tokens in private configuration; record no secrets in this checklist or research notes.

No paid trial or Reverse Prompt campaign initialization had been performed at this checkpoint. Reactor bills while a session holds a GPU, including idle time; a dropped connection alone does not establish that billing stopped. See [Reactor billing](https://docs.reactor.inc/resources/billing).

## 2. Word by Word real generation

Owner: Word by Word game owner, with integration coordinating the slot.

- [ ] Review and integrate the later Word trial-diagnostics milestone: implementation `217eddf299ba0027dbbf22dd1d539c8571a069af`, handoff head `753d2eb5a06dbfe17d8f219992f8a3d4ca0d036b`. These follow the fixture release and are not part of `4d973a8`.
- [ ] Run the first allocated FastH3 trial on the actual laptop/network: one session, four sequential additive clips, a 180-second provider cap, a 120-second application deadline and a 30-second deadline per step.
- [ ] Inspect the four saved clips for correct capture boundaries, six-second duration and additive continuity: previous scene elements should persist when a new contribution is added.
- [ ] Prove that the complete cumulative prompt supports the accepted 120-code-point Unicode contribution limit within FastH3's 1,024-token bound. Do not shorten accepted text silently. Resolve any incompatibility before enabling live play.
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

The user has now selected MiniMax FastH3 through Reactor for Reverse Prompt. The currently integrated version uses Helios; the game owner is implementing the replacement. The new adapter has not been integrated or verified live.

- [ ] Finish and review the game-owned FastH3 replacement: enqueue a clip, wait for generation, explicitly play it, and capture a private MP4. Preserve a fresh independent session per relay step, current-prompt-only input, role privacy, attempt accounting and cleanup guards.
- [ ] Update Reverse Prompt's technical specification and shared environment descriptions for FastH3, then integrate the committed implementation/tests. The game owner has confirmed that the locked Reactor SDK supports this route; no new dependency or model-selector setting is currently requested.
- [ ] Allocate the persistent campaign deliberately at one agreed quota-file location. Preserve the nine-attempt allowance and unresolved-session history across restarts and worktrees; do not initialize extra campaigns to obtain more attempts.
- [ ] Run one independent real FastH3 capture through the replacement adapter. Verify generation completion, playback and capture of usable frames and produces a five-second, 24 fps, silent H.264 MP4 under the media limits.
- [ ] Record real frame timing, visual quality, dimensions, file size, total latency, remaining attempts and independently confirmed provider closure.
- [ ] Complete a full live relay using three fresh sessions, each receiving only the current player's prompt. Check that B and C see only their permitted clue at each step.
- [ ] Score the real final guesses with the already verified local MiniLM model. Confirm that author A remains unscored and that inference failure produces an unscored reveal.
- [ ] Run the allocated forced-failure trial and verify an unscored result, owned encoder cancellation, persistent attempt consumption and cleanup blocking when closure is uncertain.
- [ ] Complete the remaining live/event-device portions of DEMO-02, DEMO-07 and DEMO-08, then update the evidence checklist.

The proposed first campaign sequence is one capture, a three-attempt full relay and one forced-failure attempt; allocation is still pending. Local tests already verify 120 supplied frames becoming an ordered five-second MP4, cancellation and offline scoring. Those existing capture checks do not establish compatibility with the new FastH3 playback flow; that replacement still needs its own tests and real trial. See the [Reverse handoff](docs/development/handoffs/reverse-prompt.md), [laptop evidence](docs/research/reverse-prompt/laptop-verification.md) and [runbook](scripts/games/reverse-prompt/README.md).

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
