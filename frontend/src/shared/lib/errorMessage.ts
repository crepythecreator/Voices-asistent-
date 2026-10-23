import { ApiError } from "@/shared/api";

/** Текст ошибки для формы: сообщение бэкенда (если оно человеческое) или общий текст. */
export function errorMessage(e: unknown, fallback = "Не получилось. Попробуйте ещё раз."): string {
  if (e instanceof ApiError) {
    if (e.status === 422) return "Проверьте правильность заполнения полей";
    if (e.status >= 500) return "Сервер недоступен. Попробуйте позже.";
    if (e.message && !e.message.startsWith("{") && !e.message.startsWith("[")) return e.message;
  }
  return fallback;
}
