import { fetchSpeech } from "../api/tts";
import { splitForSpeech } from "../lib/text";

/**
 * Озвучка ответов. Текст режется на фрагменты: пока играет один, синтезируется следующий.
 * Если серверный синтез недоступен (нет ключа, ошибка) — говорит голосом браузера (speechSynthesis).
 */
export class Speaker {
  private ctx: AudioContext;
  private source: AudioBufferSourceNode | null = null;
  private controller: AbortController | null = null;
  private serverAvailable = true;

  /** AudioContext создаётся по нажатию кнопки — иначе браузер не даст играть звук. */
  constructor() {
    this.ctx = new AudioContext();
  }

  async speak(text: string): Promise<void> {
    this.stop();
    const controller = new AbortController();
    this.controller = controller;
    const chunks = splitForSpeech(text);
    if (this.ctx.state === "suspended") await this.ctx.resume();

    const fetches: Promise<AudioBuffer | null>[] = [];
    const load = (i: number) => {
      if (i < chunks.length && !fetches[i]) fetches[i] = this.load(chunks[i], controller.signal);
    };

    for (let i = 0; i < chunks.length; i++) {
      if (controller.signal.aborted) return;
      load(i);
      load(i + 1); // следующий фрагмент синтезируется, пока играет текущий
      const buffer = await fetches[i];
      if (controller.signal.aborted) return;
      if (buffer) await this.play(buffer, controller.signal);
      else await this.speakWithBrowser(chunks[i], controller.signal);
    }
  }

  stop() {
    this.controller?.abort();
    this.controller = null;
    try {
      this.source?.stop();
    } catch {
      /* уже остановлен */
    }
    this.source = null;
    if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
  }

  close() {
    this.stop();
    void this.ctx.close();
  }

  private async load(text: string, signal: AbortSignal): Promise<AudioBuffer | null> {
    if (!this.serverAvailable) return null;
    try {
      const wav = await fetchSpeech(text, signal);
      return await this.ctx.decodeAudioData(wav);
    } catch (e) {
      if (signal.aborted) return null;
      // Синтез не настроен или упал — до конца беседы говорим голосом браузера
      console.warn("Серверный синтез недоступен, используем голос браузера", e);
      this.serverAvailable = false;
      return null;
    }
  }

  private play(buffer: AudioBuffer, signal: AbortSignal): Promise<void> {
    return new Promise((resolve) => {
      const source = this.ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(this.ctx.destination);
      source.onended = () => resolve();
      signal.addEventListener("abort", () => resolve(), { once: true });
      this.source = source;
      source.start();
    });
  }

  private speakWithBrowser(text: string, signal: AbortSignal): Promise<void> {
    if (typeof speechSynthesis === "undefined") return Promise.resolve();
    return new Promise((resolve) => {
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "ru-RU";
      const voice = speechSynthesis.getVoices().find((v) => v.lang.startsWith("ru"));
      if (voice) u.voice = voice;
      u.onend = () => resolve();
      u.onerror = () => resolve();
      signal.addEventListener("abort", () => resolve(), { once: true });
      speechSynthesis.speak(u);
    });
  }
}
