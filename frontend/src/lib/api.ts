// Local development and Vercel use the /api proxy; direct API origins may include /api.
export function normalizeApiBase(rawBase?: string): string {
  const value = (rawBase ?? "").trim();
  if (!value) return "";
  return value.replace(/\/+$/, "").replace(/\/api$/i, "");
}

export function apiUrl(path: string, baseOverride?: string): string {
  const base = normalizeApiBase(baseOverride ?? import.meta.env.VITE_API_BASE_URL);
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}/api${normalizedPath}`;
}

// Fields are declared, not constructor parameter properties: tsconfig sets
// erasableSyntaxOnly, which rejects `constructor(readonly status: number)`.
export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    super(`request failed with ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export class ApiNetworkError extends Error {
  readonly reason: "timeout" | "network";

  constructor(reason: "timeout" | "network") {
    super(reason === "timeout" ? "The server did not respond in time" : "Could not reach the server");
    this.name = "ApiNetworkError";
    this.reason = reason;
  }
}

async function fetchWithTimeout(url: string, options: RequestInit, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    throw new ApiNetworkError(error instanceof DOMException && error.name === "AbortError" ? "timeout" : "network");
  } finally {
    clearTimeout(timeout);
  }
}

type JsonBody = unknown;

async function request<T>(method: string, path: string, body?: JsonBody): Promise<T> {
  // Auth rides the httpOnly session cookie automatically — never add auth headers here.
  const options: RequestInit = {
    method,
    credentials: "include",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  };
  const isLogin = method === "POST" && path === "/auth/login";
  let res: Response;
  try {
    res = await fetchWithTimeout(apiUrl(path), options, isLogin ? 40000 : 30000);
  } catch (error) {
    if (!isLogin || !(error instanceof ApiNetworkError)) throw error;
    res = await fetchWithTimeout(apiUrl(path), options, 60000);
  }
  if (isLogin && [502, 503, 504].includes(res.status)) {
    res = await fetchWithTimeout(apiUrl(path), options, 60000);
  }

  // FastAPI reports request-validation failures as 422 with a {detail: [...]} body.
  if (!res.ok) {
    const errBody = await res.json().catch(() => null);
    throw new ApiError(res.status, errBody);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// The response type is yours to declare: nothing infers across the Python boundary, so a
// TS interface here mirrors the endpoint's Pydantic model by hand — keep the two in sync.
export const apiGet = <T>(path: string) => request<T>("GET", path);
export const apiPost = <T>(path: string, body?: JsonBody) => request<T>("POST", path, body ?? null);
export async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetchWithTimeout(apiUrl(path), {
    method: "POST",
    credentials: "include",
    body: formData,
  }, 90000);

  if (!res.ok) {
    const errBody = await res.json().catch(() => null);
    throw new ApiError(res.status, errBody);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
export const apiPut = <T>(path: string, body?: JsonBody) => request<T>("PUT", path, body ?? null);
export const apiPatch = <T>(path: string, body?: JsonBody) =>
  request<T>("PATCH", path, body ?? null);
export const apiDelete = <T>(path: string) => request<T>("DELETE", path);
