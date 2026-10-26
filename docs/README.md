# VibeParty documentation

VibeParty is a multiplayer party-game app being developed for the Worlds hackathon.

## Start here

- [Portal specification](portal-spec.md): home page, host/join entry, return/replay loop, and build order.
- [Room code standard](shared/room-code-spec.md): four-digit entry codes, validation, generation, and lifecycle shared by every game.
- [Game testing and video evidence plan](development/testing-and-video-plan.md): Codex browser walkthroughs, automated checks, per-game acceptance, screenshot-to-MP4 exports, and implementation gaps.
- [Two-minute VEED demo inputs](demo/veed/veed-guide.md): presenter image, full transcript, four narration sections, and generation instructions.
- [Game specifications](#game-specifications): rules, technical stack, scope decisions, and research for each game.
- [Product backlog](backlog.md): requested game improvements awaiting design and implementation.
- [Hackathon scope](hackathon.md): official event link, our demo limitations, and future exploration.
- [Parallel development plan](parallel-development-plan.md): four-worktree implementation of the portal and all three games on the host laptop, with explicit portal milestones, shared contracts, ownership, and integration checkpoints. The foundation adopts all three games in the portal scope.

The repository contains a runnable React/FastAPI foundation. Run `bash scripts/setup.sh`, then `bash scripts/dev.sh`, or `bash scripts/demo.sh` for the combined server. Game availability follows integrated playable milestones. The app spec defines product purpose and document ownership, the portal spec defines entry and navigation, and each game's dedicated specifications define its demo.

## Local configuration

Follow [Local environment setup](environment-setup.md) for prerequisites, private `.env` configuration, local mode, LAN origins, provider readiness, and worktree setup.

## What we're building

VibeParty includes the portal and three video party games: Word by Word, Prompt Royale, and Reverse Prompt. The [app specification](app-spec.md) defines product scope and document ownership; the [portal specification](portal-spec.md) defines entry and navigation. Player counts, timers, roles, and round flows belong to the game specifications below.

## Game specifications

Each game uses the same document names. Start with its game spec, then follow the technical stack. Simplification records the scope cuts and accepted limitations; research records provider evidence and outstanding verification.

| Game | Rules and acceptance | Implementation | Scope decisions | Provider research |
| --- | --- | --- | --- | --- |
| Word by Word | [Game spec](games/word-by-word/game-spec.md) | [Technical stack](games/word-by-word/tech-stack.md) | [Simplification](games/word-by-word/simplification.md) | [Research](research/word-by-word/README.md) |
| Prompt Royale | [Game spec](games/prompt-royale/game-spec.md) | [Technical stack](games/prompt-royale/tech-stack.md) | [Simplification](games/prompt-royale/simplification.md) | [Research](research/prompt-royale/README.md) |
| Reverse Prompt | [Game spec](games/reverse-prompt/game-spec.md) | [Technical stack](games/reverse-prompt/tech-stack.md) | [Simplification](games/reverse-prompt/simplification.md) | [Research](research/reverse-prompt/README.md) |

Additional references:

- [Experiments](experiments/README.md): dated comparisons, account checks, and measured results, including Helios vs FastH3 pricing, speed, and 480p support.
- [Word by Word: standard test scenarios](games/word-by-word/test-scenarios.md): category instructions, exact example answers, expected scene additions, and a result record to reuse in future tests.
- [Word by Word: Consequences](research/word-by-word/consequences.md): traditional-game reference and the origin of the adaptation.
- Reverse Prompt's archived [game spec](games/reverse-prompt/archive/game-spec-v1.md) and [technical stack](games/reverse-prompt/archive/tech-stack-v1.md): historical designs before simplification.

## Shared standards and plans

- [Room code standard](shared/room-code-spec.md): four-digit room entry shared by the portal and every game. Shared standards live in `shared/`.
- [Host controls and player names](shared/host-controls-and-names.md): consistent host actions, end-game confirmation, and editable random name prefills.
- [FastH3 smoothing proposal](shared/fast-h3-smoothing.md): historical playback research and proposed validation, retained as evidence. Current capture behavior belongs to each game’s technical stack.
- [App specification](app-spec.md): product purpose, app boundaries, and ownership of requirements across the portal and games.
- [Backend specification](backend-spec.md): broader backend proposal; its database/queue architecture is deferred for all three dedicated game demos.

## Folder layout

```text
docs/
  README.md
  portal-spec.md
  app-spec.md
  backend-spec.md
  hackathon.md
  shared/                # Standards used by the portal and every game
    room-code-spec.md
    host-controls-and-names.md
    fast-h3-smoothing.md
  games/<game>/
    game-spec.md
    tech-stack.md
    simplification.md
    archive/             # Superseded specs, where available
  research/<game>/
    README.md            # Provider research
    consequences.md      # Word by Word's reference note
  experiments/           # Dated comparisons and experiment evidence
    README.md
```

Use `word-by-word`, `prompt-royale`, and `reverse-prompt` as the game folder names. Keep standards that apply across games in `shared/`, game-specific rules and implementation decisions in `games/`, supporting evidence in `research/`, and superseded designs in the relevant game's `archive/`.

## Reactor resources

Use the [Reactor Model API reference](https://docs.reactor.inc/model-api-reference/overview) for each model's commands, parameters, and events. Useful starting points from the Reactor resource slide:

- [Documentation](https://docs.reactor.inc): guides and references for building with Reactor.
- [Model catalog](https://reactor.inc/models): browse the available models.
- [API keys](https://reactor.inc/account/api-keys): create an API key.
- [Cookbook examples](https://github.com/reactor-team/reactor-cookbook/tree/main/examples): example apps to read and fork.

The slide also lists this command to scaffold a working app:

```sh
npx create-reactor-app
```
