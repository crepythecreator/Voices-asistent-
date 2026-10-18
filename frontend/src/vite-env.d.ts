/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "true" — работать на моках без бэкенда. */
  readonly VITE_USE_MOCKS?: string;
  /** "browser" (по умолчанию) или "server" — движок распознавания речи. */
  readonly VITE_STT_ENGINE?: string;
}
