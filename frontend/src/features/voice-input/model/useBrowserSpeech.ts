import { useCallback, useEffect, useRef, useState } from "react";

import type { SpeechOptions, SpeechRecognitionApi } from "./types";

const ERROR_MESSAGES: Record<string, string> = {
  "not-allowed": "Нет доступа к микрофону. Разрешите его в настройках браузера.",
  "service-not-allowed": "Распознавание речи запрещено в этом браузере.",
  "no-speech": "Не удалось расслышать речь. Попробуйте ещё раз.",
  "audio-capture": "Микрофон не найден.",
  // Chrome отправляет звук на серверы Google. Ошибка значит, что они недоступны
  // или браузер собран без ключей Google (Яндекс Браузер, Brave, Arc, Chromium).
  network:
    "Браузер не может связаться со своим сервисом распознавания. Попробуйте Google Chrome или включите серверное распознавание.",
};

/**
 * Движок на браузерном Web Speech API.
 * Надёжно работает в Google Chrome и Safari; в Firefox API нет.
 */
export function useBrowserSpeech({ lang = "ru-RU", onFinal }: SpeechOptions = {}): SpeechRecognitionApi {
  const Ctor = typeof window !== "undefined" ? (window.SpeechRecognition ?? window.webkitSpeechRecognition) : undefined;
  const supported = Boolean(Ctor);

  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const finalRef = useRef("");
  const onFinalRef = useRef(onFinal);
  onFinalRef.current = onFinal;

  const start = useCallback(() => {
    if (!Ctor || recognitionRef.current) return;

    const rec = new Ctor();
    rec.lang = lang;
    rec.continuous = true;
    rec.interimResults = true;

    finalRef.current = "";
    setTranscript("");
    setError(null);

    rec.onresult = (e) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) finalRef.current += r[0].transcript;
        else interim += r[0].transcript;
      }
      setTranscript((finalRef.current + interim).trim());
    };
    rec.onerror = (e) => {
      if (e.error === "aborted") return;
      setError(ERROR_MESSAGES[e.error] ?? `Ошибка распознавания: ${e.error}`);
    };
    rec.onend = () => {
      recognitionRef.current = null;
      setListening(false);
      const text = finalRef.current.trim();
      if (text) onFinalRef.current?.(text);
    };

    recognitionRef.current = rec;
    rec.start();
    setListening(true);
  }, [Ctor, lang]);

  const stop = useCallback(() => recognitionRef.current?.stop(), []);

  const toggle = useCallback(() => (recognitionRef.current ? stop() : start()), [start, stop]);

  useEffect(() => () => recognitionRef.current?.abort(), []);

  return { supported, listening, processing: false, transcript, error, start, stop, toggle };
}
