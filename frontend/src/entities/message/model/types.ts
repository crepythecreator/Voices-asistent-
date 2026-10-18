import type { ProposedAction } from "@/entities/action/@x/message";

export type MessageRole = "user" | "assistant";

export type MessageSource = "text" | "voice";

export interface Message {
  id: string;
  role: MessageRole;
  text: string;
  createdAt: string; // ISO
  source?: MessageSource | null;
  /** Изменения календаря, которые ассистент предложил в этом ответе. */
  actions?: ProposedAction[];
  pending?: boolean;
  error?: boolean;
}
