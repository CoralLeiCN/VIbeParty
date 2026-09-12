import type { ComponentPropsWithRef } from "react";

export const ROOM_CODE_FORMAT_MESSAGE = "Enter a 4-digit room code.";
export const ROOM_CODE_UNAVAILABLE_MESSAGE =
  "That party isn't available. Check the code with your host.";

// Pure validation is part of this shared input contract; it has no refresh state.
// eslint-disable-next-line react-refresh/only-export-components
export function normalizeRoomCode(value: string): string | null {
  const trimmed = value.trim();
  return /^[0-9]{4}$/.test(trimmed) ? trimmed : null;
}

type Props = Omit<
  ComponentPropsWithRef<"input">,
  "type" | "inputMode" | "pattern" | "maxLength"
>;

// Keep the game's label/layout. Join forms use noValidate and normalizeRoomCode
// before sending, allowing surrounding whitespace and one consistent error.
export function RoomCodeInput(props: Props) {
  return (
    <input
      {...props}
      type="text"
      inputMode="numeric"
      pattern="[0-9]{4}"
      autoCapitalize="none"
      autoComplete="off"
      spellCheck={false}
      placeholder="0042"
    />
  );
}
