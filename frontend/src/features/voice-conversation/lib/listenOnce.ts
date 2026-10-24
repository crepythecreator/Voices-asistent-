// Одна фраза через браузерный Web Speech API. С continuous=false Chrome сам завершает
// распознавание после паузы — это и есть определение конца фразы.

import { canFallBackToServer, markBrowserSpeechBroken, resolveEngine } from "@/shared/lib/speechEngine";
import { listenOnceServer } from "./listenOnceServer";
import { ListenError, type ListenOptions } from "./listenTypes";

const ERRORS: Record<string, string> = {
  "not-allowed": "Нет доступа к микрофону. Разрешите его в настройках браузера.",
  "service-not-allowed": "Распознавание речи запрещено в этом браузере.",
  "audio-capture": "Микрофон не найден.",
  network: "Браузер не может связаться со своим сервисом распознавания речи.",
};

export { ListenError };

function listenOnceBrowser({ lang = "ru-RU", onInterim, signal }: ListenOptions = {}): Promise<string> {
  const Ctor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
  if (!Ctor) return Promise.reject(new ListenError("Распознавание речи не поддерживается этим браузером."));

  return new Promise((resolve, reject) => {
    const rec = new Ctor();
    rec.lang = lang;
    rec.continuous = false;
    rec.interimResults = true;

    let final = "";
    let failed = false;

    rec.onresult = (e) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) final += r[0].transcript;
        else interim += r[0].transcript;
      }
      onInterim?.((final + interim).trim());
    };
    rec.onerror = (e) => {
      if (e.error === "no-speech" || e.error === "aborted") return; // закончится через onend с пустым текстом
      failed = true;
      reject(new ListenError(ERRORS[e.error] ?? `Ошибка распознавания: ${e.error}`, e.error));
    };
    rec.onend = () => {
      signal?.removeEventListener("abort", abort);
      if (!failed) resolve(final.trim());
    };

    const abort = () => rec.abort();
    signal?.addEventListener("abort", abort, { once: true });
    rec.start();
  });
}

/**
 * Слушает одну фразу. Движок — по настройкам и браузеру (см. speechEngine): Web Speech API или запись
 * с серверным распознаванием. Если браузерный движок ответил `network` (Яндекс Браузер), запоминаем это
 * и дальше работаем через сервер. Пустая строка — пользователь ничего не сказал (или прервали).
 */
export async function listen(options: ListenOptions = {}): Promise<string> {
  if (resolveEngine() === "server") return listenOnceServer(options);
  try {
    return await listenOnceBrowser(options);
  } catch (e) {
    if (e instanceof ListenError && e.code === "network" && canFallBackToServer()) {
      markBrowserSpeechBroken();
      return listenOnceServer(options);
    }
    throw e;
  }
}
