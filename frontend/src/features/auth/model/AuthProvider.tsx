import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import type { User } from "@/entities/user";
import { api, setUnauthorizedHandler } from "@/shared/api";
import { USE_MOCKS } from "@/shared/config";

// Авторизация через Яндекс OAuth — на бэкенде:
//   GET  /auth/yandex/login?next=/path — редирект на oauth.yandex.ru (next сохраняется в state)
//   GET  /auth/yandex/callback         — обмен кода, сессионная cookie, редирект на фронт:
//                                        успех → next, ошибка → /login?error=<код>
//   GET  /auth/me                      — текущий пользователь (401, если не вошёл)
//   POST /auth/logout
// В режиме моков вход подставляет тестового пользователя и запоминает его в localStorage.

const LOGIN_URL = "/api/auth/yandex/login";
const MOCK_USER_KEY = "mock-user";
const MOCK_USER: User = { id: "mock", name: "Тестовый пользователь", email: "test@yandex.ru" };

interface AuthState {
  user: User | null;
  /** Идёт проверка сессии — до её окончания нельзя решать, пускать ли на защищённые страницы. */
  loading: boolean;
  /** Уводит на вход через Яндекс; после входа бэкенд вернёт пользователя на `next`. */
  login: (next?: string) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

function readMockUser(): User | null {
  try {
    return localStorage.getItem(MOCK_USER_KEY) ? MOCK_USER : null;
  } catch {
    return null;
  }
}

function writeMockUser(signedIn: boolean) {
  try {
    if (signedIn) localStorage.setItem(MOCK_USER_KEY, "1");
    else localStorage.removeItem(MOCK_USER_KEY);
  } catch {
    /* localStorage недоступен */
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => (USE_MOCKS ? readMockUser() : null));
  const [loading, setLoading] = useState(!USE_MOCKS);

  useEffect(() => {
    if (USE_MOCKS) return;
    // Любой 401 от API — сессия кончилась: защищённые роуты уведут на /login
    setUnauthorizedHandler(() => setUser(null));
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback((next?: string) => {
    if (USE_MOCKS) {
      writeMockUser(true);
      setUser(MOCK_USER);
      return;
    }
    const params = next ? `?${new URLSearchParams({ next })}` : "";
    window.location.href = `${LOGIN_URL}${params}`;
  }, []);

  const logout = useCallback(async () => {
    if (USE_MOCKS) writeMockUser(false);
    else await api("/auth/logout", { method: "POST" }).catch(() => {});
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, loading, login, logout }), [user, loading, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
