import { ShieldCheck, Zap } from "lucide-react";

import type { User } from "@/entities/user";
import { cn } from "@/shared/lib/cn";
import { useConfirmMode } from "../model/useConfirmMode";

/** Компактный переключатель режима подтверждения — на экране ассистента. */
export function ConfirmModeToggle({ user, onChange }: { user: User; onChange: (user: User) => void }) {
  const { mode, change, busy } = useConfirmMode(user, onChange);
  const auto = mode === "auto";

  return (
    <button
      type="button"
      disabled={busy}
      onClick={() => change(auto ? "confirm" : "auto")}
      aria-pressed={auto}
      aria-label={auto ? "Режим: авто" : "Режим: с подтверждением"}
      title={
        auto
          ? "Авто: создание и изменение — сразу, удаление — с подтверждением. Нажмите, чтобы подтверждать всё."
          : "С подтверждением: изменения записываются после вашего «да». Нажмите, чтобы применять сразу."
      }
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:opacity-60",
        auto
          ? "bg-amber-500/15 text-amber-700 hover:bg-amber-500/25 dark:text-amber-400"
          : "text-muted-foreground hover:bg-accent hover:text-foreground",
      )}
    >
      {auto ? <Zap className="size-4" /> : <ShieldCheck className="size-4" />}
      <span className={cn(!auto && "hidden sm:inline")}>{auto ? "Авто" : "С подтверждением"}</span>
    </button>
  );
}
