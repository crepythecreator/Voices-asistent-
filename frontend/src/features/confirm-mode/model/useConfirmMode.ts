import { useState } from "react";

import type { ConfirmMode, User } from "@/entities/user";
import { errorMessage } from "@/shared/lib/errorMessage";
import { setConfirmMode } from "../api/setConfirmMode";

/** Смена режима подтверждения. onChange получает обновлённого пользователя с сервера. */
export function useConfirmMode(user: User, onChange: (user: User) => void) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const change = async (mode: ConfirmMode) => {
    if (mode === user.confirmMode || busy) return;
    setBusy(true);
    setError(null);
    try {
      onChange(await setConfirmMode(user, mode));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return { mode: user.confirmMode, change, busy, error };
}
