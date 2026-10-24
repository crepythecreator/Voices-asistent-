import { Hand, X } from "lucide-react";

import { cn } from "@/shared/lib/cn";
import { Button } from "@/shared/ui/button";
import type { ConversationState } from "../model/useConversation";

const LABELS: Record<ConversationState, string> = {
  idle: "",
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

/** Панель режима беседы вместо поля ввода. */
export function ConversationPanel({ state, transcript, onInterrupt, onStop }: Props) {
  return (
    <div className="mx-auto w-full max-w-3xl px-4 pb-4">
      <div className="flex items-center gap-4 rounded-2xl border bg-background p-4 shadow-sm" aria-live="polite">
        <Orb state={state} />
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium">{LABELS[state]}</div>
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

function Orb({ state }: { state: ConversationState }) {
  return (
    <div className="relative flex size-10 shrink-0 items-center justify-center">
      <span
        className={cn(
          "absolute inset-0 rounded-full",
          state === "listening" && "animate-ping bg-red-500/30",
          state === "speaking" && "animate-pulse bg-primary/20",
        )}
      />
      <span
        className={cn(
          "relative size-6 rounded-full transition-colors",
          state === "listening" && "bg-red-500",
          state === "thinking" && "animate-pulse bg-muted-foreground",
          state === "speaking" && "bg-primary",
        )}
      />
    </div>
  );
}
