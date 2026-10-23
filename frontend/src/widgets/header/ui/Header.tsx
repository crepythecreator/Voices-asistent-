import { AudioLines, CalendarDays } from "lucide-react";
import { Link } from "react-router";

import { UserMenu } from "@/features/auth";
import { ThemeToggle } from "@/features/toggle-theme";
import { routes } from "@/shared/config";
import { Button } from "@/shared/ui/button";

interface Props {
  /** Кнопка календаря — только на странице ассистента. */
  calendarOpen?: boolean;
  onToggleCalendar?: () => void;
}

export function Header({ calendarOpen, onToggleCalendar }: Props) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-2 border-b px-4">
      <Link to={routes.home} className="flex items-center gap-2 font-semibold">
        <AudioLines className="size-5" />
        <span>Ассистент</span>
      </Link>
      <div className="flex items-center gap-1">
        {onToggleCalendar && (
          <Button
            variant={calendarOpen ? "secondary" : "ghost"}
            size="icon"
            onClick={onToggleCalendar}
            aria-label="Календарь"
            aria-pressed={calendarOpen}
          >
            <CalendarDays />
          </Button>
        )}
        <ThemeToggle />
        <div className="ml-1">
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
