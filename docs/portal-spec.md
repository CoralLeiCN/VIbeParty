# VibeParty: portal specification

Status: foundation scope adopted, 12 September 2026. The portal and all three playable games target the host laptop over local HTTP. [App scope](app-spec.md), [parallel plan](parallel-development-plan.md), [shared contracts](development/contracts/shared.md).

## 1. Goal and scope

Give a group one front door to discover, host, join, continue and switch between Word by Word, Prompt Royale and Reverse Prompt. All three are required for release. Enable a launch action when its integrated playable loop passes; label unavailable games clearly during construction. Fixture availability does not pass live acceptance.

## 2. Home page

A short responsive page at `/` with VibeParty identity, a visible Join party action, a short invitation to gather friends, and three distinct game cards. Word by Word appears first. Use text, ordinary CSS and simple icons. Desktop has three cards; phones stack them. Label controls, show keyboard focus, use readable contrast and large tap targets.

| Game | Description | Players and host |
| --- | --- | --- |
| Word by Word | Secret words. One evolving scene. Everyone creates together. | 3–4 player phones and a separate laptop host/display; the presenter may separately join a phone. Cooperative. |
| Prompt Royale | One topic. Your wildest prompts. Watch the clips and vote for your favorite. | 3–4 players including the playing host. Both topic modes belong to the game. |
| Reverse Prompt | Pass an idea through videos and descriptions. Guess where it started. | Exactly 3 players including the playing host, who begins as author A. No input countdown. |

Room codes follow the [shared four-digit standard](shared/room-code-spec.md): exactly four ASCII digits stored as strings, including leading zeros. Shared generation, validation and entry components apply to every game.

## 3. Complete the loop

Each card leads to `/games/<game-id>/host`. Game owners handle passcode/name forms, lobbies, game phases and their admission errors. Word by Word has no host-name step; other hosts also play. Generic `/join` resolves a room code and navigates to `/games/<id>/join?code=…`, where the game validates code/name and issues a cookie. Copied links, code-only legacy links, `/host` alias and direct loads work. Links use the configured laptop LAN origin.

Opening any page never creates/resets a room or generates a round. Back to games opens `/` while preserving party, sessions and deadlines. Show Continue party only after authorized `/api/session` discovery; restore the correct role and phase. Discovery never refreshes presence/inactivity. Replay follows each game specification. **Start another round** retains the room and players; **End game** requests closure and returns to the portal, which tracks any pending cleanup. Follow the [shared controls and name-entry standard](shared/host-controls-and-names.md) for labels, confirmation, and editable random name prefills.

One active party exists across the application. A different game requires explicit host confirmation to close the current party, clear roster and replay, then launch the selected game. Explain “Everyone will need to rejoin.” Host authorization is checked by the current game. Keep the finishing/cleanup explanation visible until owned tasks and provider sessions are confirmed closed and admission is released. Unresolved closure blocks switching. Players can return/continue and ask the host to switch; they cannot close.

## 4. Recovery

Invalid code format: “Enter a 4-digit room code.” Valid but unavailable code: “That party isn't available. Check the code with your host.” Preserve editable input. Network failure: “Reconnecting…” with retry; keep last state, distinguish it from anonymous/expired session. Expired party/server restart: “This party has ended,” offer join and home/host entry. Another active game: explain its name and offer authorized continuation or generic join; only its authenticated host can close/switch. A closing party keeps joining/new hosting blocked. Game owners render full/lobby-only/wrong-passcode/phase errors. Partial results always allow return home.

Public home content exposes no roster, private submissions or media. A room code or name never authorizes continuation. New guests see normal home content and minimal active-game metadata only.

## 5. Runtime

One FastAPI process, one Uvicorn worker, built React frontend on port 8000. Phones join `http://<laptop-LAN-IP>:8000`; all devices use the same configured browser origin. Development Vite proxies API from 5173 to 8000; each worktree has isolated ports/media. Shared routing, session, errors, polling, cookies and close contracts live in [shared.md](development/contracts/shared.md). Game-owned state machines stay independent. No remote deployment, database, generic game engine or shared scoring.

## 6. Build order

Publish runnable foundation first. Build complete responsive portal while game owners prove their provider spikes. Connect each committed fixture flow as it passes. Run portal acceptance per integrated game, then combined live/LAN rehearsal after all game live gates pass. Record evidence and limitations in [portal handoff](development/handoffs/portal.md). Decorative polish follows required behavior; defer accounts, public rooms, history, export, search and QR.

## 7. Acceptance checks

- Home shows three games, accurate roles/counts and explicit runtime availability; release requires all three launchable.
- For each game complete a round, return home and resume the same role/phase; replay never regenerates.
- Manual code, copied join link, direct loads and refresh work without duplicate rooms/players. Name suggestions can be kept or edited, and form errors preserve edits.
- Back to games preserves deadlines; authenticated Continue party restores state.
- Host close/switch clears old roster/replay and requires rejoin. Pending cleanup blocks switching; players cannot close.
- Wrong code, full/in-progress game, expired room, another game active, partial result and network recovery have useful actions.
- Verify keyboard navigation, visible focus, phone viewport, host laptop and real phones at the LAN address. Run shared checks and affected game checks after each merge.

Room-code lifecycle and leading-zero acceptance follow [the shared standard](shared/room-code-spec.md#4-implementation-acceptance).
