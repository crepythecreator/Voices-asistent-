import { useCallback, useState } from "react";

export type AssistantMode = "voice" | "chat";

const KEY = "assistant-mode";

function read(): AssistantMode {
  try {
    return localStorage.getItem(KEY) === "chat" ? "chat" : "voice";
  } catch {
    return "voice";
  }
}

/** Режим «Голос» (по умолчанию) или «Чат». Выбор запоминается в этом браузере. */
export function useAssistantMode() {
  const [mode, setModeState] = useState<AssistantMode>(read);

  const setMode = useCallback((next: AssistantMode) => {
    setModeState(next);
    try {
      localStorage.setItem(KEY, next);
    } catch {
      /* localStorage недоступен — просто не запомним */
    }
  }, []);

  return { mode, setMode };
}
