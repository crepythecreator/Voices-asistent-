import type { ReactNode } from "react";
import { AudioLines, CalendarDays, Mic, Sparkles } from "lucide-react";

import { ThemeToggle } from "@/features/toggle-theme";

const FEATURES = [
  { icon: Mic, title: "Голосом или текстом", text: "Продиктуйте задачу — ассистент поймёт и запишет." },
  { icon: CalendarDays, title: "Яндекс и Google Календарь", text: "Встречи и напоминания попадут в ваши календари." },
  { icon: Sparkles, title: "Понимает обычную речь", text: "«Напомни завтра в 9 позвонить врачу» — и готово." },
];

interface Props {
  title: string;
  description: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}

/** Раскладка страниц входа и регистрации: форма слева, описание продукта справа. */
export function AuthLayout({ title, description, children, footer }: Props) {
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
              <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
              <p className="text-sm text-balance text-muted-foreground">{description}</p>
            </div>
            {children}
            {footer && <div className="text-center text-sm text-muted-foreground">{footer}</div>}
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
