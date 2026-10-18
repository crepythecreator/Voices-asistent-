// Единая точка чтения переменных окружения.

/** Работа без бэкенда на моках (тестовый пользователь, фиктивные ответы). Включить: VITE_USE_MOCKS=true */
export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "true";

/**
 * Движок распознавания речи:
 *   browser (по умолчанию) — Web Speech API браузера
 *   server                 — запись в браузере, распознавание на бэкенде через Yandex SpeechKit
 */
export const STT_ENGINE: "browser" | "server" = import.meta.env.VITE_STT_ENGINE === "server" ? "server" : "browser";
