import type { Connection, ProviderId } from "@/entities/connection";
import { api, delay } from "@/shared/api";
import { routes, USE_MOCKS } from "@/shared/config";

/** Подключение аккаунта с доступом к календарю — уводит на страницу согласия провайдера. */
export function connectUrl(provider: ProviderId): string {
  return `/api/auth/${provider}/connect?${new URLSearchParams({ next: routes.settings })}`;
}

export async function setSync(connection: Connection, enabled: boolean): Promise<Connection> {
  if (USE_MOCKS) {
    await delay(200);
    return { ...connection, syncEnabled: enabled };
  }
  return api<Connection>(`/account/connections/${connection.provider}`, {
    method: "PATCH",
    body: JSON.stringify({ syncEnabled: enabled }),
  });
}

export async function disconnect(provider: ProviderId): Promise<void> {
  if (USE_MOCKS) {
    await delay(200);
    return;
  }
  await api<void>(`/account/connections/${provider}`, { method: "DELETE" });
}
