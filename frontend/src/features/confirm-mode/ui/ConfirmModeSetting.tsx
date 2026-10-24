import { ShieldCheck, Zap } from "lucide-react";

import type { ConfirmMode, User } from "@/entities/user";
import { cn } from "@/shared/lib/cn";
import { useConfirmMode } from "../model/useConfirmMode";

const OPTIONS: { id: ConfirmMode; title: string; text: string; icon: typeof Zap }[] = [
  {
    id: "confirm",
    title: "С подтверждением",
    text: "Ассистент готовит изменение, а вы подтверждаете его кнопкой или словом «да» перед записью в календарь.",
    icon: ShieldCheck,
  },
  {
    id: "auto",
    title: "Автоматически",
    text: "Создание и изменение событий — сразу, без вопросов. Удаление всё равно спросит подтверждение.",
    icon: Zap,
  },
];

/** Выбор режима подтверждения — для страницы настроек. */
export function ConfirmModeSetting({ user, onChange }: { user: User; onChange: (user: User) => void }) {
  const { mode, change, busy, error } = useConfirmMode(user, onChange);

  return (
    <div className="flex flex-col gap-3">
      <div role="radiogroup" aria-label="Подтверждение действий" className="grid gap-3 sm:grid-cols-2">
        {OPTIONS.map(({ id, title, text, icon: Icon }) => (
          <button
            key={id}
            type="button"
            role="radio"
            aria-checked={mode === id}
            disabled={busy}
            onClick={() => change(id)}
            className={cn(
              "flex flex-col gap-2 rounded-xl border p-4 text-left transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:opacity-60",
              mode === id ? "border-primary bg-primary/5 ring-1 ring-primary" : "hover:bg-accent",
            )}
          >
            <span className="flex items-center gap-2 font-medium">
              <Icon className="size-4" />
              {title}
            </span>
            <span className="text-sm text-muted-foreground">{text}</span>
          </button>
        ))}
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
