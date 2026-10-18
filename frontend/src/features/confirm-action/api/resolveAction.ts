import type { ProposedAction } from "@/entities/action";
import { api, delay } from "@/shared/api";
import { USE_MOCKS } from "@/shared/config";

export type Decision = "confirm" | "reject";

/** Подтверждение — единственный путь, которым предложение ИИ попадает в календарь. */
export async function resolveAction(action: ProposedAction, decision: Decision): Promise<ProposedAction> {
  if (USE_MOCKS) {
    await delay(400);
    return { ...action, status: decision === "confirm" ? "applied" : "rejected" };
  }
  return api<ProposedAction>(`/actions/${action.id}/${decision}`, { method: "POST" });
}
