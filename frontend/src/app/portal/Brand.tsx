import { Link } from "react-router-dom";
export function Brand() {
  return (
    <Link className="brand" to="/" aria-label="VibeParty home">
      <svg viewBox="0 0 36 36" aria-hidden="true">
        <path
          d="M18 1 22 12 33 7 27 18 35 24 23 25 21 36 15 26 4 31 9 20 1 13 13 12Z"
          fill="currentColor"
        />
        <circle cx="16" cy="17" r="1.5" fill="#fbf8ef" />
        <circle cx="23" cy="17" r="1.5" fill="#fbf8ef" />
        <path
          d="M16 22q4 4 7-1"
          fill="none"
          stroke="#fbf8ef"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
      <span>
        vibe<span className="brand-light">party</span>
        <span className="brand-dot">.</span>
      </span>
    </Link>
  );
}
