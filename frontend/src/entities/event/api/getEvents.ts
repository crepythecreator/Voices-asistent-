import { api, delay } from "@/shared/api";
import { USE_MOCKS } from "@/shared/config";
import type { CalendarEvent } from "../model/types";
import { MOCK_EVENTS } from "./mocks";

export async function getEvents(from: Date, to: Date): Promise<CalendarEvent[]> {
  if (USE_MOCKS) {
    await delay(300);
    return MOCK_EVENTS.filter((e) => {
      const t = new Date(e.start).getTime();
      return t >= from.getTime() && t < to.getTime();
    });
  }
  const params = new URLSearchParams({ from: from.toISOString(), to: to.toISOString() });
  return api<CalendarEvent[]>(`/events?${params}`);
}
