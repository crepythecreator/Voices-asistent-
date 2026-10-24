export interface SpeechOptions {
  lang?: string;
  /**
   * Браузерный движок получил ошибку `network` (Web Speech API недоступен, как в Яндекс Браузере).
   * Вернуть true — ошибка обработана (например, переключились на сервер), показывать её не нужно.
   */
  onNetworkError?: () => boolean;
  /** Вызывается, когда распознавание завершилось и есть итоговый текст. */
  onFinal?: (text: string) => void;
}

/** Общий интерфейс движков распознавания речи. */
export interface SpeechRecognitionApi {
  supported: boolean;
  /** Идёт запись с микрофона. */
  listening: boolean;
  /** Запись закончена, ждём текст от сервера. */
  processing: boolean;
  /** Промежуточный текст во время записи (только у браузерного движка). */
  transcript: string;
  error: string | null;
  start: () => void;
  stop: () => void;
  toggle: () => void;
}
