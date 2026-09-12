# Reverse Prompt: hackathon game specification

Version: 2.1 demo scope. Updated: 12 September 2026. Status: proposed, not implemented.

Build one complete, presenter-led game for **exactly three people in one private room**. This is the current source of truth for Reverse Prompt, superseding its broader requirements in the [shared app specification](../../app-spec.md). See the [tech stack](tech-stack.md), [before and after](simplification.md), and [archived original spec](archive/game-spec-v1.md).

## 1. The game we are demonstrating

One player writes a scene. Reactor generates a five-second video. The next player privately describes that video, creating a new video; the third player repeats this. Everyone watches the final result, the two interpreters guess the original prompt, and the full chain is revealed with similarity scores.

The essential experience is seeing how a scene changes through human interpretation. Keep real generation, private clues, separate final guesses, and an entertaining reveal. English text, individual phone browsers, and a presenter guiding the room are sufficient. Scores are casual entertainment: players remember different clues, so this is not a fair ranked contest.

## 2. Fixed demo settings

| Setting | Decision |
| --- | --- |
| Room and roster | One room; exactly three players; no joining during a round |
| Roles | Creator is host and author A; guests B and C follow join order |
| Round | `P0 → V0 → P1 → V1 → P2 → V2 → final guesses → reveal` |
| Clip | Five seconds, landscape, silent, tap-to-play and replay |
| Input | 1–300 Unicode code points and within the local model's token limit; English; plain text |
| Input timing | No countdowns; submit at your own pace; presenter nudges or resets |
| Generation | One attempt per video; 90-second application deadline; no automatic retry |
| Scoring | One local Sentence Transformers batch after both guesses; 15-second deadline |
| Replay | Host resets to lobby; same players and roles; new round ID |
| Recovery | Browser refresh restores identity while the server is running; server restart loses the round |
| Optional polish | One prerecorded VEED intro after the core demo works |

These are demo defaults, not provider speed promises. Target a roughly three-to-five-minute rehearsal, then measure actual pacing. Three slow generations can exceed that target. Do not add more players to the judged demonstration.

## 3. Complete player flow

1. **Join.** The presenter creates a room using the configured organizer code and a display name. Two guests enter the displayed room code and names at the same URL. The lobby lists A, B, and C. Names are 1–24 characters; duplicate names receive visible suffixes. Start is enabled with three registered players, available generation capacity, and the local scoring model loaded. The presenter confirms everyone is looking at their phone; no player readiness system is needed.
2. **Original.** A writes `P0`, for example “A tiny astronaut pours tea for a giant frog.” B and C see whose turn it is. A successful submission is final. Generate `V0` using only `P0` and the fixed rendering instruction.
3. **First interpretation.** Only B can retrieve and replay `V0`. B describes what they see as `P1`. Generate `V1` using only `P1` and the same instruction, in a fresh provider session.
4. **Second interpretation.** Only C can retrieve and replay `V1`. C submits `P2`. Generate `V2` independently from `P2`.
5. **Guess.** All three see `V2`. B and C each submit a separate final guess of `P0`. C may copy their own interpretation into the guess field, but must explicitly submit it. A sees “Author — unscored.” Guesses stay private until both are accepted.
6. **Score and reveal.** Compare both guesses with the exact accepted original prompt. Display the original, three ordered prompt/video cards with player names, both final guesses, scores, and the winner or tie. Reveal cards can be replayed individually; no exported recap video is required.
7. **Reset.** Host returns to the lobby after results or stops an incomplete round. Reset clears round content and files after active work stops. It keeps the roster and roles, and never replenishes the session quota. A server restart creates a fresh lobby and requires everyone to join again.

## 4. Screens and privacy

Use one responsive page that renders the current phase. Large buttons, labelled inputs, visible submission status, a character counter, keyboard access, and a native video player are enough. Render user text as text, never HTML.

| Phase | Active player sees | Other players see |
| --- | --- | --- |
| Lobby | Names, join code, short rules; host Start | Same lobby without host controls |
| Author input | A: original prompt editor | “Waiting for A to write the first scene” |
| Generating | Accepted status, whose clip is being made, elapsed time | Public progress only |
| Relay input | B or C: assigned clip and description editor | “Waiting for B/C to describe their video” |
| Guessing | B/C: final clip and guess editor; A: final clip | Submission counts, never another guess |
| Scoring | Final clip and “Comparing guesses” | Same |
| Reveal | Entire ordered chain, guesses, scores | Same |
| Error | Plain failure message; host Reset | Same, with no hidden chain automatically revealed |

