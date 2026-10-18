export const timeFormat = new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit" });

export const dayFormat = new Intl.DateTimeFormat("ru-RU", { weekday: "long", day: "numeric", month: "long" });

/** Ключ календарного дня в локальной зоне — для группировки событий. */
export const dayKey = (d: Date) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
