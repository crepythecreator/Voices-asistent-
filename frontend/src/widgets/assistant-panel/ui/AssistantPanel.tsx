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

  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col">
      <div className="flex shrink-0 justify-center pt-3">
        <ModeSwitch mode={mode} onChange={setMode} />
      </div>
      {mode === "voice" ? (
        <VoiceView {...assistant} onOpenChat={() => setMode("chat")} />
      ) : (
        <ChatView {...assistant} />
      )}
    </section>
  );
}
