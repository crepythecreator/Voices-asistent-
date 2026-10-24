import { useCallback, useEffect, useRef, useState } from "react";

import { isStop } from "../lib/text";
import { ListenError, listenOnce, speechRecognitionSupported } from "../lib/listenOnce";
import { Speaker } from "./speaker";

export type ConversationState = "idle" | "listening" | "thinking" | "speaking";

interface Options {
  /** Обработать фразу пользователя и вернуть текст, который ассистент скажет в ответ. */
  respond: (text: string) => Promise<string>;
}

// Столько раз подряд пользователь промолчал — заканчиваем беседу
const MAX_SILENCES = 3;

/**
 * Режим беседы: слушаем фразу → respond → озвучиваем ответ → снова слушаем.
 * Пока ассистент говорит, микрофон не слушает (иначе он услышит сам себя); перебить — кнопкой.
 */
export function useConversation({ respond }: Options) {
  const [state, setState] = useState<ConversationState>("idle");
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);

  const activeRef = useRef(false);
  const speakerRef = useRef<Speaker | null>(null);
  const listenAbortRef = useRef<AbortController | null>(null);
  const respondRef = useRef(respond);
  respondRef.current = respond;

  const stop = useCallback(() => {
    activeRef.current = false;
    listenAbortRef.current?.abort();
    speakerRef.current?.close();
    speakerRef.current = null;
    setState("idle");
    setTranscript("");
  }, []);

  const speak = useCallback(async (text: string) => {
    if (!activeRef.current || !text) return;
    setState("speaking");
    await speakerRef.current?.speak(text);
  }, []);

  const loop = useCallback(async () => {
    let silences = 0;
    while (activeRef.current) {
      setState("listening");
      setTranscript("");
      const abort = new AbortController();
      listenAbortRef.current = abort;

      let text: string;
      try {
        text = await listenOnce({ onInterim: setTranscript, signal: abort.signal });
      } catch (e) {
        setError(e instanceof ListenError ? e.message : "Не удалось распознать речь");
        stop();
        return;
      }
      if (!activeRef.current) return;

      if (!text) {
        if (++silences >= MAX_SILENCES) {
          await speak("Заканчиваю беседу. Нажмите на кнопку, когда захотите продолжить.");
          stop();
          return;
        }
        continue;
      }
      silences = 0;

      if (isStop(text)) {
        await speak("Хорошо, до связи.");
        stop();
        return;
      }

      setState("thinking");
      let reply: string;
      try {
        reply = await respondRef.current(text);
      } catch {
        reply = "Не получилось получить ответ. Попробуйте ещё раз.";
      }
      await speak(reply);
    }
  }, [speak, stop]);

  const start = useCallback(() => {
    if (activeRef.current) return;
    if (!speechRecognitionSupported()) {
      setError("Беседа работает в Google Chrome и Safari: этот браузер не умеет распознавать речь.");
      return;
    }
    setError(null);
    activeRef.current = true;
    speakerRef.current = new Speaker(); // создаём по нажатию кнопки — иначе браузер не даст играть звук
    void loop();
  }, [loop]);

  /** Перебить ассистента: замолчать и сразу слушать. */
  const interrupt = useCallback(() => {
    speakerRef.current?.stop();
  }, []);

  useEffect(() => stop, [stop]);

  return { state, transcript, error, active: state !== "idle", start, stop, interrupt };
}
