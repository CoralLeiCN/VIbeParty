export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public field?: string,
  ) {
    super(message);
  }
}
export async function apiFetch<T>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    credentials: "same-origin",
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({
        code: "request_failed",
        message: "Could not complete the request. Please try again.",
      }));
    throw new ApiError(response.status, error.code, error.message, error.field);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
export function apiPost<T>(url: string, body: unknown = {}): Promise<T> {
  return apiFetch<T>(url, { method: "POST", body: JSON.stringify(body) });
}
