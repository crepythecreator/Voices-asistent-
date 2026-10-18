import { Loader2 } from "lucide-react";

import { cn } from "@/shared/lib/cn";

function Spinner({ className }: { className?: string }) {
  return <Loader2 role="status" aria-label="Загрузка" className={cn("size-5 animate-spin text-muted-foreground", className)} />;
}

/** Спиннер на весь экран — пока проверяем сессию. */
function FullscreenSpinner() {
  return (
    <div className="flex h-full items-center justify-center">
      <Spinner className="size-6" />
    </div>
  );
}

export { Spinner, FullscreenSpinner };
