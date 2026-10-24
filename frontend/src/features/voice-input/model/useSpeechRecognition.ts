import { useCallback, useRef, useState } from "react";

import { canFallBackToServer, markBrowserSpeechBroken, resolveEngine, type SpeechEngine } from "@/shared/lib/speechEngine";
import type { SpeechOptions, SpeechRecognitionApi } from "./types";
import { useBrowserSpeech } from "./useBrowserSpeech";
import { useServerSpeech } from "./useServerSpeech";

/**
 * Хук распознавания речи для кнопки микрофона. Движок выбирается автоматически (см. shared/lib/speechEngine):
 * браузерный Web Speech API, а в Яндекс Браузере и других, где он не работает, — запись + распознавание
 * на сервере. Если браузерный движок получил ошибку `network`, переключаемся на серверный и сразу
 * продолжаем запись, чтобы пользователю не пришлось нажимать ещё раз.
 */
export function useSpeechRecognition(options: SpeechOptions = {}): SpeechRecognitionApi {
  const [engine, setEngine] = useState<SpeechEngine>(resolveEngine);
  const serverRef = useRef<SpeechRecognitionApi | null>(null);

  const browser = useBrowserSpeech({
    ...options,
    onNetworkError: useCallback(() => {
      if (!canFallBackToServer()) return false;
      markBrowserSpeechBroken();
      setEngine("server");
      // Запись, начатая нажатием пользователя, продолжается уже через сервер
      queueMicrotask(() => serverRef.current?.start());
      return true;
    }, []),
  });
  const server = useServerSpeech(options);
  serverRef.current = server;

  return engine === "server" ? server : browser;
}
