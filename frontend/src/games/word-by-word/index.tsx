import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError, apiPost } from "../../shared/api";
import { copyText } from "../../shared/clipboard";
import {
  RoomCodeInput,
  normalizeRoomCode,
  ROOM_CODE_FORMAT_MESSAGE,
} from "../../shared/RoomCodeInput";
import type { GameEntryProps } from "../../shared/contracts";
import { usePolling } from "../../shared/usePolling";
import "./word-by-word.css";

const API = "/api/games/word-by-word";
type Card = {
  index: number;
  category: string;
  text: string;
  contributor: string;
};
type Assignment = {
  index: number;
  category: string;
  question: string;
  example: string;
  accepted_text: string | null;
  fixture_text: string | null;
};
type Clip = { index: number; url: string; duration: number };
type Snapshot = {
  role: "host" | "player";
  code: string;
  round_id: string;
  revision: number;
  phase: "LOBBY" | "INPUT" | "GENERATING" | "REVEAL" | "RESULTS";
  mode: "fixture" | "live";
  players: string[];
  join_url: string;
  server_time: number;
  input_deadline: number | null;
  generation_deadline: number | null;
  collected: number;
  saved_clips: number;
  disclosed_index: number;
  cards: Card[];
  assignments?: Assignment[];
  your_name?: string;
  clips?: Clip[];
  result: string | null;
  message: string;
  provider_closing: boolean;
  closing: boolean;
  busy: boolean;
  live_attempts_left: number;
  live_unavailable_reason: string | null;
};
type Action = (
  suffix: string,
  fields?: Record<string, unknown>,
) => Promise<boolean>;

const phaseLabels = {
  LOBBY: "Gather your people",
  INPUT: "A little secret",
  GENERATING: "Preparing your story",
  REVEAL: "One idea at a time",
  RESULTS: "Made together",
};

export function GameRoute({ entry }: GameEntryProps) {
  const { data, error, loading, retry } = usePolling<Snapshot>(`${API}/state`);
  const [actionError, setActionError] = useState("");
  const [pending, setPending] = useState(false);
  const actionLock = useRef(false);
  const expired =
    error instanceof ApiError && (error.status === 401 || error.status === 404);
  const state = expired ? undefined : data;
  const act: Action = async (suffix, fields = {}) => {
    if (actionLock.current) return false;
    actionLock.current = true;
    setPending(true);
    setActionError("");
    try {
      await apiPost(`${API}${suffix}`, {
        ...(state ? { round_id: state.round_id } : {}),
        ...fields,
      });
      retry();
      return true;
    } catch (failure) {
      setActionError(
        failure instanceof Error
          ? failure.message
          : "Could not complete that action.",
      );
      retry();
      return false;
    } finally {
      actionLock.current = false;
      setPending(false);
    }
  };
  return (
    <main className="wbw">
      <header className="wbw-header">
        <Link to="/" className="wbw-brand">
          VibeParty<span> / Word by Word</span>
        </Link>
        <Link to="/">← Back to games</Link>
      </header>
      <div className="wbw-title">
        <div>
          <p className="wbw-eyebrow">FOUR IDEAS. ONE SHARED STORY.</p>
          <h1>
            Word by <em>Word.</em>
          </h1>
        </div>
        <span className="wbw-mark" aria-hidden="true">
          ✳
        </span>
      </div>
      {actionError && (
        <p className="wbw-error" role="alert">
          {actionError}
        </p>
      )}
      {error && !expired && (
        <p className="wbw-notice" role="status">
          Reconnecting… Your round keeps its deadline.{" "}
          <button onClick={retry}>Try again</button>
        </p>
      )}
      {!state ? (
        <>
          {loading && !error ? (
            <p role="status">Opening your party…</p>
          ) : (
            <Admission
              entry={entry}
              expired={expired && error.code === "session_expired"}
              act={act}
              pending={pending}
              clearError={() => setActionError("")}
            />
          )}
        </>
      ) : (
        <Party key={state.round_id} state={state} act={act} pending={pending} />
      )}
      <footer className="wbw-footer">
        A shared screen. A few secret ideas. A story only your group could make.
      </footer>
    </main>
  );
}

