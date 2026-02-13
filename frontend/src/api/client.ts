/**
 * API client — typed fetch wrapper with JWT handling.
 *
 * Every endpoint group (auth, requests, initiatives, etc.) builds on
 * this base client. The token is read from the auth Zustand store.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

interface RequestOptions {
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
  headers?: Record<string, string>;
}

class ApiError extends Error {
  status: number;
  detail: string;
  request_id?: string;

  constructor(status: number, detail: string, request_id?: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.request_id = request_id;
  }
}

function getToken(): string | null {
  // Read from localStorage — the auth store persists the token here
  return localStorage.getItem("bb_token");
}

function buildUrl(path: string, params?: Record<string, string | number | boolean | undefined>): string {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

async function request<T>(method: HttpMethod, path: string, options: RequestOptions = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(buildUrl(path, options.params), {
    method,
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    let request_id: string | undefined;
    try {
      const err = await response.json();
      detail = err.detail ?? detail;
      request_id = err.request_id;
    } catch {
      // Response wasn't JSON
    }

    // Auto-logout on 401
    if (response.status === 401) {
      localStorage.removeItem("bb_token");
      window.location.href = "/";
    }

    throw new ApiError(response.status, detail, request_id);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// Convenience methods
export const api = {
  get: <T>(path: string, params?: Record<string, string | number | boolean | undefined>) =>
    request<T>("GET", path, { params }),

  post: <T>(path: string, body?: unknown) =>
    request<T>("POST", path, { body }),

  put: <T>(path: string, body?: unknown) =>
    request<T>("PUT", path, { body }),

  patch: <T>(path: string, body?: unknown) =>
    request<T>("PATCH", path, { body }),

  delete: <T>(path: string) =>
    request<T>("DELETE", path),
};

export { ApiError };
