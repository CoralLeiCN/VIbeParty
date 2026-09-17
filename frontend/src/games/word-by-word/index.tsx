import Hls from "hls.js";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError, apiFetch, apiPost } from "../../shared/api";
import { HostControls } from "../../shared/HostControls";
import { randomPlayerName } from "../../shared/playerNames";
import { copyText } from "../../shared/clipboard";
import { HostAccessField } from "../../shared/HostAccessField";
import { HostRecovery } from "../../shared/HostRecovery";
import { useHostAccess } from "../../shared/useHostAccess";
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
  at_seconds: number;
};
type Assignment = {
  index: number;
  category: string;
  question: string;
  example: string;
  accepted_text: string | null;
  fixture_text: string | null;
};
type Snapshot = {
  role: "host" | "player";
  code: string;
  round_id: string;
  revision: number;
  phase: "LOBBY" | "INPUT" | "GENERATING" | "STREAMING" | "RESULTS";
  mode: "fixture" | "live";
  players: string[];
  player_count: number;
  join_url: string;
  server_time: number;
  input_deadline: number | null;
  generation_deadline: number | null;
  collected: number;
  recording_ready: boolean;
  disclosed_index: number;
  cards: Card[];
  assignments?: Assignment[];
  your_name?: string;
  stream_url?: string | null;
  recording_url?: string | null;
  result: string | null;
  message: string;
  provider_closing: boolean;
  closing: boolean;
  busy: boolean;
  live_attempts_left: number;
  live_unavailable_reason: string | null;
  image_source?: string;
  uploaded_image_url?: string | null;
  image_sources?: {
    id: string;
    label: string;
    unavailable_reason: string | null;
  }[];
};
type Action = (
  suffix: string,
  fields?: Record<string, unknown>,
  file?: File,
) => Promise<boolean>;

