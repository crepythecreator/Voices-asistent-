export class ListenError extends Error {
  constructor(
    message: string,
    /** Код ошибки Web Speech API (`network`, `not-allowed`…) или `server` для серверного распознавания. */
    public code: string = "unknown",
  ) {
    super(message);
  }
}

export interface ListenOptions {
  lang?: string;
  onInterim?: (text: string) => void;
  signal?: AbortSignal;
}
