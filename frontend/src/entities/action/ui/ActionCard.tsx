import type { ReactNode } from "react";
import { CalendarMinus, CalendarCog, CalendarPlus, type LucideIcon } from "lucide-react";

import { cn } from "@/shared/lib/cn";
import { Badge } from "@/shared/ui/badge";
import type { ActionStatus, ActionType, ProposedAction } from "../model/types";

const ICONS: Record<ActionType, LucideIcon> = {
  create_event: CalendarPlus,
  update_event: CalendarCog,
  delete_event: CalendarMinus,
};

const STATUS: Record<Exclude<ActionStatus, "pending">, { label: string; variant: "secondary" | "outline" | "destructive" }> = {
  applied: { label: "Выполнено", variant: "secondary" },
  rejected: { label: "Отклонено", variant: "outline" },
  expired: { label: "Истекло", variant: "outline" },
  failed: { label: "Ошибка", variant: "destructive" },
};

interface Props {
  action: ProposedAction;
  /** Кнопки решения — передаются снаружи (фича confirm-action). */
  controls?: ReactNode;
}

export function ActionCard({ action, controls }: Props) {
  const Icon = ICONS[action.type];
  const status = action.status === "pending" ? null : STATUS[action.status];

  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-xl border bg-card p-3 text-sm shadow-xs",
        action.status === "pending" && "border-primary/30",
        (action.status === "rejected" || action.status === "expired") && "opacity-60",
      )}
    >
      <div className="flex items-start gap-2">
        <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        <span className={cn("flex-1", action.status === "rejected" && "line-through")}>{action.summary}</span>
        {status && <Badge variant={status.variant}>{status.label}</Badge>}
      </div>
      {action.error && <p className="text-xs text-destructive">{action.error}</p>}
      {action.status === "pending" && controls}
    </div>
  );
}
