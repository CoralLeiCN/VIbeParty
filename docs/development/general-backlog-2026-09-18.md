# General backlog implementation

18 September 2026. Scope: [GEN-001 and GEN-002](../backlog.md). Requirements: [shared host controls and player names](../shared/host-controls-and-names.md).

## Implementation

GEN-001 introduced shared host controls, confirmation, and action labels. GEN-002 introduced editable random player-name prefills. The [shared standard](../shared/host-controls-and-names.md) owns their behavior and acceptance criteria. This dated record retains the verification performed for that delivery.

## Verification

- Frontend production build and ESLint pass. Backend Ruff lint and format checks pass.
- All 239 backend tests pass, including returning to Word by Word setup after exhausting live attempts while retaining the roster and enforcing the live limit.
- All 15 Chromium checks pass (10 portal/entry checks and 5 integration/recovery checks). Browser entry checks cover accepted suggested names, edited names retained after an invalid room code, guest refresh, host-only controls, confirmation cancellation and focus restoration, failed closure and retry, and return to the portal.
- Complete fixture rounds check identical result controls at 1360px and 390px widths, rematches preserving room codes and players, and closure invalidating guest access and old media. Host recovery and switching checks use the updated labels.
- Word by Word rehearsal: **WW-CAT-01**, three joined players, current four-slot mapping. Place = `Enchanted forest`; Character = `A fox wearing a crown`; Action = `Dances ballet`; Consequence = `Glowing snow begins falling`. The fixture round reaches results with all four cards, saved replay, and a rematch retaining the room and roster. This verifies the interface and lifecycle using scripted media; no live model generation was run.

Browser screenshots are written under the ignored `frontend/test-results/` directory by the combined integration test.
