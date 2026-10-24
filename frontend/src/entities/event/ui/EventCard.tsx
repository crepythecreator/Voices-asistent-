import { useState } from "react";
import { ChevronDown, CloudOff, Loader2 } from "lucide-react";

import { cn } from "@/shared/lib/cn";
import { timeFormat } from "@/shared/lib/format";
import { CATEGORIES, categoryOf } from "../lib/category";
import type { CalendarEvent } from "../model/types";

/** Карточка события: время слева, цветная полоса по типу, описание раскрывается по нажатию. */
export function EventCard({ event: e }: { event: CalendarEvent }) {
  const [open, setOpen] = useState(false);
  const category = CATEGORIES[categoryOf(e)];
  const external = e.source !== "assistant";
  const start = new Date(e.start);
  const allDay = Boolean(e.allDay);
  const expandable = Boolean(e.description);

  const meta = [external ? (e.calendarName ?? (e.source === "google" ? "Google" : "Яндекс")) : category.label];

  return (
    <div
      className={cn(
        "flex gap-3 rounded-lg border border-l-4 bg-card px-3 py-2.5",
        category.bar,
        external && "border-dashed bg-muted/30",
      )}
    >
      <div className="w-11 shrink-0 pt-px text-xs tabular-nums">
        {allDay ? (
          <span className="text-muted-foreground">весь день</span>
        ) : (
          <>
            <div className="font-medium">{timeFormat.format(start)}</div>
            {e.end && <div className="text-muted-foreground">{timeFormat.format(new Date(e.end))}</div>}
          </>
        )}
      </div>

      <div className="min-w-0 flex-1">
        <button
          type="button"
          disabled={!expandable}
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-start gap-1 text-left disabled:cursor-default"
          aria-expanded={expandable ? open : undefined}
        >
          <span className={cn("flex-1 text-sm font-medium break-words", external && "text-muted-foreground")}>{e.title}</span>
          {expandable && <ChevronDown className={cn("mt-0.5 size-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} />}
        </button>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground">
          <span>{meta.join(" · ")}</span>
          {e.syncStatus === "error" && (
            <span className="flex items-center gap-1 text-destructive" title="Не удалось выгрузить в подключённый календарь — повторите в настройках">
              · <CloudOff className="size-3" /> не выгружено
            </span>
          )}
          {e.syncStatus === "pending" && (
            <span className="flex items-center gap-1" title="Выгружается в подключённые календари">
              · <Loader2 className="size-3 animate-spin" /> выгрузка
            </span>
          )}
        </div>
        {open && e.description && <p className="mt-2 text-sm whitespace-pre-wrap text-muted-foreground">{e.description}</p>}
      </div>
    </div>
  );
}
