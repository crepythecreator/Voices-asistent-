import { api, delay } from "@/shared/api";
import { USE_MOCKS } from "@/shared/config";
import type { Connection } from "../model/types";

export const MOCK_CONNECTIONS: Connection[] = [
  { provider: "yandex", title: "Яндекс ID", connected: false, calendarAccess: false, syncEnabled: false },
  { provider: "google", title: "Google", connected: false, calendarAccess: false, syncEnabled: false },
];

export async function getConnections(): Promise<Connection[]> {
  if (USE_MOCKS) {
    await delay(200);
    return MOCK_CONNECTIONS;
  }
  return api<Connection[]>("/account/connections");
}
