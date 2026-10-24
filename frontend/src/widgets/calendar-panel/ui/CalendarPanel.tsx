import { useState } from "react";
import { CalendarDays, List } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Segmented } from "@/shared/ui/segmented";
import { useCalendarPrefs } from "../model/useCalendarPrefs";
import { useMonthEvents } from "../model/useMonthEvents";
import { useUpcomingEvents } from "../model/useUpcomingEvents";
import { CategoryFilter } from "./CategoryFilter";
import { ListView } from "./ListView";
import { MonthView } from "./MonthView";

/** Календарь: «Месяц» — сетка с точками и события дня, «Список» — доска предстоящих событий. */
export function CalendarPanel() {
  const { view, setView, hidden, toggleCategory, visible } = useCalendarPrefs();
  const [selected, setSelected] = useState<Date>(() => new Date());
  const [month, setMonth] = useState<Date>(() => new Date());

  // Грузим только для активного вида — запросы к календарям Яндекса и Google небыстрые
  const monthData = useMonthEvents(month, view === "month");
  const upcoming = useUpcomingEvents(view === "list");

  const goToday = () => {
    const now = new Date();
    setSelected(now);
    setMonth(now);
    // В списке «Сегодня» — это начало ленты
    document.getElementById("calendar-top")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="flex flex-col gap-3">
      <div id="calendar-top" className="flex items-center gap-2">
        <Segmented
          aria-label="Вид календаря"
          value={view}
          onChange={setView}
          className="flex-1"
          options={[
            { id: "month", label: "Месяц", icon: CalendarDays },
            { id: "list", label: "Список", icon: List },
          ]}
        />
        <Button variant="outline" size="sm" onClick={goToday}>
          Сегодня
        </Button>
      </div>

      <CategoryFilter hidden={hidden} onToggle={toggleCategory} />

      {view === "month" ? (
        <MonthView
          events={monthData.events.filter(visible)}
          loading={monthData.loading}
          month={month}
          onMonthChange={setMonth}
          selected={selected}
          onSelect={setSelected}
        />
      ) : (
        <ListView
          events={upcoming.events.filter(visible)}
          loading={upcoming.loading}
          days={upcoming.days}
          onLoadMore={upcoming.loadMore}
        />
      )}
    </div>
  );
}
