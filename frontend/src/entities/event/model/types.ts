export type EventKind = "meeting" | "reminder" | "task";

export type EventSyncStatus = "pending" | "synced" | "error" | "disabled";

export interface CalendarEvent {
  id: string;
  title: string;
  kind: EventKind;
  start: string; // ISO
  end?: string | null; // ISO
  description?: string | null;
  /** assistant — событие ассистента; yandex/google — из других календарей пользователя (только чтение). */
  source: "assistant" | "yandex" | "google";
  readonly: boolean;
  syncStatus?: EventSyncStatus | null;
  calendarName?: string | null;
}
