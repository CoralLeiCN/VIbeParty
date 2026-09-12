# VibeParty documentation

VibeParty is a multiplayer party-game app being developed for the Worlds hackathon.

## What we're building

We're building a browser app that turns a group of friends' ideas into AI-generated videos. Players join a private room on their phones, contribute words or prompts, and watch the results together through cooperative games, voting, and guessing.

The planned first release includes:

- **Word by Word:** Secretly contribute four words inspired by Consequences, then reveal four connected video segments, each adding the next word to the scene. Everyone creates together; there is no winner.
- **Prompt Royale:** Write prompts for the same topic, watch the generated clips anonymously, and vote for a favorite. The most votes wins.
- **Reverse Prompt:** Pass an idea through a chain of videos and descriptions, then guess the original prompt. Guesses score on similarity in meaning, and the final reveal shows how the idea changed.
- **Easy group play:** Private rooms with game-specific player counts, guest names, and browser refresh recovery; join codes and QR links follow each game’s demo scope.
- **Shared party controls:** A lobby, game selection, timers, generation progress, video replays, round results, and an optional shared display for public game content.

## Demo limitation

Prompt Royale supports three or four players including the playing host; Word by Word supports three or four player phones plus a separate host screen. Reverse Prompt uses exactly three players, including its playing host, with no input countdowns. Each simplified demo runs one room at a time and follows its dedicated specification.

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

## Documentation

- [Hackathon overview](hackathon.md): event context and partners.
- [App and game specification](app-spec.md): broader three-game design; each game's dedicated demo rules take precedence.
- [Python backend specification](backend-spec.md): broader backend baseline; its database/queue architecture is deferred for all three dedicated game demos.
- [Word by Word: hackathon game specification](word-by-word-spec.md): one room, three/four players, four private words, additive video reveal, and replay.
- [Word by Word: hackathon technical stack](word-by-word-tech-stack.md): one FastAPI process, in-memory state, polling, Reactor, and local clips.
- [Word by Word: simplification before and after](research/word-by-word/hackathon-simplification.md): removed infrastructure, reduced gameplay scope, and accepted demo limitations.
- [Word by Word: Consequences reference](word-by-word.md): chosen traditional-game reference and the origin of the adaptation.
- [Word by Word: Reactor and VEED research](research/word-by-word/README.md): provider capabilities, game fit, pricing discrepancies, and outstanding live verification.
- [Prompt Royale game specification](games/prompt-royale/game-spec.md): simplified four-player demo rules, timing, scoring, failures, and acceptance criteria.
- [Prompt Royale technology choices and stack](games/prompt-royale/tech-stack.md): one-process architecture, per-technology usage map, single retry, deployment, and validation.
- [Prompt Royale simplification: before and after](games/prompt-royale/simplification.md): removed infrastructure, reduced scope, and explicit tradeoffs.
- [Prompt Royale partner research](research/prompt-royale/README.md): Reactor and VEED fit, integration proposals, pricing, limits, and validation gates.
- [Reverse Prompt before and after](games/reverse-prompt/simplification.md): concrete hackathon scope cuts, technology changes, and accepted tradeoffs.
- [Reverse Prompt game specification](games/reverse-prompt/game-spec.md): current three-player demo rules, screens, privacy, scoring, and acceptance criteria.
- [Reverse Prompt tech stack](games/reverse-prompt/tech-stack.md): one FastAPI process, Reactor Helios generation, local Sentence Transformers scoring, and private local clips.
- [Reverse Prompt: Reactor and VEED research](research/reverse-prompt/README.md): provider capabilities, game fit, proposed integration, cost, and validation gates.

The specifications describe the proposed implementation. The repository does not yet contain the app. All three games have dedicated hackathon documents that override the broader app/backend requirements for their demo; the games retain separate implementation plans.
