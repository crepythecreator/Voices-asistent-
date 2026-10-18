import type { CalendarEvent } from "../model/types";

function at(dayOffset: number, hours: number, minutes = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + dayOffset);
  d.setHours(hours, minutes, 0, 0);
  return d.toISOString();
}

const ours = { source: "assistant", readonly: false, syncStatus: "synced" } as const;
const yandex = { source: "yandex", readonly: true, kind: "meeting", calendarName: "Рабочий" } as const;

export const MOCK_EVENTS: CalendarEvent[] = [
  { id: "1", title: "Созвон с командой", kind: "meeting", start: at(0, 10), end: at(0, 10, 30), ...ours },
  { id: "2", title: "Позвонить маме", kind: "reminder", start: at(0, 19), ...ours },
  { id: "y1", title: "Планёрка", start: at(0, 12), end: at(0, 13), ...yandex },
  { id: "3", title: "Подготовить отчёт", kind: "task", start: at(1, 12), ...ours },
  { id: "4", title: "Встреча с заказчиком", kind: "meeting", start: at(2, 15), end: at(2, 16), ...ours },
  { id: "5", title: "Оплатить интернет", kind: "reminder", start: at(4, 9), ...ours },
];
