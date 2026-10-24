import type { ConfirmMode, User } from "@/entities/user";
import { api, delay } from "@/shared/api";
import { USE_MOCKS } from "@/shared/config";

export async function setConfirmMode(user: User, mode: ConfirmMode): Promise<User> {
  if (USE_MOCKS) {
    await delay(200);
    return { ...user, confirmMode: mode };
  }
  return api<User>("/account/settings", { method: "PATCH", body: JSON.stringify({ confirmMode: mode }) });
}
