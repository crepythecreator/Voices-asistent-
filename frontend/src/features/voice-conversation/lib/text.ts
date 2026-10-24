/** Разбивает ответ на фрагменты по предложениям: первый озвучивается, пока синтезируется следующий. */
export function splitForSpeech(text: string, maxLength = 300): string[] {
  const clean = text.replace(/[*_`#>]+/g, "").replace(/\s+/g, " ").trim();
  if (!clean) return [];
  const sentences = clean.match(/[^.!?…]+[.!?…]+["»)]*|[^.!?…]+$/g) ?? [clean];

  const chunks: string[] = [];
  let current = "";
  for (const s of sentences.map((x) => x.trim()).filter(Boolean)) {
    // Короткие предложения склеиваем — меньше запросов и пауз между ними
    if (current && (current + " " + s).length > maxLength) {
      chunks.push(current);
      current = s;
    } else {
      current = current ? `${current} ${s}` : s;
    }
    if (current.length >= 40 && chunks.length === 0) {
      // Первый фрагмент держим коротким — чтобы ассистент начал говорить быстрее
      chunks.push(current);
      current = "";
    }
  }
  if (current) chunks.push(current);
  return chunks;
}

const normalize = (t: string) =>
  t
    .toLowerCase()
    .replace(/ё/g, "е")
    .replace(/[^a-zа-я\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

// Подтверждение — только короткой однозначной фразой: длинная фраза с «да» внутри — это новый запрос
const YES = new Set(["да", "ага", "угу", "конечно", "давай", "подтверждаю", "да подтверждаю", "подтвердить", "да давай", "верно", "все верно", "да конечно", "окей", "ок", "хорошо", "да хорошо"]);
const NO = new Set(["нет", "не надо", "не нужно", "отмена", "отмени", "отменить", "нет спасибо", "не", "неверно", "нет не надо"]);
const STOP = ["стоп", "хватит", "закончи беседу", "завершить беседу", "закончить беседу", "выход", "пока"];

export const isYes = (text: string) => YES.has(normalize(text));
export const isNo = (text: string) => NO.has(normalize(text));
export const isStop = (text: string) => STOP.includes(normalize(text));
