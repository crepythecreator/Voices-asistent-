// Единая точка чтения переменных окружения.

/** Работа без бэкенда на моках (тестовый пользователь, фиктивные ответы). Включить: VITE_USE_MOCKS=true */
export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "true";

export type SttMode = "auto" | "browser" | "server";

/**
 * Движок распознавания речи:
 *   auto (по умолчанию) — браузерный Web Speech API, а где он не работает (Яндекс Браузер) —
 *                          серверное распознавание
 *   browser             — только Web Speech API браузера
 *   server              — запись в браузере, распознавание на бэкенде (Cloud.ru GigaASR / Yandex SpeechKit)
 */
const raw = import.meta.env.VITE_STT_ENGINE;
export const STT_ENGINE: SttMode = raw === "browser" || raw === "server" ? raw : "auto";
