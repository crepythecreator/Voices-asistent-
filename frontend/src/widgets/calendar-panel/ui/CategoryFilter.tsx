import { CATEGORIES, CATEGORY_ORDER, type EventCategory } from "@/entities/event";
import { cn } from "@/shared/lib/cn";

interface Props {
  hidden: Set<EventCategory>;
  onToggle: (category: EventCategory) => void;
}

/** Фильтр по типам — он же легенда цветов. */
export function CategoryFilter({ hidden, onToggle }: Props) {
  return (
    <div className="flex flex-wrap gap-1.5" role="group" aria-label="Показывать">
      {CATEGORY_ORDER.map((c) => {
        const on = !hidden.has(c);
        return (
          <button
            key={c}
            type="button"
            aria-pressed={on}
            onClick={() => onToggle(c)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
              on ? "bg-background text-foreground" : "border-dashed text-muted-foreground opacity-60 hover:opacity-100",
            )}
            title={on ? `Скрыть: ${CATEGORIES[c].plural.toLowerCase()}` : `Показать: ${CATEGORIES[c].plural.toLowerCase()}`}
          >
            <span className={cn("size-2 rounded-full", CATEGORIES[c].dot, !on && "opacity-40")} />
            {CATEGORIES[c].plural}
          </button>
        );
      })}
    </div>
  );
}
