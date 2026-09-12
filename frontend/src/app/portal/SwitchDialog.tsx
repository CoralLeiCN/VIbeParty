import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import type { SessionSummary } from "../../shared/contracts";
export function SwitchDialog({
  currentTitle,
  nextTitle,
  session,
  busy,
  closing,
  error,
  onConfirm,
  onDismiss,
}: {
  currentTitle: string;
  nextTitle?: string;
  session?: SessionSummary;
  busy: boolean;
  closing: boolean;
  error: string;
  onConfirm: () => void;
  onDismiss: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLElement | null>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!opener.current && document.activeElement instanceof HTMLElement)
      opener.current = document.activeElement;
    dialog?.showModal();
    return () => {
      dialog?.close();
      opener.current?.focus();
    };
  }, []);
  const allowed = session?.can_close;
  return (
    <dialog
      ref={ref}
      className="party-dialog"
      onCancel={(event) => {
        event.preventDefault();
        onDismiss();
      }}
      aria-labelledby="switch-title"
      aria-describedby="switch-description"
    >
      <div className="dialog-icon" aria-hidden="true">
        {closing ? "◷" : "↗"}
      </div>
      <h2 id="switch-title">
        {closing
          ? "Finishing this party"
          : allowed
            ? nextTitle
              ? "Ready for a different game?"
              : "Close this party?"
            : "There’s a party in progress"}
      </h2>
      <p id="switch-description">
        {closing
          ? "We’re waiting for the current game to finish cleanup. You can switch once everything has closed safely."
          : allowed
            ? `Closing ${currentTitle} clears its replay and player list. Everyone will need to rejoin${nextTitle ? ` for ${nextTitle}` : " the next party"}.`
            : `${currentTitle} is already active on this laptop. Ask its host to close the party before starting a different game.`}
      </p>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="dialog-actions">
        {allowed ? (
          <button
            className="button primary"
            onClick={onConfirm}
            disabled={busy}
          >
            {busy
              ? "Closing party…"
              : closing
                ? "Check cleanup"
                : nextTitle
                  ? `Close & switch`
                  : "Close party"}
          </button>
        ) : (
          <Link
            className="button primary"
            to={session?.continuation_url || "/join"}
          >
            {session ? "Continue party" : "Join current party"}
          </Link>
        )}
        <button className="button secondary" onClick={onDismiss}>
          {closing || !allowed ? "Back to games" : "Keep this party"}
        </button>
      </div>
      <p className="dialog-note">
        {closing
          ? "Starting another game stays blocked until cleanup is confirmed."
          : "Going back to games keeps the party running."}
      </p>
    </dialog>
  );
}
