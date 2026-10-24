import { useCallback, useRef } from "react";

import type { ProposedAction } from "@/entities/action";
import { invalidateEvents } from "@/entities/event";
import type { Message } from "@/entities/message";
import { resolveAction } from "@/features/confirm-action";
import { isNo, isYes, useConversation } from "@/features/voice-conversation";

interface Options {
  messages: Message[];
  send: (text: string, source: "voice") => Promise<Message | null>;
  updateAction: (action: ProposedAction) => void;
}

const pendingOf = (m: Message | undefined) => m?.actions?.filter((a) => a.status === "pending") ?? [];

function withConfirmationQuestion(reply: Message): string {
  const pending = pendingOf(reply);
  if (!pending.length) return reply.text;
  const what = pending.map((a) => a.summary).join(". ");
  return `${reply.text} ${what}. Подтвердить? Скажите «да» или «нет».`;
}

/**
 * Беседа голосом поверх чата. Ответ «да»/«нет» на вопрос о подтверждении обрабатывает не ИИ,
 * а это правило: оно применяет только действия из последнего ответа ассистента и только на
 * короткую однозначную фразу — принцип «ИИ сам ничего не меняет» сохраняется и голосом.
 */
export function useVoiceChat({ messages, send, updateAction }: Options) {
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  const respond = useCallback(
    async (text: string): Promise<string> => {
      const last = [...messagesRef.current].reverse().find((m) => m.role === "assistant" && !m.pending);
      const pending = pendingOf(last);

      if (pending.length && (isYes(text) || isNo(text))) {
        const decision = isYes(text) ? "confirm" : "reject";
        const results = await Promise.allSettled(pending.map((a) => resolveAction(a, decision)));
        const resolved = results.flatMap((r) => (r.status === "fulfilled" ? [r.value] : []));
        resolved.forEach(updateAction);
        if (decision === "reject") return "Хорошо, отменил.";
        invalidateEvents();
        const failed = results.length - resolved.filter((a) => a.status === "applied").length;
        return failed ? "Не всё получилось применить — проверьте карточки в чате." : "Готово, записал в календарь.";
      }

      const reply = await send(text, "voice");
      if (!reply) return "Не получилось получить ответ. Попробуйте ещё раз.";
      return withConfirmationQuestion(reply);
    },
    [send, updateAction],
  );

  return useConversation({ respond });
}
