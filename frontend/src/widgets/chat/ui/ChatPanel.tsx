import { AudioLines } from "lucide-react";

import { useChat } from "@/features/send-message";
import { Button } from "@/shared/ui/button";
import { FullscreenSpinner } from "@/shared/ui/spinner";
import { Composer } from "./Composer";
import { MessageList } from "./MessageList";

const SUGGESTIONS = [
  "Напомни завтра в 9 утра позвонить врачу",
  "Создай задачу: подготовить презентацию к пятнице",
  "Запланируй встречу с Олегом в среду в 15:00",
  "Что у меня сегодня?",
];

export function ChatPanel() {
  const { messages, sending, loadingHistory, send, updateAction } = useChat();

  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto">
        {loadingHistory && messages.length === 0 ? (
          <FullscreenSpinner />
        ) : messages.length === 0 ? (
          <div className="mx-auto flex h-full max-w-xl flex-col items-center justify-center gap-6 px-4 text-center">
            <div className="flex size-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
              <AudioLines className="size-6" />
            </div>
            <div className="space-y-1">
              <h1 className="text-2xl font-semibold tracking-tight">Чем помочь?</h1>
              <p className="text-sm text-muted-foreground">
                Напишите или нажмите на микрофон — я создам задачу, напоминание или встречу.
              </p>
            </div>
            <div className="grid w-full gap-2 sm:grid-cols-2">
              {SUGGESTIONS.map((s) => (
                <Button
                  key={s}
                  variant="outline"
                  className="h-auto justify-start py-3 text-left whitespace-normal"
                  onClick={() => send(s)}
                >
                  {s}
                </Button>
              ))}
            </div>
          </div>
        ) : (
          <MessageList messages={messages} onActionResolved={updateAction} />
        )}
      </div>
      <Composer onSend={send} disabled={sending} />
    </section>
  );
}
