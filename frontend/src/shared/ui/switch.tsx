import * as React from "react";

import { cn } from "@/shared/lib/cn";

interface SwitchProps extends Omit<React.ComponentProps<"button">, "onChange"> {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}

/** Переключатель в стиле shadcn/ui (role="switch"). */
function Switch({ checked, onCheckedChange, className, disabled, ...props }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onCheckedChange(!checked)}
      className={cn(
        "inline-flex h-5 w-9 shrink-0 items-center rounded-full border border-transparent shadow-xs outline-none transition-colors focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50",
        checked ? "bg-primary" : "bg-input dark:bg-input/80",
        className,
      )}
      {...props}
    >
      <span
        className={cn(
          "pointer-events-none block size-4 rounded-full bg-background shadow-sm ring-0 transition-transform",
          checked ? "translate-x-4 dark:bg-primary-foreground" : "translate-x-0.5 dark:bg-foreground",
        )}
      />
    </button>
  );
}

export { Switch };
