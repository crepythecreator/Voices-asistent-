import { AudioLines, CalendarDays } from "lucide-react";

import { UserMenu } from "@/features/auth";
import { ThemeToggle } from "@/features/toggle-theme";
import { Button } from "@/shared/ui/button";

interface Props {
  calendarOpen: boolean;
  onToggleCalendar: () => void;
}

export function Header({ calendarOpen, onToggleCalendar }: Props) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-2 border-b px-4">
      <div className="flex items-center gap-2 font-semibold">
        <AudioLines className="size-5" />
        <span>Ассистент</span>
      </div>
      <div className="flex items-center gap-1">
        <Button
          variant={calendarOpen ? "secondary" : "ghost"}
          size="icon"
          onClick={onToggleCalendar}
          aria-label="Календарь"
          aria-pressed={calendarOpen}
        >
          <CalendarDays />
        </Button>
        <ThemeToggle />
        <div className="ml-1">
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