function Admission({
  entry,
  expired,
  act,
  pending,
  clearError,
}: {
  entry: "host" | "join";
  expired: boolean;
  act: Action;
  pending: boolean;
  clearError: () => void;
}) {
  const [params] = useSearchParams();
  const [code, setCode] = useState(params.get("code") || "");
  const [name, setName] = useState("");
  const [passcode, setPasscode] = useState("");
  const [entryError, setEntryError] = useState("");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    setEntryError("");
    clearError();
    const normalized = normalizeRoomCode(code);
    if (entry === "join") {
      if (normalized === null) {
        setEntryError(ROOM_CODE_FORMAT_MESSAGE);
        return;
      }
      if (!name.trim()) {
        setEntryError("Enter your name.");
        return;
      }
      setCode(normalized);
    }
    void act(
      entry === "host" ? "/host" : "/join",
      entry === "host" ? { passcode } : { code: normalized, name },
    );
  };
  return (
    <section className="wbw-entry wbw-panel">
      <div>
        <p className="wbw-eyebrow">
          {entry === "host" ? "THE SHARED SCREEN" : "YOUR SEAT AT THE STORY"}
        </p>
        <h2>
          {entry === "host"
            ? "Bring everyone together."
            : "Let’s make something unexpected."}
        </h2>
        <p>
          {entry === "host"
            ? "Open this screen on a laptop. Invite 3–4 friends to join on their phones, then reveal your story together."
            : "Join on your phone. Your ideas stay private until the host reveals them on the shared screen."}
        </p>
        {expired && (
          <p className="wbw-notice">
            This party has ended. Join again to play.
          </p>
        )}
      </div>
      <form onSubmit={submit} noValidate={entry === "join"}>
        {entryError && (
          <p className="wbw-error" role="alert">{entryError}</p>
        )}
        {entry === "host" ? (
          <label>
            Host passcode
            <input
              autoComplete="current-password"
              type="password"
              value={passcode}
              onChange={(e) => setPasscode(e.target.value)}
              required
            />
          </label>
        ) : (
          <>
            <label>
              Room code
              <RoomCodeInput
                value={code}
                onChange={(e) => {
                  setCode(e.target.value);
                  setEntryError("");
                  clearError();
                }}
                required
              />
            </label>
            <label>
              Your name
              <input
                autoComplete="nickname"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </label>
          </>
        )}
        <button className="wbw-primary" disabled={pending}>
          {pending
            ? "Opening…"
            : entry === "host"
              ? "Open host screen"
              : "Join the story"}
        </button>
      </form>
    </section>
  );
}

function Countdown({
  deadline,
  serverTime,
}: {
  deadline: number;
  serverTime: number;
}) {
  const [seconds, setSeconds] = useState(
    Math.max(0, Math.ceil(deadline - serverTime)),
  );
  useEffect(() => {
    const received = Date.now();
    const update = () =>
      setSeconds(
        Math.max(
          0,
          Math.ceil(deadline - serverTime - (Date.now() - received) / 1000),
        ),
      );
    update();
    const timer = setInterval(update, 250);
    return () => clearInterval(timer);
  }, [deadline, serverTime]);
  return (
    <span className="wbw-timer" aria-label={`${seconds} seconds remaining`}>
      {seconds}
      <small> sec</small>
    </span>
  );
}

