import { useState } from "react";
import { copyText } from "./clipboard";

export function useCopyLink({ retainSuccessOnFailure = false } = {}) {
  const [copied, setCopied] = useState(false);

  async function copyLink(url: string) {
    const success = await copyText(url);
    // Prompt Royale keeps its success label after a later failed copy attempt.
    if (success || !retainSuccessOnFailure) setCopied(success);
    return success;
  }

  return { copyLink, copyLabel: copied ? "Copied!" : "Copy join link" };
}
