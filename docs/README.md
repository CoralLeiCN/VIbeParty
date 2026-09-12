# VibeParty documentation

VibeParty is a multiplayer party-game app being developed for the Worlds hackathon.

## What we're building

We're building a browser app that turns a group of friends' ideas into AI-generated videos. Players join a private room on their phones, contribute words or prompts, and watch the results together through cooperative games, voting, and guessing.

The planned first release includes:

- **Word by Word:** Secretly contribute four words inspired by Consequences, then reveal four connected video segments, each adding the next word to the scene. Everyone creates together; there is no winner.
- **Prompt Royale:** Write prompts for the same topic, watch the generated clips anonymously, and vote for a favorite. The most votes wins.
- **Reverse Prompt:** Pass an idea through a chain of videos and descriptions, then guess the original prompt. Guesses score on similarity in meaning, and the final reveal shows how the idea changed.
- **Easy group play:** Private rooms for four players, join codes and QR links, guest names, and sessions that players can reconnect to.
- **Shared party controls:** A lobby, game selection, timers, generation progress, video replays, round results, and an optional shared display for public game content.

## Demo limitation

Four players is the default demo group. Prompt Royale and Reverse Prompt retain that four-player scope. The simplified Word by Word demo supports three or four player phones and a separate host screen, with one room at a time; its dedicated specifications define that exception.

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
- [App and game specification](app-spec.md): player experience, the three games, scoring, and MVP acceptance criteria.
- [Word by Word: hackathon game specification](word-by-word-spec.md): one room, three/four players, four private words, additive video reveal, and replay.
- [Word by Word: hackathon technical stack](word-by-word-tech-stack.md): one FastAPI process, in-memory state, polling, Reactor, and local clips.
- [Word by Word: simplification before and after](research/word-by-word/hackathon-simplification.md): removed infrastructure, reduced gameplay scope, and accepted demo limitations.
- [Word by Word: Consequences reference](word-by-word.md): chosen traditional-game reference and the origin of the adaptation.
- [Word by Word: Reactor and VEED research](research/word-by-word/README.md): provider capabilities, game fit, pricing discrepancies, and outstanding live verification.
- [Python backend specification](backend-spec.md): architecture, data, APIs, generation jobs, and engineering practices.

The specifications describe the proposed implementation. The repository does not yet contain the app. Word by Word's dedicated hackathon documents override the broader app/backend requirements for that demo; the other games retain their separate plans.
