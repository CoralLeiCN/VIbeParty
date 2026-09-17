# Agent Instructions

## Feature changes and specifications

Keep feature behavior and its specifications aligned in the same change. Before implementing a feature change, read the relevant current specifications. When adding, changing, or removing behavior, update the specification that owns it, including affected user flows, labels, rules, and acceptance criteria. Follow the document ownership defined in [the app specification](docs/app-spec.md); put requirements shared across games in the shared standards and link them from the affected game specs. Before reporting completion, verify that the implementation and current specifications agree. Backlog updates and implementation notes supplement the specifications; they do not replace them.

## Testing

Do not write tests for reversible, low-impact changes that mirror the implementation. If you do choose to verify your work with tests, make sure that the tests are meaningful and necessary to verify implementation.

Run tests appropriate to the change and complete required checks. Once those pass, broaden or repeat testing only when new changes, failures, or unresolved concerns justify it; otherwise, continue toward completing the task.

For frontend changes that affect visible behavior, use the browser to verify the affected flows when available.

For Word by Word rehearsals, fixture preparation, and model evaluations, use the category instructions, example answers, and expected effects in [the standard test scenarios](docs/games/word-by-word/test-scenarios.md). Record the scenario ID and results; follow that document's mapping to the current demo's four slots.

## Writing

Use plain language over jargon, and reference technical details only to the degree that it helps illustrate an idea or your work to the user. Communicate complex concepts in a clear and cohesive manner, and calibrate your writing to the level of background knowledge assumed from the user's prompt and context.

Avoid using slop words or phrases like "Bottom Line:" in conclusions, "delve," "foster," "leverage," "it's worth noting," "importantly," "Question? Answer." or "This isn't about X. It's about Y.", "genuinely" or hyphenated compound descriptions and adjectives. Do not use concluding summary statements such as "In short:..", "The simplest mental model is:...".

State the intended action directly. Avoid adding what you won't do, what will remain unchanged, or how you'll separate or categorize results. Do not use contrastive framing such as "X, not Y" or "X—not Y" that introduces an unprompted alternative that the user didn't ask about. Avoid invented compound labels like "exact-head checks" and "editorial-row layouts", vague qualifiers, and canned transitions; use plain verbs and prepositions to state the actual relationship directly.
