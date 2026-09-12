import { useEffect, useRef, useState } from "react";
import type { Snapshot } from "./types";
import styles from "./Royale.module.css";

type Props = {
  state: Snapshot;
  busy: boolean;
  act: (path: string, data?: object) => Promise<void>;
};

export function Arena({ state, busy, act }: Props) {
  const videos = useRef<Record<string, HTMLVideoElement>>({});
  const running = useRef(false);
  const starting = useRef(false);
  const ended = useRef(new Set<string>());
  const [status, setStatus] = useState<Record<string, string>>({});
  const [playing, setPlaying] = useState(false);
  const [watched, setWatched] = useState(false);
  const [selection, setSelection] = useState<string | null>(null);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [message, setMessage] = useState(
    "Load the arena, then press Play arena.",
  );
  const readyTiles = state.arena!.filter((t) => t.status === "ready");
  const eligibleIds = readyTiles.map((t) => t.id!).join(",");
  const allReady =
    readyTiles.length > 0 && readyTiles.every((t) => status[t.id!] === "ready");

  function pause() {
    running.current = false;
    Object.values(videos.current).forEach((video) => video.pause());
    setPlaying(false);
  }

  async function play() {
    const group = readyTiles.map((t) => videos.current[t.id!]).filter(Boolean);
    if (
      group.length !== readyTiles.length ||
      group.some((v) => v.readyState < 2)
    ) {
      setMessage(
        "Some clips are still loading. Retry playback or ask the host to exclude a clip.",
      );
      return;
    }
    ended.current.clear();
    starting.current = true;
    group.forEach((v) => {
      v.currentTime = 0;
    });
    running.current = true;
    try {
      await Promise.all(group.map((v) => v.play()));
      if (!running.current) {
        group.forEach((v) => v.pause());
        return;
      }
      setPlaying(true);
      setMessage("Arena playing together. All clips repeat as a group.");
      starting.current = false;
    } catch {
      pause();
      setMessage("Playback was blocked. Tap Play arena to try again.");
    }
  }

  function finish(id: string) {
    if (!running.current) return;
    ended.current.add(id);
    if (readyTiles.every((tile) => ended.current.has(tile.id!))) {
      setMessage("One full arena playback completed. Repeating together.");
      void play();
    }
  }

  useEffect(() => {
    running.current = false;
    Object.values(videos.current).forEach((v) => v.pause());
    setPlaying(false);
    setWatched(false);
    setSelection(null);
    return () => {
      running.current = false;
    };
  }, [eligibleIds]);

  function failed(id: string, text: string) {
    pause();
    setStatus((current) => ({ ...current, [id]: "error" }));
    setMessage(text);
  }

  return (
    <section aria-label="Anonymous arena" className={styles.arenaSection}>
      <div className={styles.arenaHeading}>
        <h2>The arena</h2>
        <span>Same clips. Same positions.</span>
      </div>
      <div className={styles.arena}>
        {state.arena!.map((tile) => (
          <article
            key={tile.position}
            data-testid={`tile-${tile.position}`}
            className={`${styles.tile} ${tile.winner ? styles.winner : ""} ${selection === tile.id ? styles.selected : ""}`}
          >
            <div className={styles.tileTitle}>
              <strong>{tile.label}</strong>
              {tile.winner && <span>Winner ★</span>}
            </div>
            {tile.status === "ready" ? (
              <>
                <video
                  ref={(node) => {
                    if (node) videos.current[tile.id!] = node;
                    else delete videos.current[tile.id!];
                  }}
                  src={tile.url}
                  muted
                  playsInline
                  preload="auto"
                  aria-label={tile.label}
                  onCanPlay={() =>
                    setStatus((current) => ({
                      ...current,
                      [tile.id!]: "ready",
                    }))
                  }
                  onError={() =>
                    failed(
                      tile.id!,
                      `${tile.label} could not load. Retry or exclude it before voting.`,
                    )
                  }
                  onWaiting={(event) => {
                    if (
                      running.current &&
                      !starting.current &&
                      !event.currentTarget.seeking
                    )
                      failed(
                        tile.id!,
                        `${tile.label} stalled. The arena is paused.`,
                      );
                  }}
                  onEnded={() => finish(tile.id!)}
                />
                {status[tile.id!] !== "ready" && (
                  <p role="status">
                    {status[tile.id!] === "error"
                      ? "Playback unavailable"
                      : "Loading clip…"}
                  </p>
                )}
                {state.mode === "fixture" && (
                  <small className={styles.fixtureCaption}>
                    Fixture video · synthetic motion sample
                  </small>
                )}
                {state.phase === "screening" && state.me.host && (
                  <details className={styles.exclude}>
                    <summary>Exclude clip</summary>
                    <label htmlFor={`reason-${tile.id}`}>
                      Public exclusion reason
                    </label>
                    <input
                      id={`reason-${tile.id}`}
                      value={reasons[tile.id!] || ""}
                      maxLength={120}
                      onChange={(event) =>
                        setReasons((current) => ({
                          ...current,
                          [tile.id!]: event.target.value,
                        }))
                      }
                    />
                    <button
                      disabled={busy || !reasons[tile.id!]?.trim()}
                      className={styles.quiet}
                      onClick={() => {
                        pause();
                        void act("/round/exclude", {
                          entry_id: tile.id,
                          reason: reasons[tile.id!],
                        });
                      }}
                    >
                      Exclude {tile.label}
                    </button>
                  </details>
                )}
                {state.phase === "voting" && (
                  <button
                    className={styles.choose}
                    aria-pressed={selection === tile.id}
                    disabled={busy || state.me.voted || tile.own}
                    onClick={() => setSelection(tile.id!)}
                  >
                    {tile.own
                      ? "Your clip · cannot vote"
                      : selection === tile.id
                        ? "Selected ✓"
                        : `Choose ${tile.label}`}
                  </button>
                )}
                {state.phase === "results" && (
                  <div className={styles.reveal}>
                    <strong>{tile.author}</strong>
                    <span>
                      {tile.votes} {tile.votes === 1 ? "vote" : "votes"}
                    </span>
                    <p>{tile.prompt}</p>
                  </div>
                )}
              </>
            ) : (
              <div className={styles.placeholder}>
                <span>
                  {tile.status === "excluded" ? "Excluded" : "No entry"}
                </span>
                {tile.reason && <p>{tile.reason}</p>}
              </div>
            )}
          </article>
        ))}
      </div>
      <div className={styles.controls}>
        <button disabled={!allReady} onClick={() => void play()}>
          Play arena
        </button>
        <button
          className={styles.secondary}
          disabled={!playing}
          onClick={pause}
        >
          Pause all
        </button>
        <button
          className={styles.secondary}
          disabled={!allReady}
          onClick={() => void play()}
        >
          Replay all
        </button>
        <button
          className={styles.quiet}
          onClick={() => {
            pause();
            setStatus({});
            readyTiles.forEach((t) => videos.current[t.id!]?.load());
            setMessage("Reloading clips. Tap Play arena when ready.");
          }}
        >
          Retry playback
        </button>
      </div>
      <p className={styles.hint} role="status">
        {message}
      </p>
      {state.phase === "screening" && state.me.host && (
        <div className={styles.hostControls}>
          <label className={styles.check}>
            <input
              type="checkbox"
              checked={watched}
              onChange={(e) => setWatched(e.target.checked)}
            />
            The group watched a full playback of every remaining clip.
          </label>
          <button
            disabled={busy || !watched}
            onClick={() => void act("/round/open-voting", { watched: true })}
          >
            {readyTiles.length < 2 ? "Finish unscored showcase" : "Open voting"}
          </button>
        </div>
      )}
      {state.phase === "screening" && !state.me.host && (
        <p>The host opens voting after everyone has watched.</p>
      )}
      {state.phase === "voting" && (
        <div className={styles.hostControls}>
          <p>Vote privately. Authors and totals stay hidden until results.</p>
          {state.me.voted ? (
            <strong role="status">
              {state.me.vote ? "Vote locked ✓" : "Abstention locked ✓"}
            </strong>
          ) : (
            <div className={styles.controls}>
              <button
                disabled={busy || !selection}
                onClick={() => void act("/round/vote", { entry_id: selection })}
              >
                Vote
              </button>
              <button
                className={styles.secondary}
                disabled={busy}
                onClick={() => void act("/round/vote", { entry_id: null })}
              >
                Abstain
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
