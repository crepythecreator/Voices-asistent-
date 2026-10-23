export type ProviderId = "yandex" | "google";

/** Подключённый к аккаунту Яндекс/Google и его календарь. */
export interface Connection {
  provider: ProviderId;
  title: string;
  connected: boolean;
  email?: string | null;
  /** Пользователь выдал доступ к календарю. */
  calendarAccess: boolean;
  /** События ассистента выгружаются в этот календарь. */
  syncEnabled: boolean;
  calendarStatus?: "pending" | "ok" | "error" | null;
  calendarError?: string | null;
}
