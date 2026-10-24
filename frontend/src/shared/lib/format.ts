export const timeFormat = new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit" });

export const dayFormat = new Intl.DateTimeFormat("ru-RU", { weekday: "long", day: "numeric", month: "long" });

const dayMonthFormat = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long" });

/** Ключ календарного дня в локальной зоне — для группировки событий. */
export const dayKey = (d: Date) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;

export function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

export function addDays(d: Date, days: number): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + days);
}

/** «1 событие», «3 события», «5 событий». */
export function eventsCount(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return `${n} событие`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return `${n} события`;
  return `${n} событий`;
}

const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/** «Сегодня, 24 октября», «Завтра, 25 октября», «Понедельник, 27 октября». */
export function dayLabel(d: Date, now: Date = new Date()): string {
  const diff = Math.round((startOfDay(d).getTime() - startOfDay(now).getTime()) / 86_400_000);
  if (diff === 0) return `Сегодня, ${dayMonthFormat.format(d)}`;
  if (diff === 1) return `Завтра, ${dayMonthFormat.format(d)}`;
  if (diff === -1) return `Вчера, ${dayMonthFormat.format(d)}`;
  return capitalize(dayFormat.format(d));
}
