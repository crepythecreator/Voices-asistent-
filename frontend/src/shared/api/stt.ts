import { api } from "@/shared/api";

export interface TranscribeResponse {
  text: string;
}

/**
 * Отправляет PCM (16 бит, моно) на бэкенд: он распознаёт речь через Cloud.ru (GigaASR) или Yandex SpeechKit.
 * Моков нет: серверное распознавание включают именно для проверки реальной речи.
 */
export function transcribe(pcm: ArrayBuffer, sampleRate: number, lang: string): Promise<TranscribeResponse> {
  const params = new URLSearchParams({ sample_rate: String(sampleRate), lang });
  return api<TranscribeResponse>(`/stt?${params}`, {
    method: "POST",
    headers: { "Content-Type": "application/octet-stream" },
    body: pcm,
  });
}
