import type { ComponentType } from "react";

import { cn } from "@/shared/lib/cn";

export interface SegmentedOption<T extends string> {
  id: T;
  label: string;
  icon?: ComponentType<{ className?: string }>;
}

interface Props<T extends string> {
  value: T;
  onChange: (value: T) => void;
  options: SegmentedOption<T>[];
  "aria-label": string;
  className?: string;
}

/** Переключатель вариантов в стиле shadcn Tabs. */
export function Segmented<T extends string>({ value, onChange, options, className, ...props }: Props<T>) {
  return (
    <div role="tablist" aria-label={props["aria-label"]} className={cn("inline-flex rounded-lg bg-muted p-1 text-sm", className)}>
      {options.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          role="tab"
          type="button"
          aria-selected={value === id}
          onClick={() => onChange(id)}
          className={cn(
            "inline-flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1 font-medium whitespace-nowrap transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
            value === id ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {Icon && <Icon className="size-4" />}
          {label}
        </button>
      ))}
    </div>
  );
}
