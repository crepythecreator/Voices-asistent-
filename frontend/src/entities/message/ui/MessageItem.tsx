import { Bot, Mic } from "lucide-react";

import { cn } from "@/shared/lib/cn";
import { timeFormat } from "@/shared/lib/format";
import type { Message } from "../model/types";

export function MessageItem({ message: m }: { message: Message }) {
  return (
    <div className={cn("flex gap-3", m.role === "user" && "justify-end")}>
      {m.role === "assistant" && (
        <div className="flex size-8 shrink-0 items-center justify-center rounded-full border bg-background">
          <Bot className="size-4" />
        </div>
      )}
      <div className={cn("flex max-w-[80%] flex-col gap-1", m.role === "user" && "items-end")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-2 text-sm leading-relaxed whitespace-pre-wrap",
            m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted",
            m.error && "bg-destructive/10 text-destructive",
          )}
        >
          {m.pending ? <TypingDots /> : m.text}
        </div>
        {!m.pending && (
          <span className="flex items-center gap-1 px-1 text-xs text-muted-foreground">
            {m.source === "voice" && <Mic className="size-3" />}
            {timeFormat.format(new Date(m.createdAt))}
          </span>
        )}
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <span className="flex h-5 items-center gap-1" aria-label="Ассистент печатает">
      {[0, 150, 300].map((d) => (
        <span
          key={d}
          className="size-1.5 animate-bounce rounded-full bg-muted-foreground"
          style={{ animationDelay: `${d}ms` }}
        />
      ))}
    </span>
  );
}