function Party({
  state: s,
  act,
  pending,
}: {
  state: Snapshot;
  act: Action;
  pending: boolean;
}) {
  const [mode, setMode] = useState<"fixture" | "live">("fixture");
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const host = s.role === "host";
  const blocked = pending || s.provider_closing || s.busy || s.closing;
  const phase = s.phase;
  return (
    <>
      {(phase === "LOBBY" ? mode : s.mode) === "fixture" && (
        <div className="wbw-fixture">
          <strong>FIXTURE REHEARSAL</strong>
          <span>
            Fixed example contributions + prerecorded illustrated clips. No AI
            generation.
          </span>
        </div>
      )}
      <div className="wbw-status">
        <span>{host ? "HOST DISPLAY" : `PLAYING AS ${s.your_name}`}</span>
        <span>
          ROOM <strong>{s.code}</strong>
        </span>
      </div>
      {s.provider_closing && phase !== "GENERATING" && (
        <p className="wbw-notice">
          Finishing the previous session. Saved clips can still play; another
          round waits for confirmed cleanup.
          {host && phase === "RESULTS" && (
            <button
              onClick={() => void act("/provider/cleanup")}
              disabled={pending}
            >
              Retry cleanup
            </button>
          )}
        </p>
      )}
      {s.closing && (
        <p className="wbw-notice">
          This party is closing. Return to games to check cleanup.
        </p>
      )}
      <div className="wbw-phase-heading">
        <h2>{phaseLabels[phase]}</h2>
        {phase === "INPUT" && s.input_deadline && (
          <Countdown deadline={s.input_deadline} serverTime={s.server_time} />
        )}
      </div>
      {phase === "LOBBY" && (
        <div className="wbw-lobby">
          <section className="wbw-panel">
            <p className="wbw-eyebrow">
              {host ? "INVITE YOUR FRIENDS" : "YOU’RE IN"}
            </p>
            <h3>
              {host
                ? "The good kind of group project."
                : "Waiting for the host to start."}
            </h3>
            <p>
              Everyone secretly adds a place, a character, an action, or a
              consequence. Watch each idea appear on the laptop.
            </p>
            {host && (
              <>
                <div className="wbw-code">{s.code}</div>
                <label>
                  Join on a phone
                  <input
                    aria-label="Phone join link"
                    value={s.join_url}
                    readOnly
                    onFocus={(event) => event.target.select()}
                  />
                </label>
                <button
                  onClick={async () => {
                    const success = await copyText(s.join_url);
                    setCopied(success);
                    setCopyFailed(!success);
                  }}
                >
                  {copied ? "Copied!" : "Copy join link"}
                </button>
                {copyFailed && (
                  <p role="status">
                    Select the phone join link above, then choose Copy.
                  </p>
                )}
                <label className="wbw-mode">
                  Round mode
                  <select
                    value={mode}
                    onChange={(e) =>
                      setMode(e.target.value as "fixture" | "live")
                    }
                  >
                    <option value="fixture">Fixture rehearsal</option>
                    <option
                      value="live"
                      disabled={
                        !!s.live_unavailable_reason || !s.live_attempts_left
                      }
                    >
                      Live FastH3
                    </option>
                  </select>
                </label>
                {s.live_unavailable_reason && (
                  <p className="wbw-muted">{s.live_unavailable_reason}</p>
                )}
              </>
            )}
          </section>
          <section className="wbw-panel wbw-roster">
            <p className="wbw-eyebrow">THE STORYTELLERS</p>
            <h3>{s.players.length} / 4 players</h3>
            <ol>
              {s.players.map((name, i) => (
                <li key={i}>
                  <span>{String(i + 1).padStart(2, "0")}</span>
                  {name}
                </li>
              ))}
              {Array.from({ length: 4 - s.players.length }, (_, i) => (
                <li className="wbw-empty" key={`empty${i}`}>
                  <span>+</span>Room for a friend
                </li>
              ))}
            </ol>
            <p>
              {s.players.length < 3
                ? "Waiting for at least 3 players."
                : "Your group is ready."}{" "}
              {s.players.length === 3 &&
                "The first player gets two contributions."}
            </p>
            {host && (
              <button
                className="wbw-primary"
                disabled={blocked || s.players.length < 3}
                onClick={() => void act("/round/start", { mode })}
              >
                Start round →
              </button>
            )}
          </section>
        </div>
      )}
      {phase === "INPUT" &&
        (host ? (
          <section className="wbw-panel wbw-center">
            <span className="wbw-big-count">
              {s.collected}
              <i>/4</i>
            </span>
            <h3>Secret ideas are coming in.</h3>
            <p>
              The story stays folded until the reveal. Everyone has 45 seconds.
            </p>
            <Progress count={s.collected} />
          </section>
        ) : (
          <div className="wbw-assignments">
            {s.assignments?.map((a) => (
              <Contribution
                key={a.index}
                assignment={a}
                act={act}
                pending={pending}
              />
            ))}
            <p className="wbw-muted">
              {s.collected} of 4 contributions accepted. Keep the others a
              surprise.
            </p>
          </div>
        ))}
      {phase === "GENERATING" && (
        <section className="wbw-panel wbw-center">
          <div className="wbw-orbit" aria-hidden="true">
            ✳
          </div>
          <h3>
            {s.mode === "fixture"
              ? "Preparing the rehearsal clips."
              : "Preparing your story."}
          </h3>
          <p>
            {s.saved_clips} of 4 clips saved. Each addition follows the one
            before it.
          </p>
          <Progress count={s.saved_clips} />
          {s.generation_deadline && (
            <p className="wbw-muted">
              Time remaining{" "}
              <Countdown
                deadline={s.generation_deadline}
                serverTime={s.server_time}
              />
            </p>
          )}
        </section>
      )}
      {(phase === "REVEAL" || phase === "RESULTS") && (
        <>
          {s.message && (
            <p
              className={`wbw-result-message ${s.result === "partial" ? "wbw-notice" : ""}`}
            >
              {s.message}
            </p>
          )}
          {host ? (
            <Playback state={s} act={act} pending={pending || s.closing} />
          ) : (
            <section className="wbw-panel wbw-phone-reveal">
              <p className="wbw-eyebrow">LOOK UP AT THE LAPTOP</p>
              <h3>
                {s.disclosed_index < 0
                  ? "Your story is still a secret."
                  : "Look what you made together."}
              </h3>
              <p>
                {phase === "REVEAL"
                  ? "The host will reveal each addition. Your phone follows along."
                  : "The host can replay or start another round."}
              </p>
            </section>
          )}
          {s.cards.length > 0 && (
            <div className="wbw-story" aria-label="Revealed story">
              {s.cards.map((card) => (
                <article className="wbw-card" key={card.index}>
                  <div>
                    <span>{String(card.index + 1).padStart(2, "0")}</span>
                    <p>{card.category}</p>
                  </div>
                  <h3>{card.text}</h3>
                  <small>by {card.contributor}</small>
                </article>
              ))}
            </div>
          )}
          {phase === "RESULTS" && !s.cards.length && (
            <p className="wbw-muted">
              No contributions were disclosed in this round.
            </p>
          )}
          {host && phase === "RESULTS" && (
            <button
              className="wbw-primary"
              disabled={blocked || (s.mode === "live" && !s.live_attempts_left)}
              onClick={() => void act("/round/new")}
            >
              Another round · same players →
            </button>
          )}
          {host && !s.live_attempts_left && (
            <p className="wbw-notice">
              The live session allowance for this server run has been used.
            </p>
          )}
        </>
      )}
      {host && ["INPUT", "GENERATING", "REVEAL"].includes(phase) && (
        <div className="wbw-bottom-actions">
          <button
            className="wbw-danger"
            disabled={pending || s.closing}
            onClick={() => void act("/round/end")}
          >
            End round
          </button>
          <span>Stops new work and keeps only the disclosed story.</span>
        </div>
      )}
      {host && ["LOBBY", "RESULTS"].includes(phase) && (
        <div className="wbw-bottom-actions">
          {confirmReset ? (
            <>
              <span>
                Everyone will need to rejoin. The replay will be cleared.
              </span>
              <button
                className="wbw-danger"
                disabled={blocked}
                onClick={() => void act("/room/reset")}
              >
                Reset party now
              </button>
              <button onClick={() => setConfirmReset(false)}>Keep party</button>
            </>
          ) : (
            <button
              className="wbw-text-button"
              disabled={blocked}
              onClick={() => setConfirmReset(true)}
            >
              Reset party
            </button>
          )}
        </div>
      )}
    </>
  );
}

