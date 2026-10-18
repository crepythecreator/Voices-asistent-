import * as React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { DayPicker, getDefaultClassNames } from "react-day-picker";
import { ru } from "react-day-picker/locale";

import { buttonVariants } from "./button";
import { cn } from "@/shared/lib/cn";

function Calendar({ className, classNames, showOutsideDays = true, ...props }: React.ComponentProps<typeof DayPicker>) {
  const defaults = getDefaultClassNames();

  return (
    <DayPicker
      locale={ru}
      showOutsideDays={showOutsideDays}
      className={cn("p-1", className)}
      classNames={{
        root: cn("w-full", defaults.root),
        months: "relative flex flex-col",
        month: "flex w-full flex-col gap-3",
        nav: "absolute inset-x-0 top-0 flex items-center justify-between",
        button_previous: cn(buttonVariants({ variant: "ghost", size: "icon-sm" })),
        button_next: cn(buttonVariants({ variant: "ghost", size: "icon-sm" })),
        month_caption: "flex h-8 items-center justify-center",
        caption_label: "text-sm font-medium capitalize",
        month_grid: "w-full border-collapse",
        weekdays: "flex",
        weekday: "flex-1 text-[0.8rem] font-normal text-muted-foreground capitalize",
        week: "mt-1 flex w-full",
        day: "relative flex-1 p-0 text-center aspect-square",
        day_button: cn(
          buttonVariants({ variant: "ghost" }),
          "size-full min-w-8 p-0 font-normal aria-selected:opacity-100",
        ),
        selected: "[&>button]:bg-primary [&>button]:text-primary-foreground [&>button]:hover:bg-primary",
        today: "[&>button]:bg-accent [&>button]:font-semibold",
        outside: "text-muted-foreground opacity-50",
        disabled: "text-muted-foreground opacity-50",
        hidden: "invisible",
        ...classNames,
      }}
      components={{
        Chevron: ({ orientation }) =>
          orientation === "left" ? <ChevronLeft className="size-4" /> : <ChevronRight className="size-4" />,
      }}
      {...props}
    />
  );
}

export { Calendar };
