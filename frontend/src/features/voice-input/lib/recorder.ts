// Запись микрофона в сырой PCM (16 бит, моно), который понимает Yandex SpeechKit (format=lpcm).
// Пишем сами через AudioWorklet, а не MediaRecorder: формат MediaRecorder разный в разных
// браузерах (webm/mp4), а PCM одинаковый везде и не требует перекодирования на бэкенде.

export const TARGET_SAMPLE_RATE = 16000;

const WORKLET = `
class PcmCapture extends AudioWorkletProcessor {
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (ch) this.port.postMessage(ch.slice(0));
    return true;
  }
}
registerProcessor("pcm-capture", PcmCapture);
`;

export interface Recording {
  /** Останавливает запись и возвращает PCM 16 бит, 16 кГц, моно. */
  stop: () => Promise<ArrayBuffer>;
  /** Прерывает запись без результата. */
  cancel: () => void;
}

export async function startRecording(onTick?: (seconds: number) => void): Promise<Recording> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
  });
  // Частоту не задаём: Firefox не умеет подключать микрофон к контексту с другой частотой.
  // Вместо этого понижаем частоту сами в конце записи.
  const ctx = new AudioContext();
  const url = URL.createObjectURL(new Blob([WORKLET], { type: "application/javascript" }));

  try {
    await ctx.audioWorklet.addModule(url);
  } catch (e) {
    stream.getTracks().forEach((t) => t.stop());
    await ctx.close();
    throw e;
  } finally {
    URL.revokeObjectURL(url);
  }

  const source = ctx.createMediaStreamSource(stream);
  const node = new AudioWorkletNode(ctx, "pcm-capture");
  const mute = ctx.createGain();
  mute.gain.value = 0;
  // Узел должен быть подключён к выходу, иначе часть браузеров его не обрабатывает.
  source.connect(node).connect(mute).connect(ctx.destination);

  const chunks: Float32Array[] = [];
  let samples = 0;
  node.port.onmessage = (e: MessageEvent<Float32Array>) => {
    chunks.push(e.data);
    samples += e.data.length;
    onTick?.(samples / ctx.sampleRate);
  };

  const release = () => {
    node.port.onmessage = null;
    source.disconnect();
    node.disconnect();
    stream.getTracks().forEach((t) => t.stop());
    void ctx.close();
  };

  return {
    stop: async () => {
      const rate = ctx.sampleRate;
      release();
      return toPcm16(downsample(concat(chunks, samples), rate, TARGET_SAMPLE_RATE));
    },
    cancel: release,
  };
}

function concat(chunks: Float32Array[], length: number): Float32Array {
  const out = new Float32Array(length);
  let offset = 0;
  for (const c of chunks) {
    out.set(c, offset);
    offset += c.length;
  }
  return out;
}

/** Понижение частоты усреднением отсчётов (заодно работает как простой ФНЧ). */
function downsample(input: Float32Array, from: number, to: number): Float32Array {
  if (from === to) return input;
  const ratio = from / to;
  const out = new Float32Array(Math.floor(input.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(Math.floor((i + 1) * ratio), input.length);
    let sum = 0;
    for (let j = start; j < end; j++) sum += input[j];
    out[i] = sum / Math.max(1, end - start);
  }
  return out;
}

function toPcm16(input: Float32Array): ArrayBuffer {
  const view = new DataView(new ArrayBuffer(input.length * 2));
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return view.buffer;
}
