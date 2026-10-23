import { useEffect, useState } from "react";

import { USE_MOCKS } from "@/shared/config";
import { authApi, type OAuthProviderInfo } from "../api/authApi";

const MOCK_PROVIDERS: OAuthProviderInfo[] = [
  { id: "yandex", title: "Яндекс ID", configured: true },
  { id: "google", title: "Google", configured: true },
];

// Если сервер не ответил, кнопки всё равно показываем — иначе непонятно, почему их нет
const FALLBACK_PROVIDERS: OAuthProviderInfo[] = MOCK_PROVIDERS.map((p) => ({ ...p, configured: false }));

/** Провайдеры входа и признак, что список не удалось получить с сервера. */
export function useOAuthProviders() {
  const [providers, setProviders] = useState<OAuthProviderInfo[]>(USE_MOCKS ? MOCK_PROVIDERS : FALLBACK_PROVIDERS);
  const [loading, setLoading] = useState(!USE_MOCKS);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (USE_MOCKS) return;
    let cancelled = false;
    authApi
      .providers()
      .then((list) => !cancelled && setProviders(list))
      .catch(() => !cancelled && setFailed(true))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  return { providers, loading, failed };
}
