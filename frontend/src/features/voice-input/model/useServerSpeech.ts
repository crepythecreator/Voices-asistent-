import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "@/shared/api";
import { transcribe } from "../api/transcribe";
import { startRecording, TARGET_SAMPLE_RATE, type Recording } from "../lib/recorder";
import type { SpeechOptions, SpeechRecognitionApi } from "./types";

// Синхронное распознавание SpeechKit принимает до 30 секунд аудио.
const MAX_SECONDS = 29;

/**
 * Движок «запись в браузере + распознавание на бэкенде» (Yandex SpeechKit).
 * Не зависит от браузера: нужен только доступ к микрофону.
 */
export function useServerSpeech({ lang = "ru-RU", onFinal }: SpeechOptions = {}): SpeechRecognitionApi {
  const supported = typeof window !== "undefined" && "mediaDevices" in navigator && "AudioWorkletNode" in window;

  const [listening, setListening] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const recordingRef = useRef<Recording | null>(null);
  const startingRef = useRef(false);
  const onFinalRef = useRef(onFinal);
  onFinalRef.current = onFinal;

  const stop = useCallback(async () => {
    const rec = recordingRef.current;
    if (!rec) return;
    recordingRef.current = null;
    setListening(false);
    setProcessing(true);
    try {
      const pcm = await rec.stop();
      const { text } = await transcribe(pcm, TARGET_SAMPLE_RATE, lang);
      if (text.trim()) onFinalRef.current?.(text.trim());
      else setError("Не удалось расслышать речь. Попробуйте ещё раз.");
    } catch (e) {
      setError(e instanceof ApiError ? `Ошибка распознавания: ${e.message}` : "Не удалось распознать речь.");
    } finally {
      setProcessing(false);
    }
  }, [lang]);

  const start = useCallback(async () => {
    if (!supported || recordingRef.current || startingRef.current || processing) return;
    startingRef.current = true;
    setError(null);
    try {
      recordingRef.current = await startRecording((sec) => {
        if (sec >= MAX_SECONDS) void stop();
      });
      setListening(true);
    } catch (e) {
      const denied = e instanceof DOMException && e.name === "NotAllowedError";
      setError(denied ? "Нет доступа к микрофону. Разрешите его в настройках браузера." : "Не удалось включить микрофон.");
    } finally {
      startingRef.current = false;
    }
  }, [supported, processing, stop]);

  const toggle = useCallback(() => void (recordingRef.current ? stop() : start()), [start, stop]);

  useEffect(() => () => recordingRef.current?.cancel(), []);

  return {
    supported,
    listening,
    processing,
    transcript: "",
    error,
    start: () => void start(),
    stop: () => void stop(),
    toggle,
  };
}
