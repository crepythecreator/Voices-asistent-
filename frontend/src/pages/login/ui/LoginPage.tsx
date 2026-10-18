import { AlertCircle, AudioLines, CalendarDays, Mic, Sparkles } from "lucide-react";
import { useSearchParams } from "react-router";

import { YandexLoginButton } from "@/features/auth";
import { ThemeToggle } from "@/features/toggle-theme";
import { safeRedirectPath } from "@/shared/config";

// Коды ошибок, с которыми бэкенд возвращает на /login?error=…
const ERRORS: Record<string, string> = {
  access_denied: "Вы отменили вход. Чтобы продолжить, разрешите доступ к Яндекс ID.",
  invalid_state: "Сессия входа устарела. Попробуйте ещё раз.",
};
const DEFAULT_ERROR = "Не удалось войти через Яндекс. Попробуйте ещё раз.";

const FEATURES = [
  { icon: Mic, title: "Голосом или текстом", text: "Продиктуйте задачу — ассистент поймёт и запишет." },
  { icon: CalendarDays, title: "Всё в календаре", text: "Встречи, напоминания и задачи в одном месте." },
  { icon: Sparkles, title: "Понимает обычную речь", text: "«Напомни завтра в 9 позвонить врачу» — и готово." },
];

export function LoginPage() {
  const [params] = useSearchParams();
  const next = safeRedirectPath(params.get("next"));
  const errorCode = params.get("error");
  const error = errorCode ? (ERRORS[errorCode] ?? DEFAULT_ERROR) : null;

  return (
    <div className="grid min-h-full lg:grid-cols-2">
      <div className="flex flex-col gap-4 p-6 md:p-10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 font-semibold">
            <div className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <AudioLines className="size-4" />
            </div>
            Ассистент
          </div>
          <ThemeToggle />
        </div>

        <div className="flex flex-1 items-center justify-center">
          <div className="flex w-full max-w-sm flex-col gap-6">
            <div className="flex flex-col gap-2 text-center">
              <h1 className="text-2xl font-semibold tracking-tight">Вход и регистрация</h1>
              <p className="text-sm text-balance text-muted-foreground">
                Войдите через Яндекс ID. Если вы здесь впервые, аккаунт создастся автоматически.
              </p>
            </div>

            {error && (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive"
              >
                <AlertCircle className="mt-0.5 size-4 shrink-0" />
                {error}
              </div>
            )}

            <YandexLoginButton next={next} />

            <p className="text-center text-xs text-balance text-muted-foreground">
              Мы получим только ваше имя, почту и аватар. Пароль от Яндекса остаётся у Яндекса.
            </p>
          </div>
        </div>
      </div>

      <div className="hidden flex-col justify-center gap-8 border-l bg-muted/50 p-12 lg:flex">
        <div className="max-w-md space-y-2">
          <h2 className="text-3xl font-semibold tracking-tight">Ваш голосовой помощник для дел и встреч</h2>
          <p className="text-muted-foreground">Скажите, что нужно сделать, — остальное ассистент возьмёт на себя.</p>
        </div>
        <ul className="flex max-w-md flex-col gap-5">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <li key={title} className="flex gap-4">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-lg border bg-background">
                <Icon className="size-5" />
              </div>
              <div>
                <div className="font-medium">{title}</div>
                <div className="text-sm text-muted-foreground">{text}</div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
