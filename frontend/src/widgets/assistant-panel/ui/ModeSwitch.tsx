import { MessageSquare, Mic } from "lucide-react";

import { cn } from "@/shared/lib/cn";
import type { AssistantMode } from "../model/useAssistantMode";

const MODES: { id: AssistantMode; label: string; icon: typeof Mic }[] = [
  { id: "voice", label: "Голос", icon: Mic },
  { id: "chat", label: "Чат", icon: MessageSquare },
];

export function ModeSwitch({ mode, onChange }: { mode: AssistantMode; onChange: (mode: AssistantMode) => void }) {
  return (
    <div role="tablist" aria-label="Режим" className="inline-flex rounded-lg bg-muted p-1 text-sm">
      {MODES.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          role="tab"
          type="button"
          aria-selected={mode === id}
          onClick={() => onChange(id)}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md px-3 py-1 font-medium transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
            mode === id ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
          )}
        >
          <Icon className="size-4" />
          {label}
        </button>
      ))}
    </div>
  );
}
