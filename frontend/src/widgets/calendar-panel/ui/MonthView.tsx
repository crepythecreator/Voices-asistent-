import { createContext, useContext, useMemo } from "react";
import type { DayButtonProps } from "react-day-picker";

import { CATEGORIES, CATEGORY_ORDER, categoryOf, EventCard, groupByDay, type CalendarEvent, type EventCategory } from "@/entities/event";
import { cn } from "@/shared/lib/cn";
import { dayKey, dayLabel, eventsCount } from "@/shared/lib/format";
import { Calendar } from "@/shared/ui/calendar";

// Категории событий по дням — для точек в ячейках. Через контекст, чтобы DayButton был стабильным компонентом.
const DotsContext = createContext<Map<string, EventCategory[]>>(new Map());

function DayButton({ day, modifiers: _modifiers, children, ...props }: DayButtonProps) {
  const categories = useContext(DotsContext).get(dayKey(day.date));
  return (
    <button {...props}>
      {children}
      {categories && (
        <span className="pointer-events-none absolute bottom-1 left-1/2 flex -translate-x-1/2 gap-0.5">
          {categories.map((c) => (
            <span key={c} className={cn("size-1 rounded-full", CATEGORIES[c].dot)} />
          ))}
        </span>
      )}
    </button>
  );
}

interface Props {
  events: CalendarEvent[];
  loading: boolean;
  month: Date;
  onMonthChange: (month: Date) => void;
  selected: Date;
  onSelect: (day: Date) => void;
}

export function MonthView({ events, loading, month, onMonthChange, selected, onSelect }: Props) {
  const groups = useMemo(() => groupByDay(events), [events]);

  const dots = useMemo(() => {
    const map = new Map<string, EventCategory[]>();
    for (const g of groups) {
      const present = new Set(g.events.map(categoryOf));
      map.set(g.key, CATEGORY_ORDER.filter((c) => present.has(c)));
    }
    return map;
  }, [groups]);

  const dayEvents = groups.find((g) => g.key === dayKey(selected))?.events ?? [];

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-xl border p-2">
        <DotsContext.Provider value={dots}>
          <Calendar
            mode="single"
            required
            selected={selected}
            onSelect={onSelect}
            month={month}
            onMonthChange={onMonthChange}
            components={{ DayButton }}
          />
        </DotsContext.Provider>
      </div>

      <section className="flex flex-col gap-2">
        <div className="flex items-baseline justify-between gap-2 px-1">
          <h3 className="text-sm font-semibold">{dayLabel(selected)}</h3>
          <span className="text-xs text-muted-foreground">
            {loading ? "Загрузка…" : dayEvents.length ? eventsCount(dayEvents.length) : ""}
          </span>
        </div>
        {dayEvents.length ? (
          dayEvents.map((e) => <EventCard key={e.id} event={e} />)
        ) : (
          !loading && <p className="rounded-lg border border-dashed px-3 py-4 text-center text-sm text-muted-foreground">Свободный день</p>
        )}
      </section>
    </div>
  );
}
