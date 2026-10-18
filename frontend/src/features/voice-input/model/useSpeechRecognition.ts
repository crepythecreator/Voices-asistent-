import { STT_ENGINE } from "@/shared/config";
import { useBrowserSpeech } from "./useBrowserSpeech";
import { useServerSpeech } from "./useServerSpeech";

/**
 * Хук распознавания речи. Движок выбирается переменной VITE_STT_ENGINE (см. shared/config/env).
 * Выбор делается один раз при загрузке модуля, поэтому правила хуков не нарушаются.
 */
export const useSpeechRecognition = STT_ENGINE === "server" ? useServerSpeech : useBrowserSpeech;
