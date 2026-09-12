import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError, apiPost } from "../../shared/api";
import { Brand } from "./Brand";
import {
  RoomCodeInput,
  normalizeRoomCode,
  ROOM_CODE_FORMAT_MESSAGE,
} from "../../shared/RoomCodeInput";
export function Join() {
  const [params] = useSearchParams();
  const initial = params.get("code") || "";
  const [code, setCode] = useState(initial);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(Boolean(initial));
  const navigate = useNavigate();
  const input = useRef<HTMLInputElement>(null);
  function message(error: unknown) {
    return error instanceof ApiError
      ? error.message
      : "We couldn’t reach the laptop. Check your connection and try again.";
  }
  useEffect(() => {
    if (!initial) return;
    const normalized = normalizeRoomCode(initial);
    if (!normalized) {
      setError(ROOM_CODE_FORMAT_MESSAGE);
      setBusy(false);
      return;
    }
    let current = true;
    apiPost<{ join_url: string }>("/api/party/resolve", { code: normalized })
      .then((result) => {
        if (current) navigate(result.join_url, { replace: true });
      })
      .catch((error) => {
        if (current) setError(message(error));
      })
      .finally(() => {
        if (current) setBusy(false);
      });
    return () => {
      current = false;
    };
  }, [initial, navigate]);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    const normalized = normalizeRoomCode(code);
    if (!normalized) {
      setError(ROOM_CODE_FORMAT_MESSAGE);
      input.current?.focus();
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await apiPost<{ join_url: string }>("/api/party/resolve", {
        code: normalized,
      });
      navigate(result.join_url);
    } catch (error) {
      setError(message(error));
      input.current?.focus();
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <header className="site-header">
        <Brand />
        <span className="local-label">
          <i /> Your people are waiting
        </span>
      </header>
      <main className="join-page">
        <Link className="back-link" to="/">
          ← Back to games
        </Link>
        <div className="join-layout">
          <section className="join-intro">
            <span className="eyebrow">THERE’S ROOM FOR YOUR IDEAS</span>
            <h1>
              Good company.
              <br />
              <em>You’re in.</em>
            </h1>
            <p>
              Your next great story starts with a room code. Join your friends
              and see where it goes.
            </p>
            <div className="join-decor" aria-hidden="true">
              ✳ ✧
            </div>
          </section>
          <form
            className="join-form"
            onSubmit={submit}
            aria-busy={busy}
            noValidate
          >
            <h2>Join the party</h2>
            <p>Ask your host for the code on their screen.</p>
            <label htmlFor="room-code">Room code</label>
            <RoomCodeInput
              ref={input}
              id="room-code"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              required
              aria-invalid={Boolean(error)}
              aria-describedby={`code-hint${error ? " join-error" : ""}`}
            />
            <p id="code-hint" className="form-hint">
              Your code takes you to the right game.
            </p>
            {error && (
              <p id="join-error" className="form-error" role="alert">
                {error}
              </p>
            )}
            <button className="button primary" disabled={busy}>
              {busy ? "Finding your party…" : "Find my party"}{" "}
              <span aria-hidden="true">→</span>
            </button>
            <p className="join-help">
              <strong>Playing on your phone?</strong>Connect to the same Wi-Fi
              or hotspot as the laptop, then open the address your host shares.
            </p>
          </form>
        </div>
      </main>
    </>
  );
}
