import { MessageSquare } from "lucide-react";

import { ConversationPanel } from "@/features/voice-conversation";
import { Button } from "@/shared/ui/button";
import { FullscreenSpinner } from "@/shared/ui/spinner";
import type { AssistantState } from "../model/useAssistant";
import { SUGGESTIONS } from "../config/suggestions";
import { Composer } from "./Composer";
import { MessageList } from "./MessageList";

/** Текстовый чат: история, карточки действий, поле ввода. Беседа голосом — компактной панелью снизу. */
export function ChatView({ chat, conversation }: AssistantState) {
  const { messages, sending, loadingHistory, send, updateAction } = chat;

  return (
    <>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {loadingHistory && messages.length === 0 ? (
          <FullscreenSpinner />
        ) : messages.length === 0 ? (
          <div className="mx-auto flex h-full max-w-xl flex-col items-center justify-center gap-6 px-4 text-center">
            <div className="flex size-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
              <MessageSquare className="size-6" />
            </div>
            <div className="space-y-1">
              <h1 className="text-2xl font-semibold tracking-tight">Чем помочь?</h1>
              <p className="text-sm text-muted-foreground">Напишите — я создам задачу, напоминание или встречу.</p>
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
      {conversation.active ? (
        <ConversationPanel
          state={conversation.state}
          transcript={conversation.transcript}
          onInterrupt={conversation.interrupt}
          onStop={conversation.stop}
        />
      ) : (
        <Composer onSend={send} onStartConversation={conversation.start} disabled={sending} />
      )}
    </>
  );
}
