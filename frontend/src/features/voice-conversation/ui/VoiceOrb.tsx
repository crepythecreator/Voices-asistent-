import { AudioLines, Loader2, Mic } from "lucide-react";

import { cn } from "@/shared/lib/cn";
import type { ConversationState } from "../model/useConversation";

const ARIA: Record<ConversationState, string> = {
  idle: "Начать разговор",
  listening: "Слушаю",
  thinking: "Думаю",
  speaking: "Перебить ассистента",
};

interface Props {
  state: ConversationState;
  size?: "sm" | "lg";
  onClick?: () => void;
  disabled?: boolean;
}

/** Сфера состояния беседы. Большая — главная кнопка голосового режима. */
export function VoiceOrb({ state, size = "lg", onClick, disabled }: Props) {
  const lg = size === "lg";
  const Icon = state === "thinking" ? Loader2 : state === "speaking" ? AudioLines : Mic;

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || !onClick}
      aria-label={ARIA[state]}
      className={cn(
        "group relative flex shrink-0 items-center justify-center rounded-full outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-default",
        lg ? "size-44" : "size-10",
      )}
    >
      {/* Расходящиеся круги: красные — слушаю, основного цвета — говорю */}
      {(state === "listening" || state === "speaking") && (
        <>
          <span
            className={cn(
              "absolute inset-0 animate-ping rounded-full [animation-duration:2s]",
              state === "listening" ? "bg-red-500/25" : "bg-primary/15",
            )}
          />
          <span
            className={cn(
              "absolute rounded-full animate-pulse",
              lg ? "inset-3" : "inset-1",
              state === "listening" ? "bg-red-500/20" : "bg-primary/15",
            )}
          />
        </>
      )}
      {state === "idle" && lg && (
        <span className="absolute inset-0 rounded-full bg-primary/5 transition-transform group-hover:scale-105" />
      )}
      <span
        className={cn(
          "relative flex items-center justify-center rounded-full shadow-lg transition-all duration-300",
          lg ? "size-32" : "size-7",
          state === "idle" && "bg-primary text-primary-foreground group-hover:scale-105 group-active:scale-95",
          state === "listening" && "scale-105 bg-red-500 text-white",
          state === "thinking" && "bg-muted text-muted-foreground",
          state === "speaking" && "bg-primary text-primary-foreground",
        )}
      >
        <Icon className={cn(lg ? "size-12" : "size-4", state === "thinking" && "animate-spin")} />
      </span>
    </button>
  );
}
