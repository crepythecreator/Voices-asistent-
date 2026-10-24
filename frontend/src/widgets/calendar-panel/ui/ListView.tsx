import { useMemo } from "react";
import { CalendarPlus } from "lucide-react";

import { EventCard, groupByDay, type CalendarEvent } from "@/entities/event";
import { cn } from "@/shared/lib/cn";
import { dayLabel, eventsCount, startOfDay } from "@/shared/lib/format";
import { Button } from "@/shared/ui/button";
import { Spinner } from "@/shared/ui/spinner";

interface Props {
  events: CalendarEvent[];
  loading: boolean;
  days: number;
  onLoadMore: () => void;
}

/** Доска событий: всё предстоящее подряд, по датам. */
export function ListView({ events, loading, days, onLoadMore }: Props) {
  const groups = useMemo(() => groupByDay(events), [events]);
  const today = startOfDay(new Date()).getTime();

  if (loading && !events.length) {
    return (
      <div className="flex justify-center py-10">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {groups.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed px-4 py-10 text-center">
          <CalendarPlus className="size-6 text-muted-foreground" />
          <p className="text-sm font-medium">Ближайшие {days} дней свободны</p>
          <p className="text-xs text-muted-foreground">Скажите ассистенту, что запланировать</p>
        </div>
      ) : (
        groups.map((g) => (
          <section key={g.key} className="flex flex-col gap-2">
            {/* Дата прилипает к верху при прокрутке */}
            <div className="sticky top-0 z-10 -mx-1 flex items-baseline justify-between gap-2 bg-background/95 px-1 py-1 backdrop-blur">
              <h3 className={cn("text-sm font-semibold", g.date.getTime() === today && "text-primary")}>{dayLabel(g.date)}</h3>
              <span className="text-xs text-muted-foreground">
                {eventsCount(g.events.length)}
              </span>
            </div>
            {g.events.map((e) => (
              <EventCard key={e.id} event={e} />
            ))}
          </section>
        ))
      )}

      <div className="flex flex-col items-center gap-1 pb-2">
        <Button variant="outline" size="sm" onClick={onLoadMore} disabled={loading}>
          {loading && <Spinner className="size-4" />}
          Показать ещё 30 дней
        </Button>
        <span className="text-xs text-muted-foreground">Показаны события на {days} дней вперёд</span>
      </div>
    </div>
  );
}
