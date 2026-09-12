## Inspiration

We adapted familiar party games into shared AI video experiences:

| Our game | Inspired by |
| --- | --- |
| Word by Word | Consequences |
| Prompt Royale | Quiplash by Jackbox Games |
| Reverse Prompt | Telephone |

## What it does

VibeParty brings friends together through three browser games, hosted on a laptop with players joining from their phones:

- **Word by Word:** Secret contributions build one evolving video scene.
- **Prompt Royale:** Players write prompts for a shared topic, watch anonymous clips, and vote for their favorite.
- **Reverse Prompt:** Players pass an idea through videos and descriptions, then guess the original prompt.

## How we built it

React, TypeScript, and Vite power the frontend, with Python and FastAPI on the backend. The demo uses one local server, in-memory rooms, HTTP polling, and FFmpeg to prepare saved video clips.

| Model | Role |
| --- | --- |
| Reactor FastH3 | Video generation for Word by Word and Reverse Prompt |
| Reactor Helios | Video generation for Prompt Royale |
| all-MiniLM-L6-v2 | Local similarity scoring for Reverse Prompt through Sentence Transformers |

## Challenges we ran into

Building the portal and all three games in parallel made integration and thorough testing challenging. We coordinated coding agent sessions in real time to work in parallel and used computer use to play through the games as a human tester would.

## Accomplishments that we're proud of

- Reimagined traditional party games using generative AI to turn players' ideas into shared video experiences.
- Integrated a shared portal and all three games into a runnable local demo.
- Added labelled fixture rounds, replay, and navigation between games.

## What we learned

We learned how to work with video generation models and build more efficiently by coordinating coding agents in parallel.

## What's next for VIbeParty

- Deploy VibeParty online.
- Run more evaluations of video generation quality, speed, reliability, and cost.
- Explore increasing support from four to eight players.
- Add more games to VibeParty.
