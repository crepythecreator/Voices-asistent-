import { ApiError, transcribe } from "@/shared/api";
import { startRecording, TARGET_SAMPLE_RATE } from "@/shared/lib/recorder";
import { ListenError, type ListenOptions } from "./listenTypes";

// Серверное распознавание не знает, когда фраза закончилась, — это определяем сами по громкости.
// Простой порог по энергии: тишину в начале замеряем и подстраиваем порог под шум в комнате.

const CALIBRATION_SECONDS = 0.3; // замер фонового шума
const MIN_THRESHOLD = 0.012; // громкость тише этого речью не считаем
const MAX_THRESHOLD = 0.05; // и не даём шуму поднять порог так, чтобы тихая речь пропадала
const NOISE_FACTOR = 2.5;
const MIN_SPEECH_SECONDS = 0.25; // короче — щелчок, а не речь
const END_SILENCE_SECONDS = 1.1; // пауза после речи, по которой считаем фразу законченной
const NO_SPEECH_SECONDS = 8; // молчание с самого начала — слушать дальше нет смысла
const MAX_SECONDS = 25; // сервер принимает до ~30 секунд

const rmsOf = (chunk: Float32Array) => {
  let sum = 0;
  for (let i = 0; i < chunk.length; i++) sum += chunk[i] * chunk[i];
  return Math.sqrt(sum / chunk.length);
};

/** Слушает одну фразу: пишет с микрофона, сам ловит конец речи и распознаёт на сервере. */
export async function listenOnceServer({ lang = "ru-RU", signal }: ListenOptions = {}): Promise<string> {
  if (signal?.aborted) return "";

  let finish!: () => void;
  const done = new Promise<void>((resolve) => (finish = resolve));

  let elapsed = 0;
  let noiseSum = 0;
  let noiseTime = 0;
  let speechTime = 0;
  let silenceTime = 0;
  let speaking = false;

  const onChunk = (chunk: Float32Array, sampleRate: number) => {
    const dt = chunk.length / sampleRate;
    elapsed += dt;
    const rms = rmsOf(chunk);

    if (noiseTime < CALIBRATION_SECONDS) {
      noiseSum += rms * dt;
      noiseTime += dt;
    }
    const noise = noiseTime ? noiseSum / noiseTime : 0;
    const threshold = Math.min(MAX_THRESHOLD, Math.max(MIN_THRESHOLD, noise * NOISE_FACTOR));

    if (rms > threshold) {
      speechTime += dt;
      silenceTime = 0;
      if (speechTime >= MIN_SPEECH_SECONDS) speaking = true;
    } else if (speaking) {
      silenceTime += dt;
    } else {
      speechTime = Math.max(0, speechTime - dt); // одиночные всплески шума не копим
    }

    if (speaking && silenceTime >= END_SILENCE_SECONDS) finish();
    else if (!speaking && elapsed >= NO_SPEECH_SECONDS) finish();
    else if (elapsed >= MAX_SECONDS) finish();
  };

  let recording;
  try {
    recording = await startRecording({ onChunk });
  } catch (e) {
    const denied = e instanceof DOMException && e.name === "NotAllowedError";
    throw new ListenError(
      denied ? "Нет доступа к микрофону. Разрешите его в настройках браузера." : "Не удалось включить микрофон.",
      denied ? "not-allowed" : "audio-capture",
    );
  }

  const onAbort = () => finish();
  signal?.addEventListener("abort", onAbort, { once: true });
  await done;
  signal?.removeEventListener("abort", onAbort);

  if (signal?.aborted || !speaking) {
    recording.cancel();
    return "";
  }

  const pcm = await recording.stop();
  try {
    const { text } = await transcribe(pcm, TARGET_SAMPLE_RATE, lang);
    return text.trim();
  } catch (e) {
    throw new ListenError(e instanceof ApiError ? e.message : "Не удалось распознать речь.", "server");
  }
}
