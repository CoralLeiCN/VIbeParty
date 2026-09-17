import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { catalog } from "../catalog";
import { apiPost } from "../../shared/api";
import { usePolling } from "../../shared/usePolling";
import type {
  GameAvailability,
  GameId,
  SessionDiscovery,
} from "../../shared/contracts";
import { Brand } from "./Brand";
import { GameArt } from "./GameArt";
import { SwitchDialog } from "./SwitchDialog";

const intentKey = "vibeparty.pending-switch";
function pendingTarget(): GameId | undefined {
  const value = sessionStorage.getItem(intentKey);
  return catalog.some((game) => game.id === value)
    ? (value as GameId)
    : undefined;
}

export function Portal() {
  const discovery = usePolling<SessionDiscovery>("/api/session", 3000);
  const availability = usePolling<GameAvailability>("/api/games", 10000);
  const [dialog, setDialog] = useState<{ target?: GameId; source?: GameId }>();
  const [closeBusy, setCloseBusy] = useState(false);
  const [closeError, setCloseError] = useState("");
  const [waiting, setWaiting] = useState(() =>
    Boolean(sessionStorage.getItem(intentKey)),
  );
  const navigate = useNavigate();
  const data = discovery.data;
  const party = data?.party;
  const session = data?.status === "authenticated" ? data.session : undefined;
  const current = catalog.find((game) => game.id === party?.game_id);
  const closing = party?.status === "closing";
  const reconnecting = Boolean(discovery.error);
  useEffect(() => {
    if (!waiting || !data || discovery.error || data.party) return;
    const target = pendingTarget();
    sessionStorage.removeItem(intentKey);
    setWaiting(false);
    setDialog(undefined);
    if (target) navigate(`/games/${target}/host`);
  }, [data, discovery.error, waiting, navigate]);

  useEffect(() => {
    if (
      dialog &&
      data &&
      !discovery.error &&
      !waiting &&
      data.party?.game_id !== dialog.source
    )
      setDialog(undefined);
  }, [dialog, data, discovery.error, waiting]);

  function launch(gameId: GameId) {
    if (session?.game_id === gameId) {
      navigate(session.continuation_url);
      return;
    }
    if ((party && party.game_id !== gameId) || closing) {
      setCloseError("");
      setDialog({ target: gameId, source: party?.game_id });
      return;
    }
    navigate(`/games/${gameId}/host`);
  }
  async function closeParty() {
    setCloseBusy(true);
    setCloseError("");
    try {
      const result = await apiPost<{
        status: "closed" | "closing";
        message: string;
      }>("/api/party/close", { game_id: dialog?.source || party?.game_id });
      const target = dialog?.target || pendingTarget();
      if (result.status === "closed") {
        sessionStorage.removeItem(intentKey);
        setWaiting(false);
        setDialog(undefined);
        discovery.retry();
        if (target) navigate(`/games/${target}/host`);
      } else {
        sessionStorage.setItem(intentKey, target || "close");
        setWaiting(true);
        discovery.retry();
        setCloseError(result.message);
      }
    } catch (error) {
      setCloseError(
        error instanceof Error
          ? error.message
          : "Could not close the party. Please try again.",
      );
      discovery.retry();
    } finally {
      setCloseBusy(false);
    }
  }
  return (
    <div className="portal-page">
      <header className="site-header">
        <Brand />
        <div className="header-right">
          <span className="local-label">
            <i /> Together in the same room
          </span>
          <Link className="button small dark" to="/join">
            Join party <span aria-hidden="true">↗</span>
          </Link>
        </div>
      </header>
      <main className="portal-main">
        {reconnecting ? (
          <aside className="session-notice reconnecting" role="status">
            <div>
              <strong>Reconnecting to the laptop…</strong>
              <p>
                Your party stays where you left it. Check your connection and
                try again.
              </p>
            </div>
            <button
              className="button secondary small"
              onClick={discovery.retry}
            >
              Retry connection
            </button>
          </aside>
        ) : session ? (
          <aside className="session-notice">
            <div className="session-icon" aria-hidden="true">
              {closing ? "◷" : "↩"}
            </div>
            <div className="session-copy">
              <span className="eyebrow">
                {closing ? "FINISHING UP" : "WELCOME BACK"}
              </span>
              <strong>
                {closing
                  ? "Finishing the previous session"
                  : `${current?.title} is waiting for you`}
              </strong>
              <p>
                {closing
                  ? "Another game can start once cleanup is confirmed."
                  : `${session.role === "host" ? "You’re the host" : "You’re in the party"}. Your place is saved while the party is running.`}
              </p>
            </div>
            <div className="session-actions">
              <Link
                className="button primary small"
                to={session.continuation_url}
              >
                Continue party <span aria-hidden="true">→</span>
              </Link>
              {session.can_close && (
                <button
                  className="text-button"
                  onClick={() => {
                    setCloseError("");
                    setDialog({ source: party?.game_id });
                  }}
                >
                  {closing ? "Check cleanup" : "Close party"}
                </button>
              )}
            </div>
          </aside>
        ) : data?.status === "anonymous" &&
          data.reason === "expired" &&
          !party ? (
          <aside className="session-notice" role="status">
            <div>
              <strong>This party has ended</strong>
              <p>
                Join with a new code, or choose a game to host another party.
              </p>
            </div>
            <Link className="button secondary small" to="/join">
              Join a party
            </Link>
          </aside>
        ) : closing ? (
          <aside className="session-notice" role="status">
            <div>
              <strong>Finishing the previous session</strong>
              <p>
                The host is closing the current party. New games can start after
                cleanup.
              </p>
            </div>
          </aside>
        ) : null}
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy">
            <div className="eyebrow hero-eyebrow">
              <span className="tiny-star" aria-hidden="true">
                ✳
              </span>{" "}
              A LITTLE IMAGINATION. A GREAT NIGHT.
            </div>
            <h1 id="hero-title">
              Good friends.
              <br />
              Wild ideas.
              <br />
              <em>Roll with it.</em>
            </h1>
            <p>
              Turn your collective weirdness into a movie night.
              <br className="desktop-break" /> Pick a game, grab your phones,
              and see what happens.
            </p>
            <a className="choose-link" href="#games">
              Find your next game <span aria-hidden="true">↓</span>
            </a>
          </div>
          <div className="hero-art" aria-hidden="true">
            <span className="hero-orbit orbit-one" />
            <span className="hero-orbit orbit-two" />
            <div className="hero-ticket">
              <div className="ticket-top">
                VIBEPARTY PICTURES <span>★</span>
              </div>
              <div className="ticket-screen">
                <span className="ticket-sun">✳</span>
                <span className="ticket-hill" />
                <span className="ticket-play">▶</span>
              </div>
              <div className="ticket-bottom">
                A film by all of you.<span>TAKE 01</span>
              </div>
            </div>
            <div className="idea-note">
              what if…
              <br />
              <strong>
                the moon
                <br />
                had a disco?
              </strong>
              <span>✧</span>
            </div>
            <div className="friends-note">
              <span>☺</span>
              <span>☺</span>
              <span>☺</span>
              <strong>better together.</strong>
            </div>
            <span className="hero-spark spark-one">✦</span>
            <span className="hero-spark spark-two">✴</span>
          </div>
        </section>
        <section
          className="games-section"
          id="games"
          aria-labelledby="games-heading"
        >
          <div className="section-heading">
            <div>
              <span className="eyebrow">PICK YOUR KIND OF CHAOS</span>
              <h2 id="games-heading">Three ways to make a night of it.</h2>
            </div>
            <p>No downloads. Just your people.</p>
          </div>
          {availability.error && (
            <p className="inline-notice" role="status">
              Game availability is reconnecting.{" "}
              <button className="text-button" onClick={availability.retry}>
                Try again
              </button>
            </p>
          )}
          <div className="cards">
            {catalog.map((game, index) => {
              const available =
                availability.data?.games.find((item) => item.id === game.id)
                  ?.available === true;
              return (
                <article className={`game-card card-${game.id}`} key={game.id}>
                  <GameArt game={game.id} />
                  <div className="card-body">
                    <div className="card-kicker">
                      <span>
                        0{index + 1} / {game.tag}
                      </span>
                      <span
                        className={`availability ${available ? "ready" : ""}`}
                      >
                        {available ? "Play now" : "In the making"}
                      </span>
                    </div>
                    <h3>{game.title}</h3>
                    <p className="game-description">{game.description}</p>
                    <div className="game-details">
                      <p>
                        <span aria-hidden="true">♧</span>
                        {game.players}
                      </p>
                      <p>
                        <span aria-hidden="true">▱</span>
                        {game.host}
                      </p>
                    </div>
                    <button
                      className="button card-action"
                      disabled={
                        !available ||
                        !data ||
                        reconnecting ||
                        Boolean(availability.error)
                      }
                      onClick={() => launch(game.id)}
                    >
                      {available
                        ? session?.game_id === game.id
                          ? "Continue party"
                          : `Host ${game.title}`
                        : "Getting this game ready"}
                      <span aria-hidden="true">↗</span>
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
        <section className="how-it-works" aria-label="How to play">
          <div className="how-title">
            <span aria-hidden="true">✳</span>
            <h2>
              Less setup.
              <br />
              More play.
            </h2>
          </div>
          <ol>
            <li>
              <span>01</span>
              <div>
                <h3>Pick your game</h3>
                <p>Open a party on the host laptop.</p>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                <h3>Get everyone in</h3>
                <p>Same Wi-Fi. Phones out. Room code in.</p>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <h3>Let the ideas fly</h3>
                <p>Make something none of you saw coming.</p>
              </div>
            </li>
          </ol>
        </section>
        <footer className="site-footer">
          <Brand />
          <p>Made for a room full of good company.</p>
          <span>Local play · Shared memories</span>
        </footer>
      </main>
      {dialog && (
        <SwitchDialog
          currentTitle={current?.title || "the current party"}
          nextTitle={catalog.find((game) => game.id === dialog.target)?.title}
          session={session}
          busy={closeBusy}
          closing={Boolean(closing || waiting)}
          error={closeError}
          onConfirm={() => void closeParty()}
          onDismiss={() => setDialog(undefined)}
          recoveryAvailable={party?.game_id === "word-by-word"}
          onRecovered={discovery.retry}
        />
      )}
    </div>
  );
}
