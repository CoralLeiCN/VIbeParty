import type { useHostAccess } from "./useHostAccess";

export function HostAccessField({
  access,
  id,
  label,
  value,
  onChange,
}: {
  access: ReturnType<typeof useHostAccess>;
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  if (access.error) {
    return (
      <p role="alert">
        Could not load room settings.{" "}
        <button type="button" onClick={access.retry}>
          Try again
        </button>
      </p>
    );
  }
  if (!access.ready) return <p role="status">Loading room settings…</p>;
  if (access.localMode) {
    return (
      <p>
        Local mode · Create a room, then share the join link. No password
        needed.
      </p>
    );
  }
  return (
    <>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="password"
        autoComplete="current-password"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required
      />
    </>
  );
}
