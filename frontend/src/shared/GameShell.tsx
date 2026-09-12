import type { ReactNode } from "react";
import { Link } from "react-router-dom";
export function GameShell({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <main className="game-shell">
      <Link className="back-link" to="/">
        ← Back to games
      </Link>
      <h1>{title}</h1>
      {children}
    </main>
  );
}
