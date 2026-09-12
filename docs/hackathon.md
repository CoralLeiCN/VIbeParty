# Worlds Hackathon

This project is being developed as a demo for [Worlds](https://worlds.london/?utm_source=luma), a curated, one-day hackathon in King's Cross, London, focused on building with world models.

## About the event

Worlds brings engineers, founders, and artists together to explore how world models can change games, media, and robotics. The event gives participants a chance to build working prototypes across five tracks, meet others working in the field, and test ambitious ideas in a hands-on setting.

The atmosphere is intended to feel more like a launch party than a conference: sharp people, fast-moving builds, and an emphasis on leaving with something that works.

The judges are people building the models themselves, giving participants an opportunity to demonstrate their ideas to the creators shaping the field.

## At a glance

- **Format:** Curated, one-day hackathon.
- **Location:** King's Cross, London.
- **Participants:** Engineers, founders, and artists.
- **Focus:** World models and their applications in games, media, and robotics.
- **Builds:** Working prototypes across five tracks.
- **Judges:** Creators building world models.

## Partners

| Partner | Description |
| --- | --- |
| [REACTOR](https://reactor.inc/?utm_source=luma) | The developer platform for world models. |
| [MULTIC](https://multic.com/?utm_source=luma) | Multiplayer interactive stories by Multic. |
| [VEED](https://veed.io/?utm_source=luma) | Interactive avatars. |

## Demo context

The demo in this repository is VibeParty, a multiplayer party-game app where players build prompts together, compete with generated clips, and guess original prompts through a video relay. See the [app and game specification](app-spec.md) and [Python backend specification](backend-spec.md). The hackathon track has not yet been selected.

## Hackathon limitations and future exploration

**Prompt Royale supports 3–4 active players per round for the hackathon, with a hard maximum of four including the playing host.** Run one room on one application process. Use in-memory state, polling, and local clips; defer the database, queue services, object storage, host failover, and paired display. Projecting the normal screening/results screen does not add a player. A server restart ends the room. Confirmed transient failures can retry once within the existing deadline and allowance; rejected or uncertain sessions do not retry. See the [before-and-after simplification](games/prompt-royale/simplification.md).

Current generation capacity, session-start throttling, clip preparation, and limited validation time make larger groups future work. This is the project's demo limit, not a four-player limit imposed by Reactor.

After the hackathon, explore five-to-eight-player rounds, provider quota increases, better queue scheduling, faster clip preparation, and the cost and screening time of larger groups. Expand only after full-round testing demonstrates reliable performance. See the [game specification](games/prompt-royale/game-spec.md#hackathon-limitations-and-future-exploration) and [technical capacity plan](games/prompt-royale/tech-stack.md#hackathon-limitation-and-future-capacity).

---

Based on the hackathon description supplied for this project. See the [Worlds website](https://worlds.london/?utm_source=luma) for event details.