const phaseLabels = {
  LOBBY: "Gather your people",
  INPUT: "A little secret",
  GENERATING: "Preparing your story",
  STREAMING: "Your story is unfolding",
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
  const act: Action = async (suffix, fields = {}, file) => {
    if (actionLock.current) return false;
    actionLock.current = true;
    setPending(true);
    setActionError("");
    try {
      if (file) {
        if (file.size > 10 * 1024 * 1024)
          throw new Error("Choose an image smaller than 10 MB.");
        if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
          throw new Error("Choose a PNG, JPEG, or WebP image.");
        }
        await apiFetch(`${API}${suffix}`, {
          method: "PUT",
          body: file,
          headers: { "Content-Type": file.type },
        });
      } else {
        await apiPost(`${API}${suffix}`, {
          ...(state ? { round_id: state.round_id } : {}),
          ...fields,
        });
      }
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
              onRecovered={retry}
            />
          )}
        </>
      ) : (
        <>
          {entry === "host" && state.role !== "host" && (
            <HostRecovery onRecovered={retry} />
          )}
          <Party
            key={state.round_id}
            state={state}
            act={act}
            pending={pending}
          />
        </>
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
  onRecovered,
}: {
  entry: "host" | "join";
  expired: boolean;
  act: Action;
  pending: boolean;
  clearError: () => void;
  onRecovered: () => void;
}) {
  const [params] = useSearchParams();
  const access = useHostAccess(entry === "host");
  const [code, setCode] = useState(params.get("code") || "");
  const [name, setName] = useState(randomPlayerName);
  const [passcode, setPasscode] = useState("");
  const [entryError, setEntryError] = useState("");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!access.ready) return;
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
      entry === "host"
        ? access.localMode
          ? {}
          : { passcode }
        : { code: normalized, name },
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
            ? "Open this screen on a laptop. Choose 1–4 players to join on their phones, then reveal your story together."
            : "Join on your phone. Your ideas stay private until they appear in the story on the shared screen."}
        </p>
        {expired && entry === "join" && (
          <p className="wbw-notice">
            This party has ended. Join again to play.
          </p>
        )}
      </div>
      <form onSubmit={submit} noValidate={entry === "join"}>
        {entryError && (
          <p className="wbw-error" role="alert">
            {entryError}
          </p>
        )}
        {entry === "host" ? (
          <HostAccessField
            access={access}
            id="wbw-passcode"
            label="Host passcode"
            value={passcode}
            onChange={setPasscode}
          />
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
        <button className="wbw-primary" disabled={pending || !access.ready}>
          {pending
            ? "Opening…"
            : entry === "host"
              ? "Create party"
              : "Join the story"}
        </button>
      </form>
      {entry === "host" && (
        <HostRecovery
          onRecovered={() => {
            clearError();
            onRecovered();
          }}
        />
      )}
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
  const waitingPlayers = s.player_count - s.players.length;
  const imageSource = s.image_sources?.find(
    (source) => source.id === s.image_source,
  );
  const liveBlocked =
    mode === "live" &&
    (!!s.live_unavailable_reason ||
      !s.live_attempts_left ||
      !imageSource ||
      !!imageSource.unavailable_reason);
  const assignmentSummary = [
    "",
    "One player writes all four contributions.",
    "Each player writes two contributions.",
    "The first player writes two contributions; the others write one each.",
    "Each player writes one contribution.",
  ][s.player_count];
  return (
    <>
      {(phase === "LOBBY" ? mode : s.mode) === "fixture" && (
        <div className="wbw-fixture">
          <strong>FIXTURE REHEARSAL</strong>
          <span>
            WW-CAT-01 · Fixed example contributions and one scripted video. No
            AI generation.
          </span>
        </div>
      )}
      <div className="wbw-status">
        <span>{host ? "HOST DISPLAY" : `PLAYING AS ${s.your_name}`}</span>
        <span>
          ROOM <strong>{s.code}</strong>
        </span>
      </div>
      {s.provider_closing && phase === "RESULTS" && (
        <p className="wbw-notice">
          Finishing the previous session. Your story can still play; another
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
                    disabled={blocked}
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
                      Live LingBot World 2
                    </option>
                  </select>
                </label>
                {s.live_unavailable_reason && (
                  <p className="wbw-muted">{s.live_unavailable_reason}</p>
                )}
                {!s.live_attempts_left && (
                  <p className="wbw-muted">
                    The live session limit for this server run is reached.
                  </p>
                )}
                {mode === "live" && (
                  <div className="wbw-image-choice">
                    <label>
                      Starting image
                      <select
                        value={s.image_source}
                        disabled={blocked}
                        onChange={(event) =>
                          void act("/round/image-source", {
                            image_source: event.target.value,
                          })
                        }
                      >
                        {s.image_sources?.map((source) => (
                          <option key={source.id} value={source.id}>
                            {source.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    {s.image_source === "upload" ? (
                      <>
                        <p className="wbw-muted">
                          Choose the starting scene for this round. Use an image
                          of the place, leaving the character and events for the
                          players.
                        </p>
                        <label>
                          Upload starting image
                          <input
                            type="file"
                            accept="image/png,image/jpeg,image/webp"
                            disabled={blocked}
                            onChange={(event) => {
                              const file = event.target.files?.[0];
                              if (file)
                                void act(
                                  `/round/${s.round_id}/starting-image`,
                                  {},
                                  file,
                                );
                              event.target.value = "";
                            }}
                          />
                        </label>
                        <p className="wbw-muted">
                          PNG, JPEG, or WebP · up to 10 MB and 16 megapixels.
                        </p>
                        {s.uploaded_image_url && (
                          <div className="wbw-image-preview">
                            <img
                              src={s.uploaded_image_url}
                              alt="Uploaded starting scene for this round"
                            />
                            <p role="status">Image ready for this round.</p>
                          </div>
                        )}
                      </>
                    ) : s.image_source === "configured" ? (
                      <p className="wbw-muted">
                        Use the image configured on the host. It should match
                        the place for this round.
                      </p>
                    ) : (
                      <p className="wbw-muted">
                        After everyone answers, create one image from the first
                        player’s Place answer only.
                        {s.image_source === "codex" &&
                          " Uses the host computer’s Codex login and included usage."}
                      </p>
                    )}
                    {imageSource?.unavailable_reason && (
                      <p className="wbw-notice" role="status">
                        {imageSource.unavailable_reason}
                      </p>
                    )}
                    {s.image_source === "codex" && (
                      <>
                        {!imageSource?.unavailable_reason && (
                          <p className="wbw-muted">
                            Codex is signed in and image generation is enabled.
                          </p>
                        )}
                        <button
                          disabled={blocked}
                          onClick={() => void act("/round/check-codex")}
                        >
                          Check Codex again
                        </button>
                      </>
                    )}
                  </div>
                )}
              </>
            )}
          </section>
          <section className="wbw-panel wbw-roster">
            <p className="wbw-eyebrow">THE STORYTELLERS</p>
            <h3>
              {s.players.length} / {s.player_count}{" "}
              {s.player_count === 1 ? "player" : "players"}
            </h3>
            {host && (
              <label className="wbw-player-count">
                Number of players
                <select
                  value={s.player_count}
                  disabled={blocked}
                  onChange={(event) =>
                    void act("/room/settings", {
                      player_count: Number(event.target.value),
                    })
                  }
                >
                  {[1, 2, 3, 4].map((count) => (
                    <option
                      key={count}
                      value={count}
                      disabled={count < s.players.length}
                    >
                      {count} {count === 1 ? "player" : "players"}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <ol>
              {s.players.map((name, i) => (
                <li key={i}>
                  <span>{String(i + 1).padStart(2, "0")}</span>
                  {name}
                </li>
              ))}
              {Array.from({ length: waitingPlayers }, (_, i) => (
                <li className="wbw-empty" key={`empty${i}`}>
                  <span>+</span>Room for a friend
                </li>
              ))}
            </ol>
            <p>
              {waitingPlayers > 0
                ? `Waiting for ${waitingPlayers} more ${waitingPlayers === 1 ? "player" : "players"}.`
                : "Your group is ready."}{" "}
              {assignmentSummary}
            </p>
            {host && s.players.length > 1 && (
              <p className="wbw-muted">
                To choose fewer players than have joined, use Reset party below.
              </p>
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
              ? "Preparing the rehearsal story."
              : "Preparing your story."}
          </h3>
          <p>
            {s.image_source === "upload" || s.image_source === "configured"
              ? "Preparing the selected starting image."
              : "Creating the starting scene."}{" "}
            Your story will play automatically, adding each idea as the video
            continues.
          </p>
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
      {(phase === "STREAMING" || phase === "RESULTS") && (
        <>
          {s.message && (
            <p
              className={`wbw-result-message ${s.result === "partial" ? "wbw-notice" : ""}`}
            >
              {s.message}
            </p>
          )}
          {host ? (
            <Playback state={s} />
          ) : (
            <section className="wbw-panel wbw-phone-reveal">
              <p className="wbw-eyebrow">LOOK UP AT THE LAPTOP</p>
              <h3>
                {s.disclosed_index < 0
                  ? "Your story is still a secret."
                  : "Look what you made together."}
              </h3>
              <p>
                {phase === "STREAMING"
                  ? "Each idea joins the same ongoing video. Your phone follows along."
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
          {host && !s.live_attempts_left && (
            <p className="wbw-notice">
              The live session allowance for this server run has been used.
            </p>
          )}
        </>
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
      {host && (
        <HostControls
          gameId="word-by-word"
          busy={pending || s.busy}
          closing={s.closing}
          start={
            phase === "LOBBY"
              ? {
                  run: () => void act("/round/start", { mode }),
                  disabled: blocked || waitingPlayers !== 0 || liveBlocked,
                }
              : undefined
          }
          again={
            phase === "RESULTS"
              ? {
                  run: () => void act("/round/new"),
                  disabled: blocked,
                }
              : undefined
          }
          stop={
            ["INPUT", "GENERATING", "STREAMING"].includes(phase)
              ? {
                  run: () => void act("/round/end"),
                }
              : undefined
          }
        />
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

function Playback({ state: s }: { state: Snapshot }) {
  const video = useRef<HTMLVideoElement>(null);
  const initialPosition = useRef(
    s.phase === "STREAMING" ? (s.cards.at(-1)?.at_seconds ?? 0) : 0,
  );
  const [replaying, setReplaying] = useState(false);
  const [playbackError, setPlaybackError] = useState(false);
  const [needsPlay, setNeedsPlay] = useState(false);
  const [reload, setReload] = useState(0);
  const [position, setPosition] = useState(0);
  // Keep the same stream attached when the round finishes; let its buffered tail play.
  const source = replaying ? s.recording_url : s.stream_url;
  const card = [...s.cards]
    .reverse()
    .find((item) => item.at_seconds <= position);

  useEffect(() => {
    const element = video.current;
    if (!element || !source) return;
    let disposed = false;
    const play = () => {
      void element.play().catch(() => {
        if (!disposed) setNeedsPlay(true);
      });
    };
    let hls: Hls | undefined;
    if (source.endsWith(".m3u8") && Hls.isSupported()) {
      hls = new Hls({
        startPosition: initialPosition.current,
        maxBufferLength: 30,
      });
      hls.loadSource(source);
      hls.attachMedia(element);
      hls.on(Hls.Events.MANIFEST_PARSED, play);
      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal && !disposed) setPlaybackError(true);
      });
    } else if (
      !source.endsWith(".m3u8") ||
      element.canPlayType("application/vnd.apple.mpegurl")
    ) {
      element.src = source;
      play();
    } else {
      // This callback runs after setup, matching media event error handling.
      queueMicrotask(() => {
        if (!disposed) setPlaybackError(true);
      });
    }
    return () => {
      disposed = true;
      hls?.destroy();
      element.pause();
      element.removeAttribute("src");
      element.load();
    };
  }, [source, reload]);

  const resume = () => {
    void video.current
      ?.play()
      .then(() => setNeedsPlay(false))
      .catch(() => setNeedsPlay(true));
  };
  return (
    <section className="wbw-playback">
      {source ? (
        <>
          <video
            ref={video}
            controls={replaying || s.phase === "RESULTS"}
            muted
            playsInline
            autoPlay
            onTimeUpdate={() => setPosition(video.current?.currentTime ?? 0)}
            onPlaying={() => setNeedsPlay(false)}
            onError={() => setPlaybackError(true)}
            aria-label={replaying ? "Saved story" : "Continuous story"}
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
          <h3>The next story is waiting for you.</h3>
          <p>Start another round with your group.</p>
        </div>
      )}
      {s.phase === "STREAMING" && (
        <p role="status">
          One continuous story · {s.cards.length} of 4 ideas added
        </p>
      )}
      {needsPlay && !playbackError && (
        <button onClick={resume}>Resume story playback</button>
      )}
      {playbackError && (
        <p className="wbw-error" role="alert">
          Playback was interrupted. Your story keeps running.
          <button
            onClick={() => {
              setPlaybackError(false);
              setReload((value) => value + 1);
            }}
          >
            Reconnect video
          </button>
        </p>
      )}
      {s.phase === "RESULTS" && s.recording_url && (
        <div className="wbw-video-actions">
          <button
            className="wbw-primary"
            onClick={() => {
              setPlaybackError(false);
              setPosition(0);
              if (replaying && video.current) {
                video.current.currentTime = 0;
                resume();
              } else setReplaying(true);
            }}
          >
            Replay saved story ↻
          </button>
        </div>
      )}
    </section>
  );
}
