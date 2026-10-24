import { ApiError } from "@/shared/api";
import { USE_MOCKS } from "@/shared/config";

/** WAV с озвучкой текста (бэкенд: GigaChat/SaluteSpeech через Cloud.ru). */
export async function fetchSpeech(text: string, signal?: AbortSignal): Promise<ArrayBuffer> {
  if (USE_MOCKS) throw new ApiError(503, "В демо-режиме синтеза нет");
  const res = await fetch("/api/tts", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
    signal,
  });
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  return res.arrayBuffer();
}
