const adjectives = [
  "Sunny",
  "Cosmic",
  "Happy",
  "Dancing",
  "Merry",
  "Lucky",
  "Curious",
  "Brave",
];
const animals = [
  "Otter",
  "Fox",
  "Panda",
  "Penguin",
  "Owl",
  "Tiger",
  "Koala",
  "Badger",
];

// Lazy useState initializer: polling and form errors must never replace edits.
export function randomPlayerName(): string {
  const pick = (words: string[]) =>
    words[Math.floor(Math.random() * words.length)];
  return `${pick(adjectives)} ${pick(animals)}`;
}
