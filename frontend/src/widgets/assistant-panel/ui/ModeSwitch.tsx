import { MessageSquare, Mic } from "lucide-react";

import { Segmented } from "@/shared/ui/segmented";
import type { AssistantMode } from "../model/useAssistantMode";

export function ModeSwitch({ mode, onChange }: { mode: AssistantMode; onChange: (mode: AssistantMode) => void }) {
  return (
    <Segmented
      aria-label="Режим"
      value={mode}
      onChange={onChange}
      options={[
        { id: "voice", label: "Голос", icon: Mic },
        { id: "chat", label: "Чат", icon: MessageSquare },
      ]}
    />
  );
}
