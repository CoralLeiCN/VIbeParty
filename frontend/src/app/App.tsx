import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { GameRoute as WordByWord } from "../games/word-by-word";
import { GameRoute as PromptRoyale } from "../games/prompt-royale";
import { GameRoute as ReversePrompt } from "../games/reverse-prompt";
import { Portal } from "./portal/Portal";
import { Join } from "./portal/Join";
import { RouteRecovery, RouteFocus, NotFound } from "./RouteRecovery";
const games = {
  "word-by-word": WordByWord,
  "prompt-royale": PromptRoyale,
  "reverse-prompt": ReversePrompt,
};
export function App() {
  return (
    <BrowserRouter>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <div id="main-content" tabIndex={-1}>
        <RouteRecovery>
          <RouteFocus />
          <Routes>
            <Route path="/" element={<Portal />} />
            <Route path="/join" element={<Join />} />
            <Route
              path="/host"
              element={<Navigate to="/games/word-by-word/host" replace />}
            />
            {Object.entries(games).flatMap(([id, Game]) =>
              ["host", "join"].map((entry) => (
                <Route
                  key={`${id}/${entry}`}
                  path={`/games/${id}/${entry}`}
                  element={<Game entry={entry as "host" | "join"} />}
                />
              )),
            )}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </RouteRecovery>
      </div>
    </BrowserRouter>
  );
}