function Progress({ count }: { count: number }) {
  return (
    <div className="wbw-progress" aria-label={`${count} of 4 complete`}>
      {[0, 1, 2, 3].map((index) => (
        <span key={index} className={index < count ? "done" : ""} />
      ))}
    </div>
  );
}

function Contribution({
  assignment: a,
  act,
  pending,
}: {
  assignment: Assignment;
  act: Action;
  pending: boolean;
}) {
  const [text, setText] = useState("");
  // Match the backend's Unicode White_Space trim and count code points, not UTF-16 units.
  const trimmed = text.replace(/^\p{White_Space}+|\p{White_Space}+$/gu, "");
  const count = Array.from(trimmed).length;
  const accepted = a.accepted_text !== null;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    void act("/contribution", {
      slot_index: a.index,
      text: a.fixture_text ?? text,
    });
  };
  return (
    <form
      className={`wbw-panel wbw-contribution ${accepted ? "accepted" : ""}`}
      onSubmit={submit}
    >
      <p className="wbw-eyebrow">
        YOUR CONTRIBUTION {a.index + 1} / 4 · {a.category.toUpperCase()}
      </p>
      <h3>{a.question}</h3>
      {accepted ? (
        <>
          <p className="wbw-accepted-text">{a.accepted_text}</p>
          <p className="wbw-accepted-badge">
            ✓ Accepted and locked. Your idea stays private.
          </p>
        </>
      ) : (
        <>
          <p>Write a word, phrase, or short sentence. Keep it to one idea.</p>
          {a.fixture_text !== null ? (
            <>
              <p className="wbw-muted">
                This rehearsal uses the fixed contribution below.
              </p>
              <blockquote>{a.fixture_text}</blockquote>
              <button className="wbw-primary" disabled={pending}>
                Submit example
              </button>
            </>
          ) : (
            <>
              <label htmlFor={`contribution-${a.index}`}>
                {a.category}
                <textarea
                  id={`contribution-${a.index}`}
                  value={text}
                  onChange={(event) => setText(event.target.value)}
                  rows={4}
                  aria-describedby={`hint-${a.index}`}
                />
              </label>
              <div className="wbw-input-hint" id={`hint-${a.index}`}>
                <span>For example: {a.example}</span>
                <span className={count > 120 ? "wbw-over-limit" : ""}>
                  {count} / 120
                </span>
              </div>
              {count > 120 && (
                <p className="wbw-error">
                  That idea is a little long. Keep it to 120 characters.
                </p>
              )}
              <button
                className="wbw-primary"
                disabled={pending || count < 1 || count > 120}
              >
                Lock in my idea
              </button>
            </>
          )}
        </>
      )}
    </form>
  );
}

