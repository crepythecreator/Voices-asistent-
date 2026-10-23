import type { ReactNode } from "react";
import { ArrowLeft, CheckCircle2 } from "lucide-react";
import { Link, useSearchParams } from "react-router";

import { UserAvatar } from "@/entities/user";
import { useAuth } from "@/features/auth";
import { PasswordForm } from "@/features/change-password";
import { ConnectionsSettings } from "@/features/manage-connections";
import { routes } from "@/shared/config";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { FormError } from "@/shared/ui/form-error";
import { Header } from "@/widgets/header";

// Коды, с которыми бэкенд возвращает после подключения аккаунта: /settings?connected=… | ?error=…
const PROVIDER_NAMES: Record<string, string> = { yandex: "Яндекс", google: "Google" };
const ERRORS: Record<string, string> = {
  access_denied: "Вы не выдали доступ — аккаунт не подключён.",
  already_linked: "Этот аккаунт уже привязан к другому пользователю.",
  other_account_connected: "У вас уже подключён другой аккаунт этого сервиса. Сначала отключите его.",
  invalid_state: "Сессия подключения устарела. Попробуйте ещё раз.",
};

function Section({ title, description, children }: { title: string; description?: string; children: ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export function SettingsPage() {
  const { user, refresh } = useAuth();
  const [params] = useSearchParams();
  const connected = params.get("connected");
  const error = params.get("error");

  if (!user) return null;

  return (
    <div className="flex h-full flex-col">
      <Header />
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-4 py-6">
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon-sm" asChild aria-label="К ассистенту">
              <Link to={routes.home}>
                <ArrowLeft />
              </Link>
            </Button>
            <h1 className="text-xl font-semibold tracking-tight">Настройки</h1>
          </div>

          {connected && (
            <div className="flex items-center gap-2 rounded-lg border bg-muted/50 px-3 py-2.5 text-sm">
              <CheckCircle2 className="size-4 shrink-0" />
              {PROVIDER_NAMES[connected] ?? connected} подключён.
            </div>
          )}
          <FormError message={error ? (ERRORS[error] ?? "Не удалось подключить аккаунт. Попробуйте ещё раз.") : null} />

          <Section title="Профиль">
            <div className="flex items-center gap-3">
              <UserAvatar user={user} />
              <div className="min-w-0">
                <div className="font-medium">{user.name}</div>
                <div className="truncate text-sm text-muted-foreground">{user.email ?? "Почта не указана"}</div>
              </div>
            </div>
          </Section>

          <Section
            title="Аккаунты и календари"
            description="Подключите Яндекс и Google: через них можно входить, а ассистент будет записывать события в их календари и учитывать вашу занятость."
          >
            <ConnectionsSettings />
          </Section>

          <Section title={user.hasPassword ? "Пароль" : "Вход по паролю"}>
            <PasswordForm hasPassword={user.hasPassword} email={user.email} onSuccess={refresh} />
          </Section>
        </div>
      </main>
    </div>
  );
}
