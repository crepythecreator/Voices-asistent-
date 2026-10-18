import { useState } from "react";
import { Check, X } from "lucide-react";

import type { ProposedAction } from "@/entities/action";
import { invalidateEvents } from "@/entities/event";
import { ApiError } from "@/shared/api";
import { Button } from "@/shared/ui/button";
import { Spinner } from "@/shared/ui/spinner";
import { resolveAction, type Decision } from "../api/resolveAction";

interface Props {
  action: ProposedAction;
  onResolved: (action: ProposedAction) => void;
}

export function ActionDecision({ action, onResolved }: Props) {
  const [busy, setBusy] = useState<Decision | null>(null);
  const [error, setError] = useState<string | null>(null);

  const decide = async (decision: Decision) => {
    setBusy(decision);
    setError(null);
    try {
      const updated = await resolveAction(action, decision);
      onResolved(updated);
      if (updated.status === "applied") invalidateEvents();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось выполнить. Попробуйте ещё раз.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex gap-2">
        <Button size="sm" onClick={() => decide("confirm")} disabled={busy !== null}>
          {busy === "confirm" ? <Spinner className="size-4 text-current" /> : <Check />}
          Подтвердить
        </Button>
        <Button size="sm" variant="ghost" onClick={() => decide("reject")} disabled={busy !== null}>
          {busy === "reject" ? <Spinner className="size-4" /> : <X />}
          Отклонить
        </Button>
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
