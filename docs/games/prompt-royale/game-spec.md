# Prompt Royale: hackathon game specification

[All docs](../../README.md) · [Technical stack](tech-stack.md) · [Simplification](simplification.md) · [Research](../../research/prompt-royale/README.md)

Version: 1.5, 12 September 2026. Status: simplified demo design with two topic modes, an arena reveal, 10-second voting, and one bounded retry; no application or live performance has been validated yet.

This is the authoritative scope for the Prompt Royale hackathon demo. The [app specification](../../app-spec.md) defines the wider product boundaries. See the [demo stack](tech-stack.md), [before-and-after decisions](simplification.md), and [partner research](../../research/prompt-royale/README.md).

## 1. Concept and rationale

**One topic. Everyone directs a short scene. The room picks its favorite.**

Three or four friends join in their browsers, privately write scene prompts for the same topic, watch the anonymous generated clips playing together in a 2×2 arena grid, and vote for a favorite. The host plays too and counts toward the four-player maximum.

The creative prompt-and-vote inspiration comes from **Quiplash by Jackbox Games**, which includes open prompts and sentence blanks whose answers compete for other players' votes. Credit goes to Jackbox Games. [Quiplash on Steam](https://store.steampowered.com/app/351510/Quiplash/).

Prompt Royale adapts that idea to generated video. Players write complete scene descriptions; they do not have to fill a literal blank. Everyone judges the same set of clips, and human votes decide the outcome.

## 2. Demo scope

Run the app locally on the host laptop. Players join its HTTP LAN address on the same Wi-Fi or hotspot; the host still occupies a player slot. The laptop needs internet access for Reactor and live topic suggestions. Remote deployment is deferred.

Build one invite-only room, 3–4 players including one fixed playing host, two topic modes (host choice or LLM generation with host confirmation), prompt submission, video generation, screening, voting, results, and Play again. Use one scene model and one video preset. Optional pre-rendered VEED host clips add presentation after the core round works.

No accounts, matchmaking, tournaments, game-switching UI, audience role, paired display, ready checks, QR generator, host transfer, player removal, timer extensions, or player-requested video rerolls are required. One automatic retry for a confirmed transient failure is included. The other VibeParty games remain separate designs, not dependencies of this demo.

### Hackathon limitations and future exploration

**Four active players is a hard maximum in both live and fixture modes, including the playing host.** Start requires at least three. A fifth player gets “Room full — Prompt Royale supports up to 4 players for the hackathon.” Joining during an active round is closed; there is no waiting-list implementation.

