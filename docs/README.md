# VibeParty documentation

VibeParty is a multiplayer party-game app being developed for the Worlds hackathon.

## Start here

- [Portal specification](portal-spec.md): home page, host/join entry, return/replay loop, and build order.
- [Game specifications](#game-specifications): rules, technical stack, scope decisions, and research for each game.
- [Hackathon scope](hackathon.md): official event link, our demo limitations, and future exploration.

The repository contains planning documents; the app has not been implemented. The app spec defines product purpose and document ownership, the portal spec defines entry and navigation, and each game's dedicated specifications define its demo.

## What we're building

We're building a browser app that turns a group of friends' ideas into AI-generated videos. Players join a private room on their phones, contribute words or prompts, and watch the results together through cooperative games, voting, and guessing.

The hackathon demo includes:

- **Main portal:** One home page to host or join Word by Word, return to the current party, and discover two coming-soon games.
- **Word by Word:** Secretly contribute four words inspired by Consequences, then reveal four connected video segments, each adding the next word to the scene. Everyone creates together; there is no winner.
- **Group play:** One room, three or four player phones, a separate host laptop, guest names, a join code/link, and browser refresh recovery while the server stays running.
- **Complete round loop:** Join, contribute, watch the reveal, replay saved clips, and start another round with the same players or return to the portal.

Two more games appear on the portal as **Coming soon**:

- **Prompt Royale:** Write prompts for the same topic, watch the generated clips anonymously, and vote for a favorite. The most votes wins.
- **Reverse Prompt:** Pass an idea through a chain of videos and descriptions, then guess the original prompt. Guesses score on similarity in meaning, and the final reveal shows how the idea changed.

## Demo limitation

The portal's initial launch exposes Word by Word, with Prompt Royale and Reverse Prompt marked coming soon. Word by Word supports three or four player phones plus a separate host screen. Its QR joining is optional polish; a working join link and room code are required.

Prompt Royale's dedicated demo plan supports three or four players including the playing host. Reverse Prompt uses exactly three players, including its playing host, with no input countdowns. Each simplified demo runs one room at a time and follows its own specification; a server restart loses the current room. Join codes and links follow each game's demo scope.

## Game specifications

Each game uses the same document names. Start with its game spec, then follow the technical stack. Simplification records the scope cuts and accepted limitations; research records provider evidence and outstanding verification.

| Game | Rules and acceptance | Implementation | Scope decisions | Provider research |
| --- | --- | --- | --- | --- |
| Word by Word | [Game spec](games/word-by-word/game-spec.md) | [Technical stack](games/word-by-word/tech-stack.md) | [Simplification](games/word-by-word/simplification.md) | [Research](research/word-by-word/README.md) |
| Prompt Royale | [Game spec](games/prompt-royale/game-spec.md) | [Technical stack](games/prompt-royale/tech-stack.md) | [Simplification](games/prompt-royale/simplification.md) | [Research](research/prompt-royale/README.md) |
| Reverse Prompt | [Game spec](games/reverse-prompt/game-spec.md) | [Technical stack](games/reverse-prompt/tech-stack.md) | [Simplification](games/reverse-prompt/simplification.md) | [Research](research/reverse-prompt/README.md) |

Additional references:

- [Word by Word: Consequences](research/word-by-word/consequences.md): traditional-game reference and the origin of the adaptation.
- Reverse Prompt's archived [game spec](games/reverse-prompt/archive/game-spec-v1.md) and [technical stack](games/reverse-prompt/archive/tech-stack-v1.md): historical designs before simplification.

## Shared plans

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
  games/<game>/
    game-spec.md
    tech-stack.md
    simplification.md
    archive/             # Superseded specs, where available
  research/<game>/
    README.md            # Provider research
    consequences.md      # Word by Word's reference note
```

Use `word-by-word`, `prompt-royale`, and `reverse-prompt` as the game folder names. Keep current rules and implementation decisions in `games/`, supporting evidence in `research/`, and superseded designs in the relevant game's `archive/`.

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
