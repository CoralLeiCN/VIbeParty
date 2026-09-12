# Prompt Royale: hackathon game specification

Version: 1.2, 12 September 2026. Status: simplified demo design with one bounded retry; no application or live performance has been validated yet.

This is the authoritative scope for the Prompt Royale hackathon demo. It overrides the broader room, recovery, and generation requirements in the [app specification](../../app-spec.md) for this game. See the [demo stack](tech-stack.md), [before-and-after decisions](simplification.md), and [partner research](../../research/prompt-royale/README.md).

## 1. Concept and rationale

**One topic. Everyone directs a short scene. The room picks its favorite.**

Three or four friends join in their browsers, privately write scene prompts for the same topic, watch generated clips anonymously, and vote for a favorite. The host plays too and counts toward the four-player maximum.

The creative prompt-and-vote inspiration comes from **Quiplash by Jackbox Games**, which includes open prompts and sentence blanks whose answers compete for other players' votes. Credit goes to Jackbox Games. [Quiplash on Steam](https://store.steampowered.com/app/351510/Quiplash/).

Prompt Royale adapts that idea to generated video. Players write complete scene descriptions; they do not have to fill a literal blank. Everyone judges the same set of clips, and human votes decide the outcome.

## 2. Demo scope

Build one invite-only room, 3–4 guest players, one fixed host, a curated topic list, prompt submission, generation, screening, voting, results, and Play again. Use one model and one video preset. Optional pre-rendered VEED host clips add presentation after the core round works.

No accounts, matchmaking, tournaments, game-switching UI, audience role, paired display, ready checks, QR generator, host transfer, player removal, timer extensions, or player-requested rerolls are required. One automatic retry for a confirmed transient failure is included. The other VibeParty games remain separate designs, not dependencies of this demo.

### Hackathon limitations and future exploration

**Four active players is a hard maximum in both live and fixture modes, including the playing host.** Start requires at least three. A fifth player gets “Room full — Prompt Royale supports up to 4 players for the hackathon.” Joining during an active round is closed; there is no waiting-list implementation.

