/** Copy from a user gesture on both localhost and the trusted HTTP LAN origin. */
export async function copyText(text: string): Promise<boolean> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      /* Try the local HTTP fallback. */
    }
  }
  const previous =
    document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
  const field = document.createElement("textarea");
  field.value = text;
  field.readOnly = true;
  field.style.cssText = "position:fixed;left:-9999px;top:0;opacity:0";
  document.body.append(field);
  field.select();
  field.setSelectionRange(0, text.length);
  try {
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    field.remove();
    previous?.focus({ preventScroll: true });
  }
}
