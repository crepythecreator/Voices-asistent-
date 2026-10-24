import { useCallback, useEffect, useState } from "react";

import type { ProposedAction } from "@/entities/action";
import type { Message, MessageSource } from "@/entities/message";
import { getHistory, sendMessage } from "../api/sendMessage";

const uid = () => crypto.randomUUID();
const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

/** История диалога и отправка сообщения ассистенту. */
export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getHistory()
      .then((history) => !cancelled && setMessages((prev) => [...history, ...prev]))
      .catch(() => {})
      .finally(() => !cancelled && setLoadingHistory(false));
    return () => {
      cancelled = true;
    };
  }, []);

  /** Отправляет сообщение. Возвращает ответ ассистента (null — ошибка). */
  const send = useCallback(async (text: string, source: MessageSource = "text"): Promise<Message | null> => {
    const message = text.trim();
    if (!message) return null;

    const now = new Date().toISOString();
    const userMsg: Message = { id: uid(), role: "user", text: message, createdAt: now, source };
    const placeholderId = uid();
    setMessages((prev) => [
      ...prev,
      userMsg,
      { id: placeholderId, role: "assistant", text: "", createdAt: now, pending: true },
    ]);
    setSending(true);

    try {
      const { message: reply } = await sendMessage({ message, source, timezone });
      setMessages((prev) => prev.map((m) => (m.id === placeholderId ? reply : m)));
      return reply;
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === placeholderId
            ? { ...m, text: "Не удалось получить ответ. Попробуйте ещё раз.", pending: false, error: true }
            : m,
        ),
      );
      return null;
    } finally {
      setSending(false);
    }
  }, []);

  /** Обновляет действие после подтверждения или отклонения. */
  const updateAction = useCallback((action: ProposedAction) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.actions?.some((a) => a.id === action.id)
          ? { ...m, actions: m.actions.map((a) => (a.id === action.id ? action : a)) }
          : m,
      ),
    );
  }, []);

  return { messages, sending, loadingHistory, send, updateAction };
}
