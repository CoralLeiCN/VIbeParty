import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { apiPost, ApiError } from "../../shared/api";
import { copyText } from "../../shared/clipboard";
import {
  RoomCodeInput,
  normalizeRoomCode,
  ROOM_CODE_FORMAT_MESSAGE,
} from "../../shared/RoomCodeInput";
import type { GameEntryProps } from "../../shared/contracts";
import { usePolling } from "../../shared/usePolling";
import type { Media, Snapshot } from "./types";
import s from "./reverse.module.css";
const API = "/api/games/reverse-prompt";
const labels: Record<string, string> = {
  lobby: "Gather your three",
  author_input: "The original idea",
  generating: "Making the next scene",
  relay_input: "Pass the idea along",
  guessing: "Where did it begin?",
  scoring: "Comparing guesses",
  reveal: "The whole story",
  error: "This round has stopped",
  cleanup: "Finishing the round",
};
function uuid() {
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 15) | 64;
  b[8] = (b[8] & 63) | 128;
  return Array.from(
    b,
    (v, i) =>
      ([4, 6, 8, 10].includes(i) ? "-" : "") + v.toString(16).padStart(2, "0"),
  ).join("");
}
function Clip({ media, label }: { media: Media; label: string }) {
  return (
    <figure className={s.clip}>
      <video
        src={media.url}
        controls
        playsInline
        muted
        preload="metadata"
        aria-label={label}
      />
      <figcaption>{label} · 5 seconds · tap to play or replay</figcaption>
    </figure>
  );
}
function useRelaySeconds(remaining: number | null) {
  const [clock, setClock] = useState({
    remaining,
    seconds: Math.ceil((remaining ?? 0) / 1000),
  });
  useEffect(() => {
    if (remaining === null) return;
    const deadline = performance.now() + remaining;
    const timer = window.setInterval(() => {
      setClock({
        remaining,
        seconds: Math.max(0, Math.ceil((deadline - performance.now()) / 1000)),
      });
    }, 100);
    return () => window.clearInterval(timer);
  }, [remaining]);
  return remaining === null
    ? null
    : clock.remaining === remaining
      ? clock.seconds
      : Math.ceil(remaining / 1000);
}
function Input({
  state,
  refresh,
  expired,
}: {
  state: Snapshot;
  refresh: () => void;
  expired: boolean;
}) {
  const [text, setText] = useState(state.scripted_text ?? "");
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const pending = useRef<{ text: string; id: string } | null>(null);
  const guessing = state.phase === "guessing";
  const accepted = guessing ? state.own.guess : state.own.prompt;
  const count = [...text].length;
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (status === "submitting" || accepted || expired) return;
    const normalized = text.normalize("NFC").trim();
    if (!pending.current || pending.current.text !== normalized)
      pending.current = { text: normalized, id: uuid() };
    setStatus("submitting");
    setError("");
    try {
      await apiPost(API + "/submit", {
        round_id: state.round_id,
        phase: state.phase,
        step: state.step,
        submission_id: pending.current.id,
        text,
      });
      setStatus("accepted");
      refresh();
    } catch (reason) {
      setStatus("idle");
      setError(
        reason instanceof Error
          ? reason.message
          : "Could not submit. Try again.",
      );
      if (reason instanceof ApiError && reason.status === 422)
        pending.current = null;
      refresh();
    }
  }
  if (accepted || status === "accepted")
    return (
      <p className={s.accepted} role="status">
        ✓ Accepted.{" "}
        {guessing ? "Waiting for both guesses." : "Your scene is on its way."}
      </p>
    );
  return (
    <form onSubmit={submit} className={s.input}>
      <label htmlFor="scene-text">
        {guessing
          ? "Your final guess of the original scene"
          : state.role === "A"
            ? "Write the scene that starts it all"
            : "Describe only what you see"}
      </label>
      <p>
        {guessing
          ? "Both interpreters submit a separate guess. Take your time."
          : state.phase === "relay_input"
            ? "Watch your private clue and send your description before the 30-second turn ends."
            : "One clear English scene. Your accepted words are final. Take your time."}
      </p>
      <textarea
        id="scene-text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={4}
        readOnly={state.mode === "rehearsal"}
        disabled={status === "submitting" || expired}
        aria-describedby="text-count"
        placeholder="A tiny astronaut pours tea for a giant frog…"
      />
      <div className={s.meta} id="text-count">
        <span>{count} / 300 characters</span>
        <span>Up to {state.token_limit} model tokens</span>
      </div>
      {state.mode === "rehearsal" && (
        <p className={s.note}>
          Scripted rehearsal: submit this supplied example to continue.
        </p>
      )}
      {guessing &&
        state.role === "C" &&
        state.own.prompt &&
        state.mode === "live" && (
          <button
            type="button"
            className={s.secondary}
            onClick={() => setText(state.own.prompt ?? "")}
          >
            Copy my interpretation
          </button>
        )}
      {error && (
        <p className={s.error} role="alert">
          {error}
        </p>
      )}
      <button
        disabled={
          status === "submitting" || expired || !text.trim() || count > 300
        }
      >
        {status === "submitting"
          ? "Submitting…"
          : guessing
            ? "Lock my final guess"
            : "Send this scene"}
      </button>
    </form>
  );
}
function Entry({ entry, refresh }: GameEntryProps & { refresh: () => void }) {
  const [params] = useSearchParams();
  const [name, setName] = useState("");
  const [code, setCode] = useState(params.get("code") ?? "");
  const [organizer, setOrganizer] = useState("");
  const [mode, setMode] = useState("rehearsal");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    const joinCode = entry === "join" ? normalizeRoomCode(code) : null;
    if (entry === "join" && joinCode === null) {
      setError(ROOM_CODE_FORMAT_MESSAGE);
      return;
    }
    if (!name.trim()) {
      setError("Enter your name.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await apiPost(
        API + (entry === "host" ? "/room" : "/join"),
        entry === "host"
          ? { name, organizer_code: organizer, mode }
          : { name, code: joinCode },
      );
      refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className={s.card}>
      <p className={s.eyebrow}>THREE PEOPLE · ONE CHANGING IDEA</p>
      <h2>{entry === "host" ? "Start a private relay" : "Join the relay"}</h2>
      <p>
        The host writes a scene. Two friends pass it through videos, then guess
        where it started.
      </p>
      <form onSubmit={submit} className={s.entry} noValidate={entry === "join"}>
        <label htmlFor="player-name">Your name</label>
        <input
          id="player-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={48}
          required
          autoComplete="nickname"
        />
        {entry === "host" ? (
          <>
            <label htmlFor="organizer-code">Organizer code</label>
            <input
              id="organizer-code"
              type="password"
              value={organizer}
              onChange={(e) => setOrganizer(e.target.value)}
              required
              autoComplete="off"
            />
            <label htmlFor="game-mode">Play mode</label>
            <select
              id="game-mode"
              value={mode}
              onChange={(e) => setMode(e.target.value)}
            >
              <option value="rehearsal">
                Scripted rehearsal · sample clips & scores
              </option>
              <option value="live">
                Live · MiniMax FastH3 & local scoring
              </option>
            </select>
            <p className={s.note}>
              MiniMax FastH3 generates your videos through Reactor. Final
              guesses are compared locally. Live play requires the operator’s
              allocated trial slot.
            </p>
          </>
        ) : (
          <>
            <label htmlFor="room-code">Room code</label>
            <RoomCodeInput
              id="room-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
            />
          </>
        )}
        {error && (
          <p className={s.error} role="alert">
            {error}
          </p>
        )}
        <button disabled={busy}>
          {busy
            ? "Joining…"
            : entry === "host"
              ? "Create party as author A"
              : "Join party"}
        </button>
      </form>
    </section>
  );
}
function RoundView({
  state,
  refresh,
}: {
  state: Snapshot;
  refresh: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [copied, setCopied] = useState(false);
  const relaySeconds = useRelaySeconds(state.relay_remaining_ms);
  const active = "ABC"[state.step];
  const who = state.players.find((p) => p.role === active)?.name;
  const input =
    (["author_input", "relay_input"].includes(state.phase) &&
      state.role === active) ||
    (state.phase === "guessing" && state.role !== "A");
  async function command(action: string) {
    setBusy(true);
    setError("");
    try {
      await apiPost(API + "/" + action, { round_id: state.round_id });
      refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Please try again.");
      refresh();
    } finally {
      setBusy(false);
      setConfirm(false);
    }
  }
  async function copy() {
    const success = await copyText(state.join_url);
    setCopied(success);
    setError(success ? "" : "Select and copy the join address shown below.");
  }
  return (
    <>
      <div className={s.party}>
        <span>
          ROOM <strong>{state.code}</strong>
        </span>
        <span>
          You are <strong>{state.role}</strong> ·{" "}
          {state.role === "A" ? "Author & host" : "Interpreter"}
        </span>
      </div>
      <ol className={s.roster}>
        {["A", "B", "C"].map((role) => (
          <li key={role} className={role === state.role ? s.you : ""}>
            <span className={s.role}>{role}</span>
            <span>
              {state.players.find((p) => p.role === role)?.name ??
                "Waiting for a friend"}
              <small>
                {role === "A"
                  ? "Original author · unscored"
                  : `Interpreter ${role}`}
              </small>
            </span>
          </li>
        ))}
      </ol>
      <section className={s.card}>
        <p className={s.eyebrow}>
          {state.mode === "rehearsal" ? "SCRIPTED REHEARSAL" : "LIVE ROUND"} ·
          REVERSE PROMPT
        </p>
        <h2>{labels[state.phase] ?? "The relay"}</h2>
        {state.phase === "lobby" && (
          <>
            <p>
              A writes the original. B and C each see one private clue. Everyone
              watches the final video, then B and C guess the original.
            </p>
            <p>
              B and C each have 30 seconds to watch and describe their private
              clue. The original scene and final guesses have no countdown.
            </p>
            <div className={s.join}>
              <strong>{state.players.length} / 3 players</strong>
              <button className={s.secondary} onClick={copy}>
                {copied ? "Copied" : "Copy join link"}
              </button>
              <a href={state.join_url}>{state.join_url}</a>
            </div>
            <p className={s.note}>
              MiniMax FastH3 makes each live scene through Reactor. Final
              guesses stay on the laptop for local comparison.
            </p>
            {state.start_blocked && (
              <p className={s.error} role="status">
                {state.start_blocked}
              </p>
            )}
            {state.role === "A" ? (
              <button
                disabled={!state.can_start || busy}
                onClick={() => command("start")}
              >
                {busy ? "Starting…" : "Start round"}
              </button>
            ) : (
              <p className={s.wait}>Waiting for the host to start.</p>
            )}
          </>
        )}
        {state.media.length === 1 && (
          <Clip
            key={state.media[0].id}
            media={state.media[0]}
            label={
              state.phase === "relay_input"
                ? "Your private clue"
                : "The final scene"
            }
          />
        )}
        {state.phase === "relay_input" && relaySeconds !== null && (
          <div
            className={s.timer}
            role="timer"
            aria-label="Relay time remaining"
          >
            <strong>{relaySeconds}s</strong>
            <span>
              {relaySeconds > 0
                ? `${active}’s turn · watch and describe`
                : "Time is up · waiting for the host laptop"}
            </span>
          </div>
        )}
        {input && (
          <Input
            key={`${state.round_id}:${state.phase}:${state.step}`}
            state={state}
            refresh={refresh}
            expired={state.phase === "relay_input" && relaySeconds === 0}
          />
        )}
        {["author_input", "relay_input"].includes(state.phase) && !input && (
          <p className={s.wait}>
            Waiting for {who} ({active}) to{" "}
            {active === "A"
              ? "write the first scene"
              : "describe their private video"}
            .
          </p>
        )}
        {state.phase === "generating" && (
          <div className={s.wait} role="status">
            {who}’s scene is accepted. Making video {state.step + 1} of 3…
            <small>{state.generation_elapsed ?? 0} seconds elapsed</small>
          </div>
        )}
        {["guessing", "scoring"].includes(state.phase) && (
          <>
            <p className={s.note}>
              {state.guess_count} / 2 final guesses accepted. Guesses stay
              private until both are submitted.
            </p>
            {state.role === "A" && (
              <p className={s.author}>Author — unscored</p>
            )}
          </>
        )}
        {state.phase === "scoring" && (
          <p className={s.wait} role="status">
            Comparing both guesses with the original scene…
          </p>
        )}
        {state.phase === "error" && (
          <p className={s.error} role="alert">
            {state.error}
          </p>
        )}
        {state.phase === "cleanup" && (
          <p className={s.wait} role="status">
            {state.cleanup_pending
              ? "The previous video session needs operator closure verification. New work is blocked."
              : "Stopping active work and clearing the previous round…"}
          </p>
        )}
        {state.phase === "reveal" && (
          <>
            <div className={s.original}>
              <p className={s.eyebrow}>THE ORIGINAL SCENE</p>
              <blockquote>{state.chain?.[0].prompt}</blockquote>
            </div>
            <h3>
              {state.unscored
                ? "Completed, unscored"
                : state.results?.filter((r) => r.winner).length === 2
                  ? "A shared win!"
                  : `${state.results?.find((r) => r.winner)?.player} kept the idea closest`}
            </h3>
            <p className={s.note}>
              {state.mode === "rehearsal"
                ? "Sample scores for this scripted rehearsal."
                : state.unscored
                  ? "The local comparison could not finish. No scores or ranking were assigned."
                  : "Meaning is compared; details may be missed. These are casual similarity scores."}{" "}
              The author is unscored.
            </p>
            <div className={s.results}>
              {state.results?.map((row) => (
                <article key={row.role}>
                  <strong>
                    {row.player} · {row.role}
                  </strong>
                  <p>{row.guess}</p>
                  <span className={s.score}>
                    {row.points === null
                      ? "Unscored"
                      : `Similarity: ${row.points} / 100`}
                  </span>
                  {row.winner && (
                    <small>
                      {state.mode === "rehearsal" ? "Sample winner" : "Winner"}
                    </small>
                  )}
                </article>
              ))}
            </div>
            <h3>Follow the idea through all three scenes</h3>
            <ol className={s.chain}>
              {state.chain?.map((row, i) => (
                <li key={row.role}>
                  <p className={s.eyebrow}>
                    0{i + 1} · {row.player} · {row.role}
                  </p>
                  <p>{row.prompt}</p>
                  <Clip
                    media={row.media}
                    label={`Scene ${i + 1} by ${row.player}`}
                  />
                </li>
              ))}
            </ol>
          </>
        )}
        {error && (
          <p className={s.error} role="alert">
            {error}
          </p>
        )}
      </section>
      {state.role === "A" && !["lobby", "cleanup"].includes(state.phase) && (
        <div className={s.reset}>
          {confirm ? (
            <>
              <p>
                Stop this round and clear its scenes? Everyone keeps their role.
              </p>
              <button disabled={busy} onClick={() => command("reset")}>
                Confirm reset to lobby
              </button>
              <button className={s.secondary} onClick={() => setConfirm(false)}>
                Keep playing
              </button>
            </>
          ) : (
            <button className={s.secondary} onClick={() => setConfirm(true)}>
              {state.phase === "reveal"
                ? "Another round · return to lobby"
                : "Stop & reset round"}
            </button>
          )}
        </div>
      )}
    </>
  );
}
export function GameRoute({ entry }: GameEntryProps) {
  const poll = usePolling<Snapshot>(API + "/state");
  const latest = useRef<Snapshot | undefined>(undefined);
  const expired = poll.error instanceof ApiError && poll.error.status === 401;
  if (expired) latest.current = undefined;
  else if (
    poll.data &&
    (latest.current?.room_id !== poll.data.room_id ||
      poll.data.revision >= latest.current.revision)
  )
    latest.current = poll.data;
  const state = latest.current;
  return (
    <main id="main-content" className={s.page}>
      <header className={s.header}>
        <Link to="/">← Back to games</Link>
        <span>VIBEPARTY</span>
      </header>
      <div className={s.title}>
        <div>
          <p className={s.eyebrow}>A VIDEO TELEPHONE GAME</p>
          <h1>
            Reverse
            <br />
            <em>Prompt.</em>
          </h1>
        </div>
        <p>
          Watch it.
          <br />
          Describe it.
          <br />
          <strong>Trace it back.</strong>
        </p>
      </div>
      {state?.mode === "rehearsal" && (
        <div className={s.banner}>
          SCRIPTED REHEARSAL · fixed sample clips and scores · no live
          generation
        </div>
      )}
      {poll.error && !expired && (
        <div className={s.error} role="alert">
          Reconnecting… Waiting for the laptop.{" "}
          <button className={s.secondary} onClick={poll.retry}>
            Retry connection
          </button>
        </div>
      )}
      {expired &&
        poll.error instanceof ApiError &&
        poll.error.code === "session_expired" && (
          <p className={s.error} role="status">
            This party has ended. Create or join a new party with your host.
          </p>
        )}
      {!state && poll.loading ? (
        <p role="status">Finding your party…</p>
      ) : state ? (
        <RoundView key={state.round_id} state={state} refresh={poll.retry} />
      ) : (
        <Entry entry={entry} refresh={poll.retry} />
      )}
      <footer className={s.footer}>
        Inspired by Telephone. Three people, three scenes, one unexpected
        journey.
      </footer>
    </main>
  );
}
