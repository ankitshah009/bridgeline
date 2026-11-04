// Thin client for the FastAPI backend (proxied by next.config.ts: /api/* -> HOMEBASE_API_URL).
export class ApiError extends Error {
  constructor(message: string, public stage: string = "api", public status = 0) {
    super(message);
  }
}

type ErrorBody = { error?: string; detail?: string; stage?: string } | null;

// T defaults to `any` for call-site convenience; callers that care pass a concrete type.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function api<T = any>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
    ...init,
  });
  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON error page */
  }
  if (!res.ok) {
    const err = data as ErrorBody;
    throw new ApiError(err?.error ?? err?.detail ?? `HTTP ${res.status}`, err?.stage ?? "api", res.status);
  }
  return data as T;
}

export const usd = (n: number | null | undefined) =>
  n == null ? "—" : n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
