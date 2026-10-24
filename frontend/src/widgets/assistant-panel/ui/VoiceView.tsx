import { Hand, MessageSquare, Square } from "lucide-react";

import { ActionCard } from "@/entities/action";
import type { Message } from "@/entities/message";
import { ActionDecision } from "@/features/confirm-action";
import { STATE_LABELS, speechRecognitionSupported, VoiceOrb } from "@/features/voice-conversation";
import { Button } from "@/shared/ui/button";
import type { AssistantState } from "../model/useAssistant";
import { SUGGESTIONS } from "../config/suggestions";

interface Props extends AssistantState {
  onOpenChat: () => void;
}

/** Последний обмен репликами: что сказал пользователь и что ответил ассистент. */
function lastExchange(messages: Message[]): { user?: Message; reply?: Message } {
  let reply: Message | undefined;
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i];
    if (m.role === "assistant" && !reply) reply = m;
    if (m.role === "user") return { user: m, reply };
  }
  return { reply };
}

/** Голосовой режим — основной экран: большая кнопка, статус, последняя реплика и подтверждения. */
export function VoiceView({ chat, conversation, onOpenChat }: Props) {
  const { state, transcript, error, active } = conversation;
  const supported = speechRecognitionSupported();
  const { user, reply } = lastExchange(chat.messages);
  const pending = reply?.actions?.filter((a) => a.status === "pending") ?? [];

  const onOrbClick = state === "idle" ? conversation.start : state === "speaking" ? conversation.interrupt : undefined;

  // Пока пользователь говорит, показываем его фразу; иначе — последнюю отправленную
  const userText = state === "listening" ? transcript : user?.text;

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto flex min-h-full w-full max-w-xl flex-col items-center justify-center gap-8 px-4 py-8 text-center">
        <VoiceOrb state={state} onClick={onOrbClick} disabled={!supported} />

        <div className="space-y-2" aria-live="polite">
          <h1 className="text-2xl font-semibold tracking-tight">{STATE_LABELS[state]}</h1>
          {state === "idle" && (
            <p className="text-sm text-muted-foreground">
              {supported
                ? "Нажмите на кнопку и скажите, что нужно сделать. Я отвечу голосом."
                : "Этот браузер не умеет распознавать речь. Откройте сайт в Google Chrome или Safari — или пишите в чат."}
            </p>
          )}
          {state === "listening" && !transcript && (
            <p className="text-sm text-muted-foreground">Говорите — я отвечу, когда вы замолчите</p>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        {active && (
          <div className="flex gap-2">
            {state === "speaking" && (
              <Button variant="outline" onClick={conversation.interrupt}>
                <Hand />
                Перебить
              </Button>
            )}
            <Button variant="ghost" onClick={conversation.stop}>
              <Square className="fill-current" />
              Завершить
            </Button>
          </div>
        )}

        {(userText || reply) && (
          <div className="flex w-full flex-col gap-3 text-left">
            {userText && (
              <p className="self-end rounded-2xl bg-primary px-4 py-2 text-sm text-primary-foreground">{userText}</p>
            )}
            {reply && !reply.pending && state !== "listening" && (
              <p className="max-h-48 overflow-y-auto rounded-2xl bg-muted px-4 py-2 text-sm leading-relaxed whitespace-pre-wrap">
                {reply.text}
              </p>
            )}
            {state !== "listening" &&
              pending.map((a) => (
                <ActionCard key={a.id} action={a} controls={<ActionDecision action={a} onResolved={chat.updateAction} />} />
              ))}
            {pending.length > 0 && active && (
              <p className="text-center text-xs text-muted-foreground">Скажите «да» или «нет» — или нажмите кнопку</p>
            )}
          </div>
        )}

        {state === "idle" && !reply && supported && (
          <div className="space-y-2 text-sm text-muted-foreground">
            <p>Например:</p>
            <ul className="space-y-1">
              {SUGGESTIONS.slice(0, 3).map((s) => (
                <li key={s}>«{s}»</li>
              ))}
            </ul>
          </div>
        )}

        {!supported && (
          <Button variant="outline" onClick={onOpenChat}>
            <MessageSquare />
            Открыть чат
          </Button>
        )}
      </div>
    </div>
  );
}
