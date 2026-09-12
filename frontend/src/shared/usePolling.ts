import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "./api";

export function usePolling<T>(url: string | null, intervalMs = 1000) {
  const [state, setState] = useState<{
    data?: T;
    error?: Error;
    loading: boolean;
  }>({ loading: true });
  const lastUrl = useRef<string | null>(null);
  const [revision, setRevision] = useState(0);
  const retry = useCallback(() => setRevision((value) => value + 1), []);
  useEffect(() => {
    if (!url) return;
    let stopped = false;
    let busy = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let controller: AbortController | undefined;
    const sameUrl = lastUrl.current === url;
    setState((previous) =>
      sameUrl ? { ...previous, loading: true } : { loading: true },
    );
    lastUrl.current = url;
    const poll = async () => {
      if (stopped || busy) return;
      if (document.hidden) {
        timer = setTimeout(poll, intervalMs);
        return;
      }
      clearTimeout(timer);
      busy = true;
      controller = new AbortController();
      const requestTimeout = setTimeout(() => controller?.abort(), 10000);
      try {
        const data = await apiFetch<T>(url, { signal: controller.signal });
        if (!stopped) setState({ data, loading: false });
      } catch (error) {
        if (!stopped)
          setState((previous) => ({
            ...previous,
            error: error instanceof Error ? error : new Error("Reconnecting…"),
            loading: false,
          }));
      } finally {
        clearTimeout(requestTimeout);
        busy = false;
        if (!stopped) timer = setTimeout(poll, intervalMs);
      }
    };
    const wake = () => {
      if (!document.hidden) void poll();
    };
    void poll();
    window.addEventListener("online", wake);
    window.addEventListener("focus", wake);
    document.addEventListener("visibilitychange", wake);
    return () => {
      stopped = true;
      clearTimeout(timer);
      controller?.abort();
      window.removeEventListener("online", wake);
      window.removeEventListener("focus", wake);
      document.removeEventListener("visibilitychange", wake);
    };
  }, [url, intervalMs, revision]);
  return { ...state, retry };
}
