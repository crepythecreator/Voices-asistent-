import { useEffect, useState } from "react";

import { getEvents, useEventsRevision, type CalendarEvent } from "@/entities/event";

/** События видимого месяца с запасом на соседние недели (их тоже видно в сетке). */
export function useMonthEvents(month: Date, enabled = true) {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  // Меняется, когда календарь изменился (подтверждение, авто-режим, настройки), — перезагружаем
  const revision = useEventsRevision();

  useEffect(() => {
    if (!enabled) return;
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
  }, [month, revision, enabled]);

  return { events, loading };
}
