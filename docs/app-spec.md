# VibeParty: app specification

[All docs](README.md) · [Portal specification](portal-spec.md)

Status: product scope and document ownership, 12 September 2026. The repository contains plans; implementation has not started.

## 1. Product purpose

VibeParty is a browser party-game app that turns a group's creative contributions into AI-generated videos. Friends create, watch, and react together through different games.

The [Worlds hackathon](hackathon.md) delivery goal is a complete group experience: enter the app, finish a game, and return for another round. Each game provides its own way to create and reveal the result.

**Inspiration and credit:** Reverse Prompt is inspired by the classic game [Telephone](https://en.wikipedia.org/wiki/Telephone_game), where players pass a whispered message from person to person and compare the final message with the original. Our adaptation passes the idea through AI-generated videos and human descriptions, then adds final guesses and similarity scoring.

## 2. Where requirements live

The [portal specification](portal-spec.md) owns game availability, home-page content, host/join entry, session continuation, return navigation, and the portal build plan. A completed game specification does not by itself make that game available in the portal.

The [room code standard](shared/room-code-spec.md) owns the shared four-digit entry code format, validation, generation, and lifecycle for the portal and all three games. Game-specific admission and authorization follow each game's specifications.

Each **game spec** owns its player counts, roles, round flow, screens, inputs, timers, scoring, privacy, failures, replay behavior, and demo acceptance. Its **technical stack** owns runtime architecture, APIs, provider integration, spending limits, cleanup, build order, and implementation checks.

| Game | Rules and demo acceptance | Implementation and build plan |
| --- | --- | --- |
| Word by Word | [Game spec](games/word-by-word/game-spec.md) | [Technical stack](games/word-by-word/tech-stack.md) |
| Prompt Royale | [Game spec](games/prompt-royale/game-spec.md) | [Technical stack](games/prompt-royale/tech-stack.md) |
| Reverse Prompt | [Game spec](games/reverse-prompt/game-spec.md) | [Technical stack](games/reverse-prompt/tech-stack.md) |

The [documentation index](README.md#game-specifications) also links each game's simplification decisions and provider research. Those explain the decisions and evidence; the current game and technical specifications define what to build.

The [backend specification](backend-spec.md) is a broader architecture proposal for future expansion. Current demo infrastructure is defined by the technical stacks above.

## 3. App boundaries

The portal and all three games target the host laptop for development and the demo. One local server serves the frontend and API over HTTP; phones join its LAN address on the same Wi-Fi or hotspot. Live generation still uses external providers, and Reverse Prompt scoring runs locally. Remote deployment is deferred. Each game's technical plan and the [local environment guidance](environment-setup.md) define setup and verification.

- Present the portal and games under the VibeParty identity. The portal and game specs define their concrete copy, controls, and screens.
- A launched game follows its own roles and room lifecycle. Shared components must preserve those rules; one game's defaults must not become requirements for another game.
- Results belong to their game. There is no combined score or ranking across games.
- Change behavior in the document that owns it and update links where needed. Keep detailed rules, numeric limits, and checklists there so this app specification stays a product overview.

## 4. Delivery scope and completion

The confirmed development scope is the portal and all three playable games running locally. The [parallel development plan](parallel-development-plan.md) defines worktree ownership and integration milestones; its foundation milestone extends the portal's earlier Word by Word launch plan to all three games. Follow each game's technical plan for its implementation sequence and integration gates.

Release readiness comes from the [portal acceptance checks](portal-spec.md#7-acceptance-checks) and each enabled game's demo acceptance, linked above. Record live verification in that game's research directory. A second app-level copy of those checklists is unnecessary.

Future features and archived designs become implementation requirements only when explicitly adopted in the relevant current specification.
