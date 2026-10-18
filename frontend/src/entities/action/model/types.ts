export type ActionType = "create_event" | "update_event" | "delete_event";

export type ActionStatus = "pending" | "applied" | "rejected" | "expired" | "failed";

/** Изменение календаря, предложенное ИИ. Применяется только после подтверждения пользователем. */
export interface ProposedAction {
  id: string;
  type: ActionType;
  summary: string;
  status: ActionStatus;
  error: string | null;
  eventId: string | null;
  expiresAt: string; // ISO
}