The limit reflects current generation capacity and validation time; it is not a claim that Reactor imposes a four-player limit. First rehearse with three players, then four. Only enable the live sizes that have passed rehearsal. [Capacity research](../../research/prompt-royale/README.md#cost-capacity-and-waiting-time).

One server process holds room state in memory. Refreshing a browser recovers its state while that process is alive. A server restart ends the room and loses its results. A host absent for 30 seconds ends an active round unscored; there is no automatic replacement host.

After the hackathon, explore five-to-eight-player groups, simultaneous rooms, persistent state, automatic recovery, shared-display pairing, and richer presentation. Larger groups require new measurements of generation, cost, and screening pace, plus an explicit cap change.

## 3. Defaults

| Item | Demo rule |
| --- | --- |
| Players | 3–4, including the host; one room per deployment. |
| Name | 1–24 Unicode code points after trimming and NFC normalization; suffix duplicate names. |
| Topic | Host chooses from a small bundled list before starting. |
| Prompt | 1–500 code points after trimming and NFC normalization; entire rendered model input must also fit the 500-token application limit. |
| Prompting | 60 seconds; close early when everyone submits. No extension. |
| Generation | 180 seconds total, including queueing, capture, and preparation. |
| Retry | One recovery pass per entry for confirmed transient failures; unchanged inputs, original deadline, and at most two creation attempts. |
| Clip | Five-second silent landscape MP4; same preset and capture policy for everyone. |
| Screening | Host advances clips; 180 seconds for the entire screening phase. |
| Voting | 30 seconds; close early when everyone votes or abstains. No extension. |
| Host absence | No successful host poll/command for 30 seconds ends an active round unscored. |
| Room expiry | End after two hours without an authenticated participant request. |

Server time decides deadlines. Browser timers are visual estimates. Every screen shows whether this is Live or Fixture mode; never substitute fixtures silently in a live round.

## 4. Complete round flow

### Join and start

The host creates the single room using the deployment's host access code, enters a name, and receives a short join code and copyable link. Guests join with a name. An opaque browser session identifies each player; a name alone cannot reclaim an identity.

Show the roster, a concise rule card, topic selector, and Start. The host checks that everyone is present; there is no separate ready action. Start checks the 3–4-player limit, presence within the last 30 seconds, selected mode, configured live capacity, and remaining generation allowance before freezing the roster and topic. Only demonstrate a live size after rehearsing it. Reject a second room and over-capacity joins/starts on the server, including simultaneous requests. To replace departed players or change host, end the room and create a new one.

Initial topics:

- The worst possible first day at a new job.
- A hotel with one very unusual rule.
- The world's least useful superhero.
- A restaurant that takes its name too literally.
- A completely unnecessary invention.
- An unexpected guest at a royal banquet.

### Prompting

Show the topic, countdown, draft field, length limit, and Submit. The tip is: “Describe one scene: who is there, where they are, and what happens.”

For the first-day topic, an example is: “A nervous astronaut arrives at an office on the moon and discovers every desk is occupied by a dancing penguin.” This is illustrative input, not a promised model output.

Only the author can retrieve their draft/accepted prompt. Show aggregate submission progress to everyone else. Validate before acceptance, reject rather than truncate, and lock the first accepted submission. A retry of the same accepted text returns its existing confirmation; different text is rejected. Keep unsent drafts in browser session storage for refreshes and clear them after the round.

Close when all frozen players submit or 60 seconds expires. A missing submission creates no clip and no provider request. Disconnected guests remain on the roster; deadlines continue.

### Generating

Generate one candidate per accepted prompt after prompting closes. Preserve the text within one fixed rendering template. Use identical model settings and one round seed policy; no prompt rewriting, alternate model, or player-requested reroll.

Allow one automatic retry for a confirmed transient failure, using the same inputs and settings. Reuse an existing recording if only download/preparation failed; otherwise allow one replacement generation after the previous session is confirmed ended or not created. Wait briefly, and retry only within the original 180-second deadline and call allowance. Rejections, invalid input, and uncertain session status do not trigger a retry. A second failure, or insufficient time to retry, makes the entry unavailable. Publish at most one clip per player.

Show aggregate Queued, Generating, Retrying, and Preparing states and elapsed time. Hide clips, authors, and other players' prompts. Close once all entries finish, including eligible retries, or at 180 seconds. Freeze only completed, playable clips; failed and late entries remain unavailable. With zero clips, show no result; with one, offer an unscored showcase; with two or more, screen them for voting.

### Screening

Shuffle the completed entries once and assign neutral labels, such as Clip 1. Reveal the current and previously screened clips; future clips remain inaccessible. Phones poll for the same current clip, but players tap Play themselves. Frame-perfect playback synchronization is unnecessary.

The host controls Next and Skip clip. Next confirms that the group has watched the clip. Skip excludes an unplayable or unsuitable clip with a public reason before voting; it does not regenerate it. No separate reporting queue or automated output-review service is required for this supervised demo. Provider input moderation is not a guarantee about every generated frame.

The host can project the normal screen during screening/results. A separate spectator identity or paired-display route is deferred. Keep private prompt entry and voting off the projected screen, and keep the host's game tab foreground during play so polling continues.

After the last remaining clip, freeze the ballot and open voting. If fewer than two clips remain, finish unscored. If the host does not finish screening within 180 seconds, finish unscored with “Screening was not completed.”

### Voting

Every player on the frozen roster can vote once for another player's eligible clip or choose Abstain. Players who missed submission or whose generation failed can still vote. A local selection is editable until Vote is accepted; then the ballot locks. Reject self-votes, changed ballots, excluded targets, and late requests on the server.

Show all eligible clips and the topic for replay. Mark the author's own entry as unavailable only in their private view. Keep totals, other ballots, authors, and prompts hidden. Close when every player votes/abstains or 30 seconds expires; missing ballots add no votes.

If a serious playback/content problem arises after voting opens, the host can abort the whole round unscored. Do not change candidates after ballots arrive.

### Results and replay

Count votes once on the server. Reveal each eligible entry's author, prompt, and total; keep individual ballots private and excluded/rejected content hidden. Highest positive score wins; equal highest scores produce joint winners. No votes means no winner. Fewer than two eligible clips or an aborted round is unscored.

For four clips, scores of 2, 1, 1, 0 produce one winner; 2, 2, 0, 0 produce joint winners. There is no AI judge or cumulative leaderboard.

Play again clears the finished round's prompts, ballots, and clips and returns the same players to topic selection. End room removes the room and its media. A new round always has a fresh ID and new ballots.

## 5. Failure, privacy, and presentation

| Event | Behavior |
| --- | --- |
| Guest refreshes or briefly disconnects | Restore accepted actions with the same browser session; keep deadlines. |
| Host absent for 30 seconds | Abort the active round, cancel remaining generation, show a reason. Host can return to start again. |
| Confirmed transient provider/capture failure | Retry once when time and allowance permit; otherwise mark unavailable and continue. |
| Moderation rejection, invalid input, or authentication/configuration error | Mark unavailable without a retry or prompt rewrite. |
| Provider session status is uncertain | Stop new live generations until the operator checks session status; fixtures remain available for a new room. |
| Server restarts | Show “Demo restarted — please rejoin.” No room/job recovery or automatic resubmission. |

Keep keys on the server. Authorize snapshots, commands, and media by membership and phase. A room code locates a room; it is not a credential for private clips. Text is rendered as text, not HTML. Explain before play that scene prompts go to Reactor and generated files are temporarily stored.

Delete app-owned round media on replay/end/expiry and clear orphaned files at startup. The operator purges the demo directory after the event, within 24 hours; this is a demo runbook obligation, not a monitored retention service. Provider retention is separate. Downloaded media cannot be recalled.

Provide responsive phone layouts, keyboard controls, visible focus, labelled inputs, readable contrast, and status text that does not rely on color. Require a tap for video playback when necessary. Contest clips are silent. Optional VEED host clips have matching visible text and can be skipped without delaying play.

Keep Quiplash / Jackbox Games in About/Credits as inspiration, Reactor as the scene provider when used, and VEED Fabric for any host assets used. Generic host media contains no player names, prompts, or ballots.

## 6. Demo acceptance

| Check | Required outcome |
| --- | --- |
| Full round | Three browsers complete join → prompt → generate → screen → vote → results, then Play again. |
| Four-player cap | Four can play after live validation; a fifth join and forged larger roster fail in both modes. |
| Voting | Self/duplicate/changed/late votes are rejected; ties, abstention, and zero-vote outcomes are correct. |
| Privacy | No other player's prompt/author or unrevealed clip can be fetched early; individual ballots never become public. |
| Timing/failure | Partial generation failure, late completion, screening timeout, and host absence yield a clear outcome. |
| Simple retry | A transient failure can recover once with unchanged inputs; no third creation attempt, deadline extension, or retry of rejected/unknown sessions. Reuse saved media for a preparation retry. |
| Refresh/restart | Browser refresh restores state; process restart clears it and never restarts a paid request. |
| Live media | A real five-second Reactor clip plays on phone Safari and Chrome; owned sessions terminate. |
| Rehearsal | Complete a three-player and a four-player live round within the generation deadline; record time, failures, and cost. Recheck after a material integration change. |
| Fallback/presenter | Fixture mode stays visibly labelled; missing VEED assets do not block the round. |

These are planned checks, not completed test results.
