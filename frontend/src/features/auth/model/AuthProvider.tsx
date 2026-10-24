import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import type { User } from "@/entities/user";
import { setUnauthorizedHandler } from "@/shared/api";
import { USE_MOCKS } from "@/shared/config";
import { authApi, oauthLoginUrl } from "../api/authApi";

// Сессия — httpOnly cookie, её ставит бэкенд после входа по паролю или через Яндекс/Google.
// В режиме моков вход подставляет тестового пользователя и запоминает его в localStorage.

const MOCK_USER_KEY = "mock-user";
const MOCK_USER: User = {
  id: "mock",
  name: "Тестовый пользователь",
  email: "test@example.com",
  hasPassword: true,
  confirmMode: "confirm",
};

interface AuthState {
  user: User | null;
  /** Идёт проверка сессии — до её окончания нельзя решать, пускать ли на защищённые страницы. */
  loading: boolean;
  loginWithPassword: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  /** Уводит на вход через провайдера; после входа бэкенд вернёт пользователя на `next`. */
  loginWithProvider: (provider: string, next?: string) => void;
  logout: () => Promise<void>;
  /** Перечитать профиль (после смены пароля, подключения аккаунта). */
  refresh: () => Promise<void>;
  /** Обновить профиль ответом сервера (например, после смены настроек). */
  setUser: (user: User) => void;
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

  const refresh = useCallback(async () => {
    if (USE_MOCKS) return;
    setUser(await authApi.me().catch(() => null));
  }, []);

  useEffect(() => {
    if (USE_MOCKS) return;
    // Любой 401 от API — сессия кончилась: защищённые роуты уведут на /login
    setUnauthorizedHandler(() => setUser(null));
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  const mockSignIn = useCallback(() => {
    writeMockUser(true);
    setUser(MOCK_USER);
  }, []);

  const loginWithPassword = useCallback(
    async (email: string, password: string) => {
      if (USE_MOCKS) return mockSignIn();
      setUser(await authApi.login(email, password));
    },
    [mockSignIn],
  );

  const register = useCallback(
    async (email: string, password: string, name: string) => {
      if (USE_MOCKS) return mockSignIn();
      setUser(await authApi.register(email, password, name));
    },
    [mockSignIn],
  );

  const loginWithProvider = useCallback(
    (provider: string, next?: string) => {
      if (USE_MOCKS) return mockSignIn();
      window.location.href = oauthLoginUrl(provider, next);
    },
    [mockSignIn],
  );

  const logout = useCallback(async () => {
    if (USE_MOCKS) writeMockUser(false);
    else await authApi.logout().catch(() => {});
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, loginWithPassword, register, loginWithProvider, logout, refresh, setUser }),
    [user, loading, loginWithPassword, register, loginWithProvider, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
