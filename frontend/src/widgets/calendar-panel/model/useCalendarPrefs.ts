import { useCallback, useState } from "react";

import { CATEGORY_ORDER, categoryOf, type CalendarEvent, type EventCategory } from "@/entities/event";

export type CalendarView = "month" | "list";

const VIEW_KEY = "calendar-view";
const HIDDEN_KEY = "calendar-hidden-categories";

function read<T>(key: string, fallback: T, parse: (raw: string) => T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw === null ? fallback : parse(raw);
  } catch {
    return fallback;
  }
}

function write(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* localStorage недоступен — просто не запомним */
  }
}

/** Вид календаря и фильтр по типам событий. Запоминаются в этом браузере. */
export function useCalendarPrefs() {
  const [view, setViewState] = useState<CalendarView>(() => read(VIEW_KEY, "month", (r) => (r === "list" ? "list" : "month")));
  const [hidden, setHidden] = useState<Set<EventCategory>>(
    () =>
      new Set(
        read<EventCategory[]>(HIDDEN_KEY, [], (r) =>
          (JSON.parse(r) as string[]).filter((c): c is EventCategory => CATEGORY_ORDER.includes(c as EventCategory)),
        ),
      ),
  );

  const setView = useCallback((next: CalendarView) => {
    setViewState(next);
    write(VIEW_KEY, next);
  }, []);

  const toggleCategory = useCallback((category: EventCategory) => {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(category)) next.delete(category);
      else next.add(category);
      write(HIDDEN_KEY, JSON.stringify([...next]));
      return next;
    });
  }, []);

  const visible = useCallback((e: CalendarEvent) => !hidden.has(categoryOf(e)), [hidden]);

  return { view, setView, hidden, toggleCategory, visible };
}
