import { useId, useState } from "react";
import type { FormEvent } from "react";
import { apiPost } from "./api";
import { usePolling } from "./usePolling";
import "./host-recovery.css";

type RecoveryOptions =
  | { available: false }
  | { available: true; party_id: string; method: "local_code" | "passcode" };
const endpoint = "/api/games/word-by-word/host/recovery";

export function HostRecovery({ onRecovered }: { onRecovered: () => void }) {
  const options = usePolling<RecoveryOptions>(endpoint, 5000);
  const [openedParty, setOpenedParty] = useState<string>();
  const [credential, setCredential] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const id = useId();
  const data = options.data;
  if (!data?.available) return null;
  const local = data.method === "local_code";

  async function recover(event: FormEvent) {
    event.preventDefault();
    if (!data?.available || busy || options.error) return;
    setBusy(true);
    setError("");
    try {
      await apiPost(endpoint, { party_id: openedParty, credential });
      setCredential("");
      setOpenedParty(undefined);
      onRecovered();
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "Could not recover host access.",
      );
      options.retry();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="host-recovery" aria-label="Host recovery">
      <p>This browser is not recognized as host.</p>
      {!openedParty ? (
        <button
          type="button"
          className="button secondary"
          onClick={() => setOpenedParty(data.party_id)}
        >
          Recover host access
        </button>
      ) : (
        <form onSubmit={(event) => void recover(event)}>
          {local ? (
            <p>
              On the host laptop, open a terminal in the running VibeParty
              project and run{" "}
              <code>uv run python -m scripts.host_recovery</code>. Enter the
              private code shown there.
            </p>
          ) : (
            <p>Enter the host passcode used to open this party.</p>
          )}
          <p>
            Recovery moves host controls to this browser. The party keeps
            running.
          </p>
          <label htmlFor={id}>
            {local ? "Host recovery code" : "Host passcode"}
          </label>
          <input
            id={id}
            type="password"
            autoComplete="off"
            autoCapitalize="none"
            spellCheck={false}
            value={credential}
            onChange={(event) => setCredential(event.target.value)}
            maxLength={200}
            required
            disabled={busy}
          />
          {(error || options.error) && (
            <p role="alert">
              {error || "Could not check this party. Try again."}
            </p>
          )}
          <button
            className="button primary"
            disabled={busy || Boolean(options.error)}
          >
            {busy ? "Recovering…" : "Restore host controls"}
          </button>
          <button
            type="button"
            className="text-button"
            disabled={busy}
            onClick={() => {
              setOpenedParty(undefined);
              setCredential("");
              setError("");
            }}
          >
            Cancel recovery
          </button>
        </form>
      )}
    </section>
  );
}
