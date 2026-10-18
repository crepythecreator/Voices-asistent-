import { api } from "@/shared/api";

export interface TranscribeResponse {
  text: string;
}

/**
 * Отправляет PCM (16 бит, моно) на бэкенд, который распознаёт его через Yandex SpeechKit.
 * Моков нет: серверный движок включают именно для проверки реального распознавания.
 */
export function transcribe(pcm: ArrayBuffer, sampleRate: number, lang: string): Promise<TranscribeResponse> {
  const params = new URLSearchParams({ sample_rate: String(sampleRate), lang });
  return api<TranscribeResponse>(`/stt?${params}`, {
    method: "POST",
    headers: { "Content-Type": "application/octet-stream" },
    body: pcm,
  });
}
