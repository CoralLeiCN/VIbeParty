import type { GameId } from "../shared/contracts";
export const catalog: {
  id: GameId;
  title: string;
  description: string;
  players: string;
  host: string;
  tag: string;
}[] = [
  {
    id: "word-by-word",
    title: "Word by Word",
    description: "Secret words. One evolving scene. Everyone creates together.",
    players: "3–4 players",
    host: "Separate laptop host · players join on phones",
    tag: "Create together",
  },
  {
    id: "prompt-royale",
    title: "Prompt Royale",
    description:
      "One topic. Your wildest prompts. Watch the clips and vote for your favorite.",
    players: "1–4 players, including the host",
    host: "The host plays too",
    tag: "Compete & vote",
  },
  {
    id: "reverse-prompt",
    title: "Reverse Prompt",
    description:
      "Pass an idea through videos and descriptions. Can you guess where it started?",
    players: "Exactly 3 players, including the host",
    host: "The host starts the story",
    tag: "Guess the original",
  },
];
