import { useCallback, useEffect, useState } from "react";

import { getEvents, useEventsRevision, type CalendarEvent } from "@/entities/event";
import { addDays, startOfDay } from "@/shared/lib/format";

export const WINDOW_DAYS = 30;

/** Предстоящие события с сегодняшнего дня. Догружаются окнами по 30 дней. */
export function useUpcomingEvents(enabled = true) {
  const [windows, setWindows] = useState(1);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const revision = useEventsRevision();

  useEffect(() => {
    if (!enabled) return;
    // С начала сегодняшнего дня: утренняя встреча не должна «пропадать» из списка днём
    const from = startOfDay(new Date());
    let cancelled = false;
    setLoading(true);
    // Бэкенд отдаёт не больше 100 дней за запрос — грузим каждое окно отдельно
    Promise.all(
      Array.from({ length: windows }, (_, i) =>
        getEvents(addDays(from, i * WINDOW_DAYS), addDays(from, (i + 1) * WINDOW_DAYS)),
      ),
    )
      .then((chunks) => !cancelled && setEvents(chunks.flat()))
      .catch(() => !cancelled && setEvents([]))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [windows, revision, enabled]);

  const loadMore = useCallback(() => setWindows((w) => w + 1), []);

  return { events, loading, days: windows * WINDOW_DAYS, loadMore };
}
