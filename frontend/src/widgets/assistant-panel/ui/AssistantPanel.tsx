import { useAuth } from "@/features/auth";
import { ConfirmModeToggle } from "@/features/confirm-mode";
import { useAssistant } from "../model/useAssistant";
import { useAssistantMode } from "../model/useAssistantMode";
import { ChatView } from "./ChatView";
import { ModeSwitch } from "./ModeSwitch";
import { VoiceView } from "./VoiceView";

/**
 * Ассистент: голосовой режим — основной, чат — по желанию. Оба режима работают с одной историей,
 * а начатая беседа продолжается при переключении (в чате — компактной панелью снизу).
 */
export function AssistantPanel() {
  const assistant = useAssistant();
  const { mode, setMode } = useAssistantMode();
  const { user, setUser } = useAuth();

  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col">
      <div className="grid shrink-0 grid-cols-[1fr_auto_1fr] items-center gap-2 px-3 pt-3">
        <span />
        <ModeSwitch mode={mode} onChange={setMode} />
        <div className="flex justify-end">{user && <ConfirmModeToggle user={user} onChange={setUser} />}</div>
      </div>
      {mode === "voice" ? (
        <VoiceView {...assistant} onOpenChat={() => setMode("chat")} />
      ) : (
        <ChatView {...assistant} />
      )}
    </section>
  );
}
