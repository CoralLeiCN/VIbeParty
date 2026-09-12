import { Component, useEffect, useRef } from "react";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

export class RouteRecovery extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="route-error">
        <h1>Let’s get you back to the party.</h1>
        <p>
          This screen couldn’t load. Refresh to reconnect to your saved session,
          or return to the games.
        </p>
        <button
          className="button primary"
          onClick={() => window.location.reload()}
        >
          Refresh screen
        </button>{" "}
        <a className="button secondary" href="/">
          Back to games
        </a>
      </main>
    );
  }
}
export function RouteFocus() {
  const { pathname } = useLocation();
  const previous = useRef(pathname);
  useEffect(() => {
    if (previous.current === pathname) return;
    previous.current = pathname;
    window.scrollTo(0, 0);
    const heading = document.querySelector("h1");
    if (heading) {
      heading.tabIndex = -1;
      heading.focus({ preventScroll: true });
    }
  }, [pathname]);
  return null;
}
export function NotFound() {
  return (
    <main className="route-error">
      <h1>That page has wandered off.</h1>
      <p>Head back to choose a game, or join your friends with a room code.</p>
      <Link className="button primary" to="/">
        Back to games
      </Link>{" "}
      <Link className="button secondary" to="/join">
        Join party
      </Link>
    </main>
  );
}
