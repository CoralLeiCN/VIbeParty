# VibeParty documentation

VibeParty is a multiplayer party-game app being developed for the Worlds hackathon.

## What we're building

We're building a browser app that turns a group of friends' ideas into AI-generated videos. Players join a private room on their phones, contribute words or prompts, and watch the results together through cooperative games, voting, and guessing.

The planned first release includes:

- **Word by Word:** Build a shared prompt one word at a time, then turn it into a short video of an imagined world. Everyone creates together; there is no winner.
- **Prompt Royale:** Write prompts for the same topic, watch the generated clips anonymously, and vote for a favorite. The most votes wins.
- **Reverse Prompt:** Pass an idea through a chain of videos and descriptions, then guess the original prompt. Guesses score on similarity in meaning, and the final reveal shows how the idea changed.
- **Easy group play:** Private rooms for four players, join codes and QR links, guest names, and sessions that players can reconnect to.
- **Shared party controls:** A lobby, game selection, timers, generation progress, video replays, round results, and an optional shared display for public game content.

## Demo limitation

For the current demo, we're focusing on four players per room across all three games. Support for other group sizes is outside the demo scope.

## Documentation

- [Hackathon overview](hackathon.md): event context and partners.
- [App and game specification](app-spec.md): player experience, the three games, scoring, and MVP acceptance criteria.
- [Python backend specification](backend-spec.md): architecture, data, APIs, generation jobs, and engineering practices.

The specifications describe the proposed implementation. The repository does not yet contain the app.
