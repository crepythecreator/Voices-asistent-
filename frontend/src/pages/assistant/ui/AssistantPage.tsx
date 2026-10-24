import { useState } from "react";

import { CalendarPanel } from "@/widgets/calendar-panel";
import { AssistantPanel } from "@/widgets/assistant-panel";
import { Header } from "@/widgets/header";
import { cn } from "@/shared/lib/cn";

export function AssistantPage() {
  // На широких экранах календарь открыт сбоку, на узких — поверх ассистента.
  const [calendarOpen, setCalendarOpen] = useState(() => window.matchMedia("(min-width: 1024px)").matches);

  return (
    <div className="flex h-full flex-col">
      <Header calendarOpen={calendarOpen} onToggleCalendar={() => setCalendarOpen((v) => !v)} />
      <div className="relative flex min-h-0 flex-1">
        <AssistantPanel />
        {calendarOpen && (
          <aside
            className={cn(
              "absolute inset-0 z-10 overflow-y-auto bg-background p-4",
              "lg:static lg:w-[360px] lg:shrink-0 lg:border-l",
            )}
          >
            <CalendarPanel />
          </aside>
        )}
      </div>
    </div>
  );
}
