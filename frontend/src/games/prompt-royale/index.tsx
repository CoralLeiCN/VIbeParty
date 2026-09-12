import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError, apiFetch, apiPost } from "../../shared/api";
import { copyText } from "../../shared/clipboard";
import {
  RoomCodeInput,
  normalizeRoomCode,
  ROOM_CODE_FORMAT_MESSAGE,
} from "../../shared/RoomCodeInput";
import type { GameEntryProps } from "../../shared/contracts";
import { usePolling } from "../../shared/usePolling";
import { Arena } from "./Arena";
import type { Snapshot } from "./types";
import styles from "./Royale.module.css";

const API = "/api/games/prompt-royale";
const playerCounts = [1, 2, 3, 4];
const phases: Record<string, string> = {
  lobby: "Gather the directors",
  prompting: "Your scene. Your secret.",
  generating: "From words to motion",
  screening: "Four corners. One favorite.",
  voting: "Make your choice",
  results: "The room has spoken",
};

export function GameRoute({ entry }: GameEntryProps) {
  const [params] = useSearchParams();
  const poll = usePolling<Snapshot>(API + "/room");
  const [state, setState] = useState<Snapshot>();
  const latest = useRef<Snapshot | undefined>(undefined);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [passcode, setPasscode] = useState("");
  const [playerCount, setPlayerCount] = useState(3);
  const [code, setCode] = useState(params.get("code") || "");
  const [draft, setDraft] = useState("");
  const [seconds, setSeconds] = useState(0);
  const [copied, setCopied] = useState(false);

  function accept(next: Snapshot) {
    const old = latest.current;
    if (
      old?.boot_id === next.boot_id &&
      (next.revision < old.revision ||
        (next.revision === old.revision && next.server_time < old.server_time))
    )
      return;
    latest.current = next;
    setState(next);
  }
  useEffect(() => {
    if (poll.data) accept(poll.data);
  }, [poll.data]);
  useEffect(() => {
    if (poll.error instanceof ApiError && poll.error.status === 401) {
      setState(undefined);
      latest.current = undefined;
      Object.keys(sessionStorage)
        .filter((key) => key.startsWith("pr-draft:"))
        .forEach((key) => sessionStorage.removeItem(key));
    }
  }, [poll.error]);
  useEffect(() => {
    if (!state) return;
    const deadline = Date.now() + state.seconds_left * 1000;
    const tick = () =>
      setSeconds(Math.max(0, Math.ceil((deadline - Date.now()) / 1000)));
    tick();
    const timer = setInterval(tick, 200);
    return () => clearInterval(timer);
  }, [state]);
  const draftKey = state?.round_id
    ? `pr-draft:${state.boot_id}:${state.room_id}:${state.round_id}`
    : "";
  useEffect(() => {
    if (draftKey && state?.phase === "prompting")
      setDraft(sessionStorage.getItem(draftKey) || "");
    else if (state?.phase) {
      Object.keys(sessionStorage)
        .filter((key) => key.startsWith("pr-draft:"))
        .forEach((key) => sessionStorage.removeItem(key));
      setDraft("");
    }
  }, [draftKey, state?.phase]);

  async function act(path: string, data: object = {}) {
    if (!state || busy) return;
    setBusy(true);
    setError("");
    const privateAction =
      path === "/round/submission" || path === "/round/vote";
    const payload = {
      round_id: state.round_id,
      ...(!privateAction
        ? {
            command_id: Array.from(
              crypto.getRandomValues(new Uint8Array(16)),
              (n) => n.toString(16).padStart(2, "0"),
            ).join(""),
            expected_version: state.version,
          }
        : {}),
      ...data,
    };
    try {
      accept(await apiPost<Snapshot>(API + path, payload));
      poll.retry();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Please try again.");
      poll.retry();
    } finally {
      setBusy(false);
    }
  }

  async function enter() {
    const normalizedCode = normalizeRoomCode(code);
    if (entry === "join" && normalizedCode === null) {
      setError(ROOM_CODE_FORMAT_MESSAGE);
      return;
    }
    setBusy(true);
    setError("");
    try {
      accept(
        await apiPost<Snapshot>(
          API + (entry === "host" ? "/room" : "/room/join"),
          entry === "host"
            ? { name, passcode, player_count: playerCount }
            : { name, code: normalizedCode },
        ),
      );
      setPasscode("");
      poll.retry();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function close() {
    setBusy(true);
    setError("");
    try {
      const result = await apiFetch<{ status: string; message: string }>(
        API + "/room",
        { method: "DELETE", body: "{}" },
      );
      if (result.status === "closed") {
        setState(undefined);
        latest.current = undefined;
        poll.retry();
      } else setError(result.message);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  }

  const lobby = state?.lobby;
  return (
    <main className={`${styles.page} ${state?.arena ? styles.arenaPage : ""}`}>
      <header className={styles.header}>
        <Link to="/">← Back to games</Link>
        <span>VIBEPARTY / 02</span>
      </header>
      <div className={styles.masthead}>
        <div>
          <span className={styles.eyebrow}>THE PROMPT + VIDEO PARTY GAME</span>
          <h1>
            Prompt <em>Royale</em>
            <span className={styles.star}>✳</span>
          </h1>
        </div>
        <span className={styles.mode}>
          {state
            ? state.mode === "fixture"
              ? "FIXTURE MODE"
              : "LIVE · REACTOR"
            : "1–4 PLAYERS · HOST PLAYS TOO"}
        </span>
      </div>
      {state?.mode === "fixture" && (
        <p className={styles.fixtureNotice}>
          Fixture rehearsal · videos are synthetic samples, not generated from
          your scene. Topic suggestions are{" "}
          {state.topic_source === "fixture"
            ? "simulated fixtures"
            : "live LLM suggestions"}
          .
        </p>
      )}
      {error && (
        <div className={styles.error} role="alert">
          {error}
        </div>
      )}
      {poll.error &&
        !(poll.error instanceof ApiError && poll.error.status === 401) && (
          <div className={styles.error} role="status">
            Reconnecting… Your round’s deadlines continue.{" "}
            <button onClick={poll.retry}>Retry connection</button>
          </div>
        )}
      {!state ? (
        <section className={styles.entry}>
          <div>
            <span className={styles.eyebrow}>ONE TOPIC. EVERYONE DIRECTS.</span>
            <h2>
              Make a scene.
              <br />
              Win the room.
            </h2>
            <p>
              Write in secret. Watch the anonymous arena together. Give your
              favorite another player’s vote.
            </p>
            <div className={styles.steps}>
              <span>01 Write</span>
              <span>02 Watch</span>
              <span>03 Vote</span>
            </div>
          </div>
          <form
            noValidate={entry === "join"}
            className={styles.card}
            onSubmit={(event) => {
              event.preventDefault();
              void enter();
            }}
          >
            <h2>{entry === "host" ? "Host a party" : "Join the directors"}</h2>
            {poll.error instanceof ApiError && poll.error.status === 401 && (
              <p className={styles.hint}>
                New here or demo restarted? Enter below to join the party.
              </p>
            )}
            <label htmlFor="royale-name">Your name</label>
            <input
              id="royale-name"
              autoComplete="nickname"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            {entry === "host" ? (
              <>
                <label htmlFor="royale-passcode">Host access code</label>
                <input
                  id="royale-passcode"
                  type="password"
                  value={passcode}
                  onChange={(e) => setPasscode(e.target.value)}
                  required
                />
                <label htmlFor="royale-player-count">Number of players</label>
                <select
                  id="royale-player-count"
                  value={playerCount}
                  disabled={busy}
                  onChange={(e) => setPlayerCount(Number(e.target.value))}
                  aria-describedby="royale-player-count-hint"
                >
                  {playerCounts.map((count) => (
                    <option key={count} value={count}>
                      {count === 1 ? "1 player · Solo" : `${count} players`}
                    </option>
                  ))}
                </select>
                <p id="royale-player-count-hint" className={styles.hint}>
                  Includes you as host. Solo rounds are unscored showcases.
                </p>
              </>
            ) : (
              <>
                <label htmlFor="royale-code">Room code</label>
                <RoomCodeInput
                  id="royale-code"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  required
                />
              </>
            )}
            <button disabled={busy || poll.loading}>
              {busy
                ? "Joining…"
                : entry === "host"
                  ? "Create party"
                  : "Join party"}
            </button>
            <p className={styles.hint}>
              Live scene prompts go to Reactor. Videos are stored temporarily
              and deleted when the round is cleared.
            </p>
          </form>
        </section>
      ) : (
        <>
          <div className={styles.phaseBar}>
            <div>
              <span className={styles.eyebrow}>{state.phase}</span>
              <h2>{phases[state.phase]}</h2>
            </div>
            <div className={styles.phaseMeta}>
              <span>
                ROOM <strong>{state.code}</strong>
              </span>
              {state.phase !== "lobby" && state.phase !== "results" && (
                <strong className={styles.timer} aria-label="Time remaining">
                  {seconds}s
                </strong>
              )}
            </div>
          </div>
          {(state.closing || state.cleanup_pending) && (
            <p className={styles.error}>
              Finishing provider cleanup. New rounds and switching are blocked
              until closure is confirmed.
            </p>
          )}
          {state.phase === "lobby" && (
            <div className={styles.lobby}>
              <section className={styles.card}>
                <h3>
                  The directors{" "}
                  <span>
                    {state.players.length}/{state.player_count}
                  </span>
                </h3>
                <ul className={styles.roster}>
                  {state.players.map((p) => (
                    <li key={p.id}>
                      <span>
                        {p.name}
                        {p.host ? " · Host" : ""}
                        {p.id === state.me.id ? " · You" : ""}
                      </span>
                      <small>{p.present ? "Here" : "Away"}</small>
                    </li>
                  ))}
                </ul>
                <label htmlFor="join-url">Invite your friends</label>
                <input
                  id="join-url"
                  readOnly
                  value={state.join_url}
                  onFocus={(e) => e.target.select()}
                />
                <button
                  className={styles.secondary}
                  onClick={async () => {
                    try {
                      if (!(await copyText(state.join_url)))
                        throw new Error("Manual copy needed");
                      setCopied(true);
                    } catch {
                      setError(
                        "Select the invite link and copy it. Clipboard access is unavailable on this HTTP browser.",
                      );
                    }
                  }}
                >
                  {copied ? "Link copied ✓" : "Copy link"}
                </button>
                <p>
                  60 seconds to write. Five seconds on screen. Ten seconds to
                  vote.
                </p>
                <p className={styles.hint}>
                  Keep the host’s tab foreground. After 30 seconds away, an
                  active round ends unscored.
                </p>
              </section>
              <section className={styles.card}>
                <h3>Set the scene</h3>
                {state.me.host && lobby ? (
                  <>
                    <label htmlFor="royale-lobby-player-count">
                      Number of players
                    </label>
                    <select
                      id="royale-lobby-player-count"
                      value={state.player_count}
                      disabled={busy || state.closing || state.cleanup_pending}
                      aria-describedby="royale-lobby-player-count-hint"
                      onChange={(e) =>
                        void act("/room/player-count", {
                          player_count: Number(e.target.value),
                        })
                      }
                    >
                      {playerCounts.map((count) => (
                        <option
                          key={count}
                          value={count}
                          disabled={count < state.players.length}
                        >
                          {count === 1 ? "1 player · Solo" : `${count} players`}
                        </option>
                      ))}
                    </select>
                    <p
                      id="royale-lobby-player-count-hint"
                      className={styles.hint}
                    >
                      Includes you as host. Solo rounds are unscored showcases.
                    </p>
                    <div className={styles.tabs}>
                      <button
                        aria-pressed={lobby.mode === "bundled"}
                        className={styles.secondary}
                        disabled={busy}
                        onClick={() =>
                          void act("/room/topic", { mode: "bundled" })
                        }
                      >
                        Host chooses
                      </button>
                      <button
                        aria-pressed={lobby.mode === "llm"}
                        className={styles.secondary}
                        disabled={busy}
                        onClick={() => void act("/room/topic", { mode: "llm" })}
                      >
                        Auto-generated topic
                      </button>
                    </div>
                    {lobby.mode === "bundled" ? (
                      <>
                        <label htmlFor="topic-choice">Choose a topic</label>
                        <select
                          id="topic-choice"
                          value={lobby.topic || ""}
                          disabled={busy}
                          onChange={(e) =>
                            void act("/room/topic", {
                              mode: "bundled",
                              topic: e.target.value,
                            })
                          }
                        >
                          <option value="" disabled>
                            Select a topic…
                          </option>
                          {lobby.topics.map((t) => (
                            <option key={t}>{t}</option>
                          ))}
                        </select>
                      </>
                    ) : (
                      <div className={styles.suggestion}>
                        <span className={styles.eyebrow}>
                          {state.topic_source === "fixture"
                            ? "FIXTURE SUGGESTION · SIMULATED LLM"
                            : "Generated by an LLM"}
                        </span>
                        <p>
                          {lobby.pending
                            ? "Finding a fresh topic…"
                            : lobby.topic ||
                              "Get a suggestion for your next round."}
                        </p>
                        {lobby.error && (
                          <p role="alert" className={styles.error}>
                            {lobby.error}
                          </p>
                        )}
                        <div className={styles.controls}>
                          <button
                            className={styles.secondary}
                            disabled={busy || lobby.pending}
                            onClick={() => void act("/room/topic/generate")}
                          >
                            {lobby.topic
                              ? "Generate another"
                              : "Generate topic"}
                          </button>
                          {lobby.topic && (
                            <button
                              disabled={
                                busy || lobby.pending || lobby.confirmed
                              }
                              onClick={() =>
                                void act("/room/topic/confirm", {
                                  suggestion_id: lobby.suggestion_id,
                                })
                              }
                            >
                              {lobby.confirmed
                                ? "Topic confirmed ✓"
                                : "Confirm topic"}
                            </button>
                          )}
                        </div>
                      </div>
                    )}
                    <button
                      className={styles.start}
                      disabled={
                        busy ||
                        state.closing ||
                        state.cleanup_pending ||
                        state.players.length !== state.player_count ||
                        !lobby.topic ||
                        (lobby.mode === "llm" && !lobby.confirmed)
                      }
                      onClick={() => void act("/room/start")}
                    >
                      Start round ↗
                    </button>
                    <p className={styles.hint}>
                      {state.players.length < state.player_count
                        ? `Waiting for ${state.player_count} players, including you.`
                        : state.player_count === 1
                          ? "Ready for your solo showcase."
                          : "Check that everyone is present before starting."}
                    </p>
                  </>
                ) : (
                  <p>
                    The host is choosing a topic. Your scene stays private until
                    the reveal.
                  </p>
                )}
              </section>
            </div>
          )}
          {state.topic && (
            <div className={styles.topic}>
              <span className={styles.eyebrow}>THE TOPIC</span>
              <h2>{state.topic}</h2>
            </div>
          )}
          {state.phase === "prompting" && (
            <section className={styles.promptSection}>
              <form
                className={styles.card}
                onSubmit={(e) => {
                  e.preventDefault();
                  void act("/round/submission", { prompt: draft });
                }}
              >
                <label htmlFor="scene">Your private scene</label>
                {state.me.prompt ? (
                  <>
                    <p className={styles.accepted}>{state.me.prompt}</p>
                    <strong role="status">Scene locked ✓</strong>
                  </>
                ) : (
                  <>
                    <textarea
                      id="scene"
                      rows={5}
                      value={draft}
                      onChange={(e) => {
                        setDraft(e.target.value);
                        sessionStorage.setItem(draftKey, e.target.value);
                      }}
                      placeholder="A nervous astronaut walks into an office full of dancing penguins…"
                    />
                    <div className={styles.count}>
                      <span>
                        Describe who is there, where they are, and what happens.
                      </span>
                      <span>
                        {Array.from(draft.normalize("NFC").trim()).length}/500
                      </span>
                    </div>
                    <button
                      disabled={
                        busy ||
                        !draft.trim() ||
                        Array.from(draft.normalize("NFC").trim()).length > 500
                      }
                    >
                      Submit scene
                    </button>
                  </>
                )}
                <p>
                  {state.submitted}/{state.players.length} scenes submitted
                </p>
                <small>
                  Keep private prompts off the projected screen. The full scene
                  and topic must fit 500 model tokens.
                </small>
              </form>
            </section>
          )}
          {state.phase === "generating" && (
            <section className={`${styles.card} ${styles.generation}`}>
              <div className={styles.orbit}>✳</div>
              <h3>The scenes are taking shape</h3>
              <div className={styles.progress}>
                {Object.entries(state.progress || {}).map(([label, count]) => (
                  <span key={label}>
                    {count} {label}
                  </span>
                ))}
              </div>
              <p>
                Same settings for every director. One recovery attempt if
                needed.
              </p>
              <p className={styles.hint}>
                Clips and authors stay hidden until the arena opens.
              </p>
            </section>
          )}
          {state.phase === "results" && (
            <div className={styles.result} role="status">
              <h2>
                {state.scored && state.winners?.length
                  ? state.winners.length > 1
                    ? "A shared crown!"
                    : "We have a winner!"
                  : "Unscored / no winner"}
              </h2>
              <p>
                {state.reason ||
                  "The highest score takes the crown. Individual ballots stay private."}
              </p>
            </div>
          )}
          {state.arena && (
            <Arena key={state.round_id} state={state} busy={busy} act={act} />
          )}
          {state.me.host && (
            <footer className={styles.hostFooter}>
              {state.phase === "results" && (
                <button
                  disabled={busy || state.cleanup_pending || state.closing}
                  onClick={() => void act("/round/again")}
                >
                  Play again
                </button>
              )}
              {["prompting", "generating", "screening", "voting"].includes(
                state.phase,
              ) && (
                <button
                  className={styles.quiet}
                  disabled={busy}
                  onClick={() => void act("/round/abort")}
                >
                  Abort round · unscored
                </button>
              )}
              {["lobby", "results"].includes(state.phase) && (
                <>
                  <button
                    className={styles.quiet}
                    disabled={busy}
                    onClick={() => void close()}
                  >
                    End room
                  </button>
                  <small>
                    Clears this party and its media. Everyone will need to
                    rejoin.
                  </small>
                </>
              )}
            </footer>
          )}
        </>
      )}
      <footer className={styles.credits}>
        Inspired by Quiplash from Jackbox Games. Live scenes by Reactor. Human
        votes decide.
      </footer>
    </main>
  );
}
