import { Bell, CalendarClock, CheckSquare, CloudOff } from "lucide-react";

import { cn } from "@/shared/lib/cn";
import { timeFormat } from "@/shared/lib/format";
import { Badge } from "@/shared/ui/badge";
import type { CalendarEvent, EventKind } from "../model/types";

const KIND: Record<EventKind, { label: string; icon: typeof Bell }> = {
  meeting: { label: "Встреча", icon: CalendarClock },
  reminder: { label: "Напоминание", icon: Bell },
  task: { label: "Задача", icon: CheckSquare },
};

export function EventCard({ event: e }: { event: CalendarEvent }) {
  const external = e.source === "yandex";
  const { label, icon: Icon } = KIND[e.kind];
  const syncFailed = e.syncStatus === "error";

  return (
    <div className={cn("flex items-start gap-3 rounded-lg border p-3", external && "border-dashed bg-muted/40")}>
      <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1">
        <div className={cn("truncate text-sm font-medium", external && "text-muted-foreground")}>{e.title}</div>
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          {timeFormat.format(new Date(e.start))}
          {e.end && ` – ${timeFormat.format(new Date(e.end))}`}
          {syncFailed && (
            <span className="flex items-center gap-1 text-destructive" title="Не удалось выгрузить в Яндекс Календарь">
              · <CloudOff className="size-3" /> не в Яндексе
            </span>
          )}
        </div>
      </div>
      {external ? (
        <Badge variant="outline" title="Событие из Яндекс Календаря, только для просмотра">
          {e.calendarName ?? "Яндекс"}
        </Badge>
      ) : (
        <Badge variant="secondary">{label}</Badge>
      )}
    </div>
  );
}
