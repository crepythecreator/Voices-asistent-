import { useChat } from "@/features/send-message";
import { useVoiceChat } from "./useVoiceChat";

/** Общее состояние голосового и текстового режимов: одна история и одна беседа. */
export function useAssistant() {
  const chat = useChat();
  const conversation = useVoiceChat({ messages: chat.messages, send: chat.send, updateAction: chat.updateAction });
  return { chat, conversation };
}

export type AssistantState = ReturnType<typeof useAssistant>;
