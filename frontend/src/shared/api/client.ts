// Тонкая обёртка над fetch. Все запросы идут через прокси Vite `/api` -> backend.
// credentials: "include" — сессионная cookie после входа через Яндекс.

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

// Вызывается на любой 401 — сессия истекла или пользователь вышел в другой вкладке.
let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

async function errorDetail(res: Response): Promise<string> {
  const text = await res.text().catch(() => "");
  try {
    const detail = (JSON.parse(text) as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  } catch {
    /* не JSON */
  }
  return text || res.statusText;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`/api${path}`, {
    credentials: "include",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });
  if (res.status === 401) unauthorizedHandler?.();
  if (!res.ok) {
    throw new ApiError(res.status, await errorDetail(res));
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));