function Playback({
  state: s,
  act,
  pending,
}: {
  state: Snapshot;
  act: Action;
  pending: boolean;
}) {
  const [replay, setReplay] = useState<number | null>(null);
  const [hidden, setHidden] = useState(false);
  const [playbackError, setPlaybackError] = useState(false);
  const video = useRef<HTMLVideoElement>(null);
  const index = replay ?? s.disclosed_index;
  const clip = s.clips?.find((c) => c.index === index);
  const card = s.cards.find((c) => c.index === index);
  const advance = async () => {
    setHidden(false);
    setPlaybackError(false);
    setReplay(null);
    await act("/reveal/next", { expected_reveal_index: s.disclosed_index });
  };
  return (
    <section className="wbw-playback">
      {clip && !hidden ? (
        <>
          <video
            ref={video}
            key={clip.url}
            src={clip.url}
            controls
            muted
            playsInline
            autoPlay
            preload="metadata"
            onError={() => setPlaybackError(true)}
            onEnded={() => {
              if (replay !== null && replay < (s.clips?.length ?? 0) - 1)
                setReplay(replay + 1);
              else setReplay(null);
            }}
            aria-label={`Saved ${card?.category || "story"} clip`}
          />
          {card && (
            <div className="wbw-current-card">
              <span>
                {card.category} · by {card.contributor}
              </span>
              <p>{card.text}</p>
            </div>
          )}
        </>
      ) : (
        <div className="wbw-curtain">
          <span aria-hidden="true">✳</span>
          <h3>
            {hidden
              ? "Video hidden."
              : s.saved_clips
                ? "Ready for the first surprise?"
                : "The next story is waiting for you."}
          </h3>
          <p>
            {hidden
              ? "You can show this disclosed clip again or end the round."
              : s.saved_clips
                ? "Only Play will unfold the first contribution."
                : "Start another round with your group."}
          </p>
        </div>
      )}
      {playbackError && (
        <p className="wbw-error" role="alert">
          The saved video could not play.{" "}
          <button
            onClick={() => {
              video.current?.load();
              setPlaybackError(false);
            }}
          >
            Reload saved clip
          </button>
        </p>
      )}
      <div className="wbw-video-actions">
        {s.phase === "REVEAL" && (
          <button
            className="wbw-primary"
            disabled={pending}
            onClick={() => void advance()}
          >
            {s.disclosed_index < 0
              ? "Play the first addition"
              : s.disclosed_index + 1 < s.saved_clips
                ? "Next addition →"
                : "Finish story →"}
          </button>
        )}
        {s.phase === "RESULTS" && (s.clips?.length ?? 0) > 0 && (
          <button
            className="wbw-primary"
            onClick={() => {
              setHidden(false);
              setPlaybackError(false);
              setReplay(0);
              if (index === 0 && video.current) {
                video.current.currentTime = 0;
                void video.current.play().catch(() => setPlaybackError(true));
              }
            }}
          >
            Replay saved story ↻
          </button>
        )}
        {clip && (
          <button
            onClick={() => {
              video.current?.pause();
              setHidden(!hidden);
            }}
          >
            {hidden ? "Show video" : "Hide video"}
          </button>
        )}
        {replay !== null && (
          <span role="status">
            Replaying {replay + 1} of {s.clips?.length}
          </span>
        )}
      </div>
    </section>
  );
}
