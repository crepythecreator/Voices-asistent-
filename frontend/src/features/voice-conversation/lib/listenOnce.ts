// Одна фраза через браузерный Web Speech API. С continuous=false Chrome сам завершает
// распознавание после паузы — это и есть определение конца фразы.

const ERRORS: Record<string, string> = {
  "not-allowed": "Нет доступа к микрофону. Разрешите его в настройках браузера.",
  "service-not-allowed": "Распознавание речи запрещено в этом браузере.",
  "audio-capture": "Микрофон не найден.",
  network:
    "Браузер не может связаться со своим сервисом распознавания. Для беседы нужен Google Chrome или Safari.",
};

export class ListenError extends Error {}

export function speechRecognitionSupported(): boolean {
  return typeof window !== "undefined" && Boolean(window.SpeechRecognition ?? window.webkitSpeechRecognition);
}

interface Options {
  lang?: string;
  onInterim?: (text: string) => void;
  signal?: AbortSignal;
}

/** Слушает одну фразу. Пустая строка — пользователь ничего не сказал (или прервали). */
export function listenOnce({ lang = "ru-RU", onInterim, signal }: Options = {}): Promise<string> {
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
      reject(new ListenError(ERRORS[e.error] ?? `Ошибка распознавания: ${e.error}`));
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
