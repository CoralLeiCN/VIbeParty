import { usePolling } from "./usePolling";

export function useHostAccess(enabled: boolean) {
  const config = usePolling<{ local_mode: boolean }>(
    enabled ? "/api/config" : null,
    10000,
  );
  return {
    ...config,
    localMode: config.data?.local_mode === true,
    ready: !enabled || Boolean(config.data && !config.error),
  };
}
