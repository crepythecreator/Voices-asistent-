import { Link, useSearchParams } from "react-router";

import { OAuthButtons, RegisterForm } from "@/features/auth";
import { routes, safeRedirectPath } from "@/shared/config";
import { AuthLayout } from "@/widgets/auth-layout";

export function RegisterPage() {
  const [params] = useSearchParams();
  const next = safeRedirectPath(params.get("next"));
  const nextQuery = params.get("next") ? `?${new URLSearchParams({ next })}` : "";

  return (
    <AuthLayout
      title="Регистрация"
      description="Создайте аккаунт по почте или войдите через Яндекс ID и Google — аккаунт создастся сам."
      footer={
        <>
          Уже есть аккаунт?{" "}
          <Link to={`${routes.login}${nextQuery}`} className="font-medium text-foreground underline underline-offset-4">
            Войти
          </Link>
        </>
      }
    >
      <RegisterForm />
      <OAuthButtons next={next} />
    </AuthLayout>
  );
}
