import type { Message, MessageSource } from "@/entities/message";
import { api, delay } from "@/shared/api";
import { USE_MOCKS } from "@/shared/config";

export interface SendMessageRequest {
  message: string;
  source: MessageSource;
  timezone: string;
}

export interface SendMessageResponse {
  reply: string;
  /** Сохранённый ответ ассистента вместе с предложенными действиями. */
  message: Message;
}

function mockReply(req: SendMessageRequest): SendMessageResponse {
  const wantsChange = /напомни|создай|запланируй|встреч|задач/i.test(req.message);
  return {
    reply: "",
    message: {
      id: crypto.randomUUID(),
      role: "assistant",
      text: wantsChange
        ? "Подготовил изменение — подтвердите его, и я добавлю его в календарь."
        : "Демо-режим: подключите бэкенд (VITE_USE_MOCKS=false), чтобы я отвечал по-настоящему.",
      createdAt: new Date().toISOString(),
      actions: wantsChange
        ? [
            {
              id: crypto.randomUUID(),
              type: "create_event",
              summary: `Создать событие «${req.message}»`,
              status: "pending",
              error: null,
              eventId: null,
              expiresAt: new Date(Date.now() + 86_400_000).toISOString(),
            },
          ]
        : [],
    },
  };
}

export async function sendMessage(req: SendMessageRequest): Promise<SendMessageResponse> {
  if (USE_MOCKS) {
    await delay(700);
    return mockReply(req);
  }
  return api<SendMessageResponse>("/chat", { method: "POST", body: JSON.stringify(req) });
}

export async function getHistory(): Promise<Message[]> {
  if (USE_MOCKS) return [];
  return api<Message[]>("/chat/history");
}
