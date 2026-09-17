import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import { apiPost } from "./api";
import type { GameId } from "./contracts";
import {
  END_GAME_DESCRIPTION,
  END_GAME_TITLE,
  PENDING_SWITCH_KEY,
} from "./hostActions";
import "./host-controls.css";

type Action = { run: () => void; disabled?: boolean };

export function HostControls({
  gameId,
  busy,
  closing = false,
  start,
  again,
  stop,
}: {
  gameId: GameId;
  busy: boolean;
  closing?: boolean;
  start?: Action;
  again?: Action;
  stop?: Action;
}) {
  const [confirm, setConfirm] = useState(false);
  const [ending, setEnding] = useState(false);
  const [error, setError] = useState("");
  const lock = useRef(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const endButton = useRef<HTMLButtonElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!confirm) return;
    const element = dialog.current;
    const opener = endButton.current;
    element?.showModal();
    return () => {
      element?.close();
      opener?.focus();
    };
  }, [confirm]);

  async function endGame() {
    if (lock.current) return;
    lock.current = true;
    setEnding(true);
    setError("");
    try {
      const result = await apiPost<{ status: "closed" | "closing" }>(
        "/api/party/close",
        { game_id: gameId },
      );
      if (result.status === "closing") {
        // The portal tracks cleanup and blocks admission until it completes.
        sessionStorage.setItem(PENDING_SWITCH_KEY, "close");
      } else {
        sessionStorage.removeItem(PENDING_SWITCH_KEY);
      }
      navigate("/");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Please try again.");
    } finally {
      lock.current = false;
      setEnding(false);
    }
  }

  return (
    <>
      <footer className="host-controls" role="group" aria-label="Host controls">
        <div className="host-controls-actions">
          {start && (
            <button
              className="host-control-primary"
              disabled={busy || ending || closing || start.disabled}
              onClick={start.run}
            >
              Start round
            </button>
          )}
          {again && (
            <button
              className="host-control-primary"
              disabled={busy || ending || closing || again.disabled}
              onClick={again.run}
            >
              Start another round
            </button>
          )}
          {stop && (
            <button
              disabled={busy || ending || closing || stop.disabled}
              onClick={stop.run}
            >
              End round
            </button>
          )}
          <button
            ref={endButton}
            disabled={busy || ending}
            onClick={() => {
              setError("");
              setConfirm(true);
            }}
          >
            End game
          </button>
        </div>
        {again && <p>Another round keeps the same players and room.</p>}
      </footer>
      {confirm &&
        createPortal(
          <dialog
            ref={dialog}
            className="host-confirm"
            aria-labelledby="end-game-title"
            aria-describedby="end-game-description"
            onCancel={(event) => {
              event.preventDefault();
              if (!ending) setConfirm(false);
            }}
          >
            <h2 id="end-game-title">{END_GAME_TITLE}</h2>
            <p id="end-game-description">{END_GAME_DESCRIPTION}</p>
            {error && <p role="alert">{error}</p>}
            <div className="host-controls-actions">
              <button
                className="host-control-primary"
                disabled={ending}
                onClick={() => void endGame()}
              >
                {ending ? "Ending game…" : "End game"}
              </button>
              <button
                disabled={ending}
                onClick={() => setConfirm(false)}
                autoFocus
              >
                Keep playing
              </button>
            </div>
          </dialog>,
          document.body,
        )}
    </>
  );
}
