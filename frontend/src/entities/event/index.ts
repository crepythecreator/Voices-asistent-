export type { CalendarEvent, EventKind, EventSyncStatus } from "./model/types";
export { invalidateEvents, useEventsRevision } from "./model/revision";
export { getEvents } from "./api/getEvents";
export { EventCard } from "./ui/EventCard";
export {
  CATEGORIES,
  CATEGORY_ORDER,
  categoryOf,
  groupByDay,
  type DayGroup,
  type EventCategory,
} from "./lib/category";
