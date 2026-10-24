import { Hand, X } from "lucide-react";

import { Button } from "@/shared/ui/button";
import type { ConversationState } from "../model/useConversation";
import { VoiceOrb } from "./VoiceOrb";

export const STATE_LABELS: Record<ConversationState, string> = {
  idle: "Нажмите и говорите",
  listening: "Слушаю…",
  thinking: "Думаю…",
  speaking: "Говорю…",
};

interface Props {
  state: ConversationState;
  transcript: string;
  onInterrupt: () => void;
  onStop: () => void;
}

/** Компактная панель беседы — вместо поля ввода в режиме чата. */
export function ConversationPanel({ state, transcript, onInterrupt, onStop }: Props) {
  return (
    <div className="mx-auto w-full max-w-3xl px-4 pb-4">
      <div className="flex items-center gap-4 rounded-2xl border bg-background p-4 shadow-sm" aria-live="polite">
        <VoiceOrb state={state} size="sm" />
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium">{STATE_LABELS[state]}</div>
          <div className="truncate text-sm text-muted-foreground">
            {state === "listening"
              ? transcript || "Говорите — я отвечу, когда вы замолчите"
              : state === "speaking"
                ? "Нажмите «Перебить», чтобы сказать своё"
                : transcript}
          </div>
        </div>
        {state === "speaking" && (
          <Button variant="outline" size="sm" onClick={onInterrupt}>
            <Hand />
            Перебить
          </Button>
        )}
        <Button variant="ghost" size="icon-sm" onClick={onStop} aria-label="Завершить беседу" title="Завершить беседу">
          <X />
        </Button>
      </div>
    </div>
  );
}
