# VibeParty: hackathon scope

Event: [Worlds — official event page](https://worlds.london/). Track selection remains open.

## Our demo limitations

- **Local target:** build the portal and all three games on the host laptop; phones join its HTTP LAN address on the same Wi-Fi or hotspot. Remote deployment is deferred. The laptop needs internet access for live providers.
- **Completion first:** prioritize the [portal → game → replay loop](portal-spec.md). Add polish after the complete flow works.
- **Small groups:** each game targets one supervised room. Player caps reflect our generation capacity and rehearsal scope; they are project decisions, not claimed provider limits.
- **Limited recovery:** accept losing the room on server restart to keep the build small. Each game's technical plan defines the safeguards for paid generation.
- **Live integration remains unverified:** capture reliability, visual quality, latency, and cost need real rehearsals. A scripted fixture does not prove live readiness.

Detailed limits and tradeoffs stay with each game:

- [Word by Word](games/word-by-word/simplification.md)
- [Prompt Royale](games/prompt-royale/simplification.md)
- [Reverse Prompt](games/reverse-prompt/simplification.md)

## After the demo

Explore larger groups and simultaneous rooms after full-round rehearsals establish timing, cost, and provider capacity. Add persistent state and broader recovery when those become requirements.
