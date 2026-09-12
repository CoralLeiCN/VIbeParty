export type GameId = "word-by-word" | "prompt-royale" | "reverse-prompt";
export type GameEntryProps = { entry: "host" | "join" };
export type PartySummary = {
  game_id: GameId;
  status: "starting" | "active" | "closing";
};
export type SessionSummary = {
  game_id: GameId;
  role: "host" | "player";
  continuation_url: string;
  can_close: boolean;
};
export type SessionDiscovery =
  | { status: "authenticated"; session: SessionSummary; party: PartySummary }
  | {
      status: "anonymous";
      reason: "no_session" | "expired";
      party: PartySummary | null;
    };
export type GameAvailability = { games: { id: GameId; available: boolean }[] };
