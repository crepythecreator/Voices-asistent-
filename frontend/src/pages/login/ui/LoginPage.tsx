import { Link, useSearchParams } from "react-router";

import { LoginForm, OAuthButtons } from "@/features/auth";
import { routes, safeRedirectPath } from "@/shared/config";
import { FormError } from "@/shared/ui/form-error";
import { AuthLayout } from "@/widgets/auth-layout";

// Коды ошибок, с которыми бэкенд возвращает на /login?error=…
const ERRORS: Record<string, string> = {
  access_denied: "Вы отменили вход. Чтобы продолжить, разрешите доступ.",
  invalid_state: "Сессия входа устарела. Попробуйте ещё раз.",
  other_account_connected: "К аккаунту с этой почтой уже привязан другой аккаунт этого сервиса.",
};
const DEFAULT_ERROR = "Не удалось войти. Попробуйте ещё раз.";

export function LoginPage() {
  const [params] = useSearchParams();
  const next = safeRedirectPath(params.get("next"));
  const errorCode = params.get("error");
  const nextQuery = params.get("next") ? `?${new URLSearchParams({ next })}` : "";

  return (
    <AuthLayout
      title="Вход"
      description="Войдите по почте и паролю или через Яндекс ID и Google."
      footer={
        <>
          Нет аккаунта?{" "}
          <Link to={`${routes.register}${nextQuery}`} className="font-medium text-foreground underline underline-offset-4">
            Зарегистрироваться
          </Link>
        </>
      }
    >
      <FormError message={errorCode ? (ERRORS[errorCode] ?? DEFAULT_ERROR) : null} />
      <LoginForm />
      <OAuthButtons next={next} />
    </AuthLayout>
  );
}
