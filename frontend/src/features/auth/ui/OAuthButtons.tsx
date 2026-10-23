import { useState } from "react";

import { Button } from "@/shared/ui/button";
import { ProviderIcon } from "@/shared/ui/provider-icon";
import { Spinner } from "@/shared/ui/spinner";
import { useAuth } from "../model/AuthProvider";
import { useOAuthProviders } from "../model/useOAuthProviders";

const LABELS: Record<string, string> = {
  yandex: "Войти с Яндекс ID",
  google: "Войти через Google",
};

/** Кнопки входа и регистрации через Яндекс/Google. Ненастроенный на сервере провайдер — неактивная кнопка. */
export function OAuthButtons({ next }: { next?: string }) {
  const { loginWithProvider } = useAuth();
  const { providers, loading, failed } = useOAuthProviders();
  const [redirecting, setRedirecting] = useState<string | null>(null);

  return (
    <div className="flex flex-col gap-4">
      <div className="relative text-center text-xs text-muted-foreground after:absolute after:inset-x-0 after:top-1/2 after:z-0 after:border-t">
        <span className="relative z-10 bg-background px-2">или</span>
      </div>
      <div className="grid gap-2">
        {providers.map((p) => {
          const unavailable = !loading && !p.configured;
          return (
            <Button
              key={p.id}
              type="button"
              variant="outline"
              className="h-10 w-full"
              disabled={loading || unavailable || redirecting !== null}
              title={unavailable ? "Вход через этот сервис не настроен на сервере" : undefined}
              onClick={() => {
                setRedirecting(p.id);
                loginWithProvider(p.id, next);
              }}
            >
              {redirecting === p.id ? <Spinner className="size-4" /> : <ProviderIcon provider={p.id} />}
              {LABELS[p.id] ?? `Войти через ${p.title}`}
            </Button>
          );
        })}
      </div>
      {failed && <p className="text-center text-xs text-destructive">Сервер недоступен — вход через Яндекс и Google пока невозможен.</p>}
      {!failed && !loading && providers.some((p) => !p.configured) && (
        <p className="text-center text-xs text-muted-foreground">
          Неактивные кнопки не настроены: добавьте ключи в <span className="font-mono">.env</span> и перезапустите бэкенд.
        </p>
      )}
    </div>
  );
}
