import { useState, type KeyboardEvent } from "react";
import { ArrowUp, AudioLines } from "lucide-react";

import type { MessageSource } from "@/entities/message";
import { useSpeechRecognition, VoiceButton, voiceStatus } from "@/features/voice-input";
import { cn } from "@/shared/lib/cn";
import { Button } from "@/shared/ui/button";
import { Textarea } from "@/shared/ui/textarea";

interface Props {
  onSend: (text: string, source: MessageSource) => void;
  /** Включить режим беседы голосом. */
  onStartConversation?: () => void;
  disabled?: boolean;
}

export function Composer({ onSend, onStartConversation, disabled }: Props) {
  const [value, setValue] = useState("");
  const [fromVoice, setFromVoice] = useState(false);

  const voice = useSpeechRecognition({
    // Итог распознавания кладём в поле ввода — пользователь может поправить перед отправкой.
    onFinal: (text) => {
      setValue((prev) => (prev ? `${prev} ${text}` : text));
      setFromVoice(true);
    },
  });

  const shown = voice.listening ? [value, voice.transcript].filter(Boolean).join(" ") : value;

  const submit = () => {
    if (!value.trim() || disabled) return;
    onSend(value, fromVoice ? "voice" : "text");
    setValue("");
    setFromVoice(false);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-4 pb-4">
      <div
        className={cn(
          "rounded-2xl border bg-background p-2 shadow-sm transition-shadow focus-within:ring-[3px] focus-within:ring-ring/30",
          voice.listening && "ring-[3px] ring-red-500/30",
        )}
      >
        <Textarea
          value={shown}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          readOnly={voice.listening}
          placeholder={voice.listening ? "Говорите…" : "Напишите или продиктуйте задачу, напоминание или встречу"}
          rows={1}
          className="max-h-40 min-h-10 resize-none border-0 shadow-none focus-visible:ring-0"
        />
        <div className="flex items-center justify-between gap-2 pt-1">
          <span className="truncate px-2 text-xs text-muted-foreground">
            {voiceStatus(voice) ?? "Enter — отправить, Shift+Enter — новая строка"}
          </span>
          <div className="flex shrink-0 gap-1">
            {onStartConversation && (
              <Button
                type="button"
                size="icon-sm"
                variant="ghost"
                onClick={onStartConversation}
                disabled={disabled || voice.listening || voice.processing}
                aria-label="Беседа голосом"
                title="Беседа голосом: говорите — ассистент ответит голосом"
              >
                <AudioLines />
              </Button>
            )}
            <VoiceButton voice={voice} />
            <Button
              type="button"
              size="icon-sm"
              className="rounded-full"
              onClick={submit}
              disabled={disabled || voice.listening || voice.processing || !value.trim()}
              aria-label="Отправить"
            >
              <ArrowUp />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
