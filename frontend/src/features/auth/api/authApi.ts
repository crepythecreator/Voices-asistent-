import type { User } from "@/entities/user";
import { api } from "@/shared/api";

export interface OAuthProviderInfo {
  id: "yandex" | "google";
  title: string;
  /** false — на сервере нет ключей этого провайдера. */
  configured: boolean;
}

export const authApi = {
  me: () => api<User>("/auth/me"),
  login: (email: string, password: string) =>
    api<User>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  register: (email: string, password: string, name: string) =>
    api<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, password, name }) }),
  logout: () => api<void>("/auth/logout", { method: "POST" }),
  providers: () => api<OAuthProviderInfo[]>("/auth/providers"),
};

/** Вход/регистрация через провайдера — уводит браузер на его страницу согласия. */
export function oauthLoginUrl(provider: string, next?: string): string {
  const params = next ? `?${new URLSearchParams({ next })}` : "";
  return `/api/auth/${provider}/login${params}`;
}
