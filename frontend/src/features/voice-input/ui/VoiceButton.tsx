import { Loader2, Mic, Square } from "lucide-react";

import { cn } from "@/shared/lib/cn";
import { Button } from "@/shared/ui/button";
import type { SpeechRecognitionApi } from "../model/types";

export function VoiceButton({ voice }: { voice: SpeechRecognitionApi }) {
  return (
    <Button
      type="button"
      size="icon-sm"
      variant={voice.listening ? "destructive" : "ghost"}
      onClick={voice.toggle}
      disabled={!voice.supported || voice.processing}
      aria-label={voice.listening ? "Остановить запись" : "Голосовой ввод"}
      className={cn(voice.listening && "animate-pulse")}
    >
      {voice.processing ? (
        <Loader2 className="animate-spin" />
      ) : voice.listening ? (
        <Square className="fill-current" />
      ) : (
        <Mic />
      )}
    </Button>
  );
}

/** Подсказка о состоянии записи; null — показывать нечего. */
export function voiceStatus(voice: SpeechRecognitionApi): string | null {
  if (voice.error) return voice.error;
  if (voice.listening) return "Идёт запись — нажмите ещё раз, чтобы остановить";
  if (voice.processing) return "Распознаю речь…";
  if (!voice.supported) return "Голосовой ввод не поддерживается этим браузером";
  return null;
}