The limit reflects current generation capacity and validation time; it is not a claim that Reactor imposes a four-player limit. First rehearse with three players, then four. Only enable the live sizes that have passed rehearsal. [Capacity research](../../research/prompt-royale/README.md#cost-capacity-and-waiting-time).

One server process holds room state in memory. Refreshing a browser recovers its state while that process is alive. A server restart ends the room and loses its results. A host absent for 30 seconds ends an active round unscored; there is no automatic replacement host.

After the hackathon, explore five-to-eight-player groups, simultaneous rooms, persistent state, automatic recovery, shared-display pairing, and richer presentation. Larger groups require new measurements of generation, cost, and screening pace, plus an explicit cap change.

## 3. Defaults

| Item | Demo rule |
| --- | --- |
| Players | 3–4, including the host; one room on the local server. |
| Name | 1–24 Unicode code points after trimming and NFC normalization; suffix duplicate names. |
| Topic | Before starting, choose Host chooses or Auto-generated topic. The host selects from a small bundled list or confirms an LLM-generated suggestion, with an option to generate another. |
| Prompt | 1–500 code points after trimming and NFC normalization; entire rendered model input must also fit the 500-token application limit. |
| Prompting | 60 seconds; close early when everyone submits. No extension. |
| Generation | 180 seconds total, including queueing, capture, and preparation. |
| Retry | One recovery pass per entry for confirmed transient failures; unchanged inputs, original deadline, and at most two creation attempts. |
| Clip | Five-second silent landscape MP4; same preset and capture policy for everyone. |
| Screening | Reveal all eligible clips together in a 2×2 arena grid, playing simultaneously on repeat. The host opens voting after the group has watched; 180 seconds for the entire screening phase. |
| Voting | 10 seconds; close early when everyone votes or abstains. No extension. |
| Host absence | No successful host poll/command for 30 seconds ends an active round unscored. |
| Room expiry | End after two hours without an authenticated participant request. |

Server time decides deadlines. Browser timers are visual estimates. Every screen shows whether this is Live or Fixture mode; never substitute fixtures silently in a live round.

## 4. Complete round flow

### Join and start

The host creates the single room using the configured host access code, enters a name, and receives a short join code and copyable link using the laptop's LAN origin. Guests join with a name. An opaque browser session identifies each player; a name alone cannot reclaim an identity.

Show the roster, a concise rule card, two topic modes, and Start. The host checks that everyone is present; there is no separate ready action. Topic selection happens in the lobby before the round timer starts:

1. **Host chooses:** the host selects a topic from the small bundled list.
2. **Auto-generated topic:** an LLM creates a topic suggestion. Show the host the topic with the label “Generated by an LLM” and the actions “Confirm topic” and “Generate another.” The host can request another suggestion if the group has played that topic before, then confirm the one to use. A generated suggestion cannot start a round until the host confirms it. Generating another suggestion or changing topic mode clears the previous selection/confirmation.

These topic modes are separate from Live/Fixture video mode. If topic generation fails, show an error and let the host try again or choose from the bundled list. Host review handles topics remembered from earlier games; automatic detection of previously played topics is not required.

Start checks the selected topic and, for an LLM suggestion, confirmation of that exact suggestion, as well as the 3–4-player limit, presence within the last 30 seconds, Live/Fixture mode, configured live capacity, and remaining video generation allowance before freezing the roster, topic mode, and topic. Only demonstrate a live size after rehearsing it. Reject a second room and over-capacity joins/starts on the server, including simultaneous requests. To replace departed players or change host, end the room and create a new one.

Initial topics for Host chooses:

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

### Screening: arena reveal

Reveal every completed eligible clip together in a **2×2 arena grid**. Shuffle entries into positions once on the server and assign neutral labels, Clip 1 through Clip 4. Every browser uses the same labels and positions throughout screening, voting, and results. Authors and prompts stay hidden until results.

| Clip 1 | Clip 2 |
| --- | --- |
| Clip 3 | Clip 4 |

All four five-second silent videos play **at the same time** and repeat together so players can compare them. Show the topic above the arena. Load the eligible videos before playback, then provide one “Play arena” action to start all videos on that screen together, plus Pause all and Replay all. Keep all four tiles visible on phones and the projected screen. Playback is coordinated within each screen; browsers can start after their own tap, without requiring frame-perfect synchronization across devices.

With three eligible clips, leave the fourth tile empty with “No entry”; with two, show two clips and two empty tiles. Empty tiles are not candidates. If a clip cannot load or play, show the affected tile's status and allow playback retry within the screening deadline. The host can use **Exclude clip** on any tile before voting, with a public reason; replace it with a neutral excluded placeholder and keep other positions fixed. Exclusion does not regenerate a clip. No separate reporting queue or automated output-review service is required for this supervised demo. Provider input moderation is not a guarantee about every generated frame.

The host can project the normal arena during screening/results. A separate spectator identity or paired-display route is deferred. Keep private prompt entry and voting off the projected screen, and keep the host's game tab foreground during play so polling continues.

The host selects **Open voting** to confirm that the group has watched at least one full playback of every remaining clip. Freeze the ballot and begin the 10-second vote, keeping the arena visible. If fewer than two clips remain, finish unscored. If the host does not open voting within the original 180-second screening deadline, finish unscored with “Arena screening was not completed.” Loading, replays, and exclusions do not extend that deadline.

### Voting

Every player on the frozen roster can vote once for another player's eligible clip or choose Abstain. Players who missed submission or whose generation failed can still vote. A local selection is editable until Vote is accepted; then the ballot locks. Reject self-votes, changed ballots, excluded targets, and late requests on the server.

Keep the same arena grid, labels, positions, and topic visible, with simultaneous playback and Pause all/Replay all available. Players select a tile and press Vote, or choose Abstain. Mark the author's own entry as unavailable only in their private view; empty and excluded tiles cannot be selected. Keep totals, other ballots, authors, and prompts hidden. Close when every player votes/abstains or 10 seconds expires; missing ballots add no votes.

If a serious playback/content problem arises after voting opens, the host can abort the whole round unscored. Do not change candidates after ballots arrive.

### Results and replay

Count votes once on the server. Keep the arena positions and reveal each eligible entry's author, prompt, and total alongside its tile; highlight all winning tiles. Keep individual ballots private and excluded/rejected content hidden. Highest positive score wins; equal highest scores produce joint winners. No votes means no winner. Fewer than two eligible clips or an aborted round is unscored.

For four clips, scores of 2, 1, 1, 0 produce one winner; 2, 2, 0, 0 produce joint winners. There is no AI judge or cumulative leaderboard.

Play again clears the finished round's prompts, ballots, clips, and topic selection/confirmation and returns the same players to the two topic modes. Any new LLM suggestion requires fresh host confirmation. End room removes the room and its media. A new round always has a fresh ID and new ballots.

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
| Topic modes | The host can select a bundled topic or request an LLM suggestion labelled “Generated by an LLM.” Generated topics require host confirmation; Generate another clears it, stale confirmations cannot start a round, and replay requires a fresh selection. A failed suggestion leaves retry and host choice available. |
| Four-player cap | Four can play after live validation; a fifth join and forged larger roster fail in both modes. |
| Arena reveal | All eligible clips become accessible together at screening and play simultaneously in a 2×2 grid. Labels/positions match across players and stay fixed through results. Three/two clips leave empty tiles; exclusions show placeholders. Play arena, Pause all, and Replay all work on phones and projection, including after refresh. The host opens voting after the group watches every remaining clip. |
| Voting | Voting closes after 10 seconds or earlier when everyone votes/abstains. Self/duplicate/changed/late votes are rejected; ties, abstention, and zero-vote outcomes are correct. |
| Privacy | No other player's prompt/author can be fetched before results, and no contest clip can be fetched before arena screening; individual ballots never become public. |
| Timing/failure | Partial generation failure, late completion, screening timeout, and host absence yield a clear outcome. |
| Simple retry | A transient failure can recover once with unchanged inputs; no third creation attempt, deadline extension, or retry of rejected/unknown sessions. Reuse saved media for a preparation retry. |
| Refresh/restart | Browser refresh restores state; process restart clears it and never restarts a paid request. |
| Live media | Four real five-second Reactor clips play together in the arena on phone Safari and Chrome and the projected host screen; playback loading/failure controls work, and owned sessions terminate. |
| Rehearsal | Complete a three-player and a four-player live round within the generation deadline; record time, failures, and cost. Recheck after a material integration change. |
| Fallback/presenter | Fixture mode stays visibly labelled; missing VEED assets do not block the round. |

These are planned checks, not completed test results.
