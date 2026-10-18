import { useEffect, useMemo, useState } from "react";

import { getEvents, useEventsRevision, type CalendarEvent } from "@/entities/event";
import { dayKey } from "@/shared/lib/format";

/** События видимого месяца (с запасом на соседние недели), сгруппированные по дням. */
export function useMonthEvents(month: Date) {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  // Меняется, когда пользователь подтвердил изменение календаря, — перезагружаем события
  const revision = useEventsRevision();

  useEffect(() => {
    const from = new Date(month.getFullYear(), month.getMonth() - 1, 20);
    const to = new Date(month.getFullYear(), month.getMonth() + 1, 10);
    let cancelled = false;
    setLoading(true);
    getEvents(from, to)
      .then((list) => !cancelled && setEvents(list))
      .catch(() => !cancelled && setEvents([]))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [month, revision]);

  const byDay = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const e of events) {
      const k = dayKey(new Date(e.start));
      map.set(k, [...(map.get(k) ?? []), e]);
    }
    for (const list of map.values()) list.sort((a, b) => a.start.localeCompare(b.start));
    return map;
  }, [events]);

  const daysWithEvents = useMemo(() => events.map((e) => new Date(e.start)), [events]);

  return { loading, byDay, daysWithEvents };
}
