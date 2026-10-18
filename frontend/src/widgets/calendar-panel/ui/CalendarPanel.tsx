import { useState } from "react";

import { EventCard } from "@/entities/event";
import { dayFormat, dayKey } from "@/shared/lib/format";
import { Calendar } from "@/shared/ui/calendar";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { useMonthEvents } from "../model/useMonthEvents";

export function CalendarPanel() {
  const [selected, setSelected] = useState<Date>(new Date());
  const [month, setMonth] = useState<Date>(new Date());
  const { loading, byDay, daysWithEvents } = useMonthEvents(month);

  const dayEvents = byDay.get(dayKey(selected)) ?? [];

  return (
    <div className="flex flex-col gap-4">
      <Card className="py-3">
        <CardContent className="px-3">
          <Calendar
            mode="single"
            required
            selected={selected}
            onSelect={setSelected}
            month={month}
            onMonthChange={setMonth}
            modifiers={{ hasEvents: daysWithEvents }}
            modifiersClassNames={{
              hasEvents:
                "after:absolute after:bottom-1 after:left-1/2 after:size-1 after:-translate-x-1/2 after:rounded-full after:bg-primary [&[aria-selected]]:after:bg-primary-foreground",
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="first-letter:uppercase">{dayFormat.format(selected)}</CardTitle>
          <CardDescription>
            {loading ? "Загрузка…" : dayEvents.length ? `Событий: ${dayEvents.length}` : "Ничего не запланировано"}
          </CardDescription>
        </CardHeader>
        {dayEvents.length > 0 && (
          <CardContent className="flex flex-col gap-2">
            {dayEvents.map((e) => (
              <EventCard key={e.id} event={e} />
            ))}
          </CardContent>
        )}
      </Card>
    </div>
  );
}
