import { Bell, CalendarClock, CalendarDays, CheckSquare, type LucideIcon } from "lucide-react";

import { dayKey, startOfDay } from "@/shared/lib/format";
import type { CalendarEvent } from "../model/types";

/** Категория для цвета и фильтров: тип события ассистента или «другие календари». */
export type EventCategory = "meeting" | "reminder" | "task" | "external";

export const CATEGORIES: Record<EventCategory, { label: string; plural: string; icon: LucideIcon; dot: string; bar: string }> = {
  meeting: { label: "Встреча", plural: "Встречи", icon: CalendarClock, dot: "bg-sky-500", bar: "border-l-sky-500" },
  reminder: { label: "Напоминание", plural: "Напоминания", icon: Bell, dot: "bg-amber-500", bar: "border-l-amber-500" },
  task: { label: "Задача", plural: "Задачи", icon: CheckSquare, dot: "bg-emerald-500", bar: "border-l-emerald-500" },
  external: {
    label: "Другой календарь",
    plural: "Другие календари",
    icon: CalendarDays,
    dot: "bg-muted-foreground/60",
    bar: "border-l-muted-foreground/40",
  },
};

export const CATEGORY_ORDER: EventCategory[] = ["meeting", "reminder", "task", "external"];

export function categoryOf(e: CalendarEvent): EventCategory {
  return e.source === "assistant" ? e.kind : "external";
}

export interface DayGroup {
  key: string;
  date: Date;
  events: CalendarEvent[];
}

/** Группирует события по дням (локальная зона), дни и события внутри — по времени. */
export function groupByDay(events: CalendarEvent[]): DayGroup[] {
  const map = new Map<string, DayGroup>();
  for (const e of events) {
    const start = new Date(e.start);
    const key = dayKey(start);
    const group = map.get(key) ?? { key, date: startOfDay(start), events: [] };
    group.events.push(e);
    map.set(key, group);
  }
  const groups = [...map.values()].sort((a, b) => a.date.getTime() - b.date.getTime());
  for (const g of groups) g.events.sort((a, b) => a.start.localeCompare(b.start));
  return groups;
}
