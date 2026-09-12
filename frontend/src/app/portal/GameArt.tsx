import type { GameId } from "../../shared/contracts";
export function GameArt({ game }: { game: GameId }) {
  return (
    <div className={`game-art ${game}`} aria-hidden="true">
      {game === "word-by-word" ? (
        <>
          <div className="word-slip word-one">a forest</div>
          <div className="word-slip word-two">
            a dancing fox <span>✳</span>
          </div>
          <div className="word-slip word-three">…in space!</div>
          <span className="art-spark">✦</span>
        </>
      ) : game === "prompt-royale" ? (
        <>
          <div className="arena-tile tile-one">✶</div>
          <div className="arena-tile tile-two">✺</div>
          <div className="vote-sticker">BEST IN SHOW ↗</div>
          <span className="art-spark">✧</span>
        </>
      ) : (
        <>
          <div className="relay-bubble bubble-one">
            an idea<span>✳</span>
          </div>
          <div className="relay-arrow">↝</div>
          <div className="relay-bubble bubble-two">
            a wild guess<span>?</span>
          </div>
        </>
      )}
    </div>
  );
}