Before reveal, snapshots contain only public progress, the requesting player's own accepted text, and their currently permitted media reference. During relay input, only its assigned interpreter can fetch the clue. When that turn ends, that permission ends. During guessing/scoring, everyone can fetch only `V2`. Reveal permits all three clips. The host has no extra content access. Enforce this on the server, including video range requests; hiding an element is insufficient.

No shared-display role is required. Project the host's browser only at guessing/reveal, after any private author text is off screen. There are no accounts, invitations to spectators, QR generation, chat, uploads, galleries, or player removal controls.

## 5. Submission and scoring rules

Normalize text with Unicode NFC and trim outer whitespace; preserve case, punctuation, negation, and internal wording. Reject empty input, more than 300 code points, or text exceeding the loaded model's token limit, including special tokens; never silently truncate. Return a correctable validation message. The UI distinguishes “Submitting” from “Accepted.” Validation is local and checks format/length, not content safety; no external moderation request is required before acceptance.

Accept one submission per player and expected step. A duplicate request returns its previous result, a conflicting replacement is rejected, and a stale request after reset cannot change the new round. Do not auto-write interpretations, improve prompts, or substitute AI guesses.

Use local Sentence Transformers with `sentence-transformers/all-MiniLM-L6-v2` and CPU PyTorch. Encode the original and both accepted final guesses in one local batch using the same pinned model and preprocessing. No OpenAI service or API key is required. Store scores once for that round. Compute cosine similarity, then apply this game rule:

```text
similarity = dot(original_vector, guess_vector) / (norm(original_vector) * norm(guess_vector))
points = floor(100 * clamp(similarity, 0, 1) + 0.5)
```

An identical normalized guess gets 100. A similarity of 0.824 gets 82; a negative value gets 0. Highest integer score wins, including a tie at 0. Equal scores produce joint winners. A is always excluded. Display “Similarity: 82 / 100”; explain that meaning is compared and details may be missed. Do not describe this as accuracy or use an LLM judge. Provider rationale is in the [scoring decision](tech-stack.md#5-scoring-and-text-moderation).

If local inference fails, times out, or returns invalid vectors, reveal the completed chain and both guesses as **unscored**, with no partial ranking. If someone never guesses, the presenter asks them to finish or resets; there is no missing-guess scoring branch.

## 6. Failure and demo operation

- Any generation failure, timeout, provider rejection, or unusable video ends the round unscored on the error screen. No skipped relay steps, paid retries, or automatic fixture substitution. The host can reset once session cleanup permits it.
- A browser refresh fetches current authorized state. A lost cookie, closed device, or absent host is handled by the presenter restarting the demo; no account recovery or host migration.
- Host Reset stops the round without exposing unfinished private content. If provider termination cannot be confirmed, block further generation until the operator resolves it. A new room or server restart cannot bypass the quota or this block.
- Use benign, visual prompts in the presented demo. Reactor applies its own checks to generation input; there is no separate app content classifier for names, guesses, or videos. If an unsuitable result appears, the presenter stops the round. Explain in the lobby that scene prompts go to Reactor for video generation, while final guesses are scored locally. Provider rejection may happen after a paid session begins.
- Delete local round media on reset and startup, and stop the service/clear remaining media after the event. Do not log prompts, guesses, cookies, or provider credentials. This is local app cleanup; provider retention is separate.
- An optional explicit **Rehearsal** mode may use a fixed scripted chain with sample scores. Label it throughout and select it before starting. It is not a live-generation success and is not a required build feature.

## 7. Demo acceptance

| ID | Pass condition |
| --- | --- |
| DEMO-01 | Three browser sessions join one room; a fourth is rejected; only the host can start/reset. |
| DEMO-02 | One round creates exactly three independent Reactor videos from the three accepted prompts. |
| DEMO-03 | B alone can fetch `V0` on their turn, C alone can fetch `V1` on theirs; unauthorized snapshots and media/range requests reveal nothing private. |
| DEMO-04 | Both guesses compare locally with `P0` using the preloaded Sentence Transformers model, without scoring-network access; token-limit rejection, ties, exact matches, and score failures work; A cannot guess. |
| DEMO-05 | Duplicate clicks create one submission/session; a late callback or command after reset cannot alter the next round. |
| DEMO-06 | Refresh restores the right phase; a backend restart loses the round but preserves the generation quota and unresolved-session block. |
| DEMO-07 | Videos play/replay on the actual demo phones; reveal presents all three prompt/video pairs in order. |
| DEMO-08 | A generation timeout stops the round and initiates termination; provider cap and quota are verified before the event. |

Ship after a complete live three-player rehearsal and one deliberately failed generation. VEED, animations, and any post-hackathon feature are optional after these pass.
