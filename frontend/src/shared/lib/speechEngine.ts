import { STT_ENGINE } from "@/shared/config";

// Выбор движка распознавания речи.
//
// Web Speech API в Chromium отправляет звук на серверы Google. В Яндекс Браузере (и Brave, Arc)
// у сборки нет доступа к этому сервису: запуск проходит, а в конце приходит ошибка `network`.
// Локальный режим (processLocally) там тоже не работает — языковой пакет не скачивается.
// Поэтому в таких браузерах записываем звук сами и распознаём на сервере.

export type SpeechEngine = "browser" | "server";

const BROKEN_KEY = "stt-browser-broken";
// Через сутки пробуем браузерное распознавание снова: сеть могла вернуться, браузер — обновиться
const BROKEN_TTL_MS = 24 * 60 * 60 * 1000;

export const isYandexBrowser = () => typeof navigator !== "undefined" && /YaBrowser/i.test(navigator.userAgent);

export const browserSpeechSupported = () =>
  typeof window !== "undefined" && Boolean(window.SpeechRecognition ?? window.webkitSpeechRecognition);

export const serverSpeechSupported = () =>
  typeof window !== "undefined" && "mediaDevices" in navigator && "AudioWorkletNode" in window;

function browserKnownBroken(): boolean {
  try {
    const at = Number(localStorage.getItem(BROKEN_KEY));
    return at > 0 && Date.now() - at < BROKEN_TTL_MS;
  } catch {
    return false;
  }
}

/** Запоминает, что браузерное распознавание не работает (пришла ошибка `network`). */
export function markBrowserSpeechBroken() {
  try {
    localStorage.setItem(BROKEN_KEY, String(Date.now()));
  } catch {
    /* localStorage недоступен — переключимся только на эту сессию */
  }
}

/** Можно ли при ошибке `network` переключиться на серверное распознавание. */
export const canFallBackToServer = () => STT_ENGINE === "auto" && serverSpeechSupported();

export function resolveEngine(): SpeechEngine {
  if (STT_ENGINE === "browser") return "browser";
  if (STT_ENGINE === "server") return "server";
  if (!serverSpeechSupported()) return "browser";
  if (!browserSpeechSupported() || isYandexBrowser() || browserKnownBroken()) return "server";
  return "browser";
}

/** Умеет ли этот браузер хоть как-то принимать голос. */
export function speechInputSupported(): boolean {
  return resolveEngine() === "server" ? serverSpeechSupported() : browserSpeechSupported();
}
