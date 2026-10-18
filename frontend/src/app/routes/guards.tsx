import { Navigate, Outlet, useLocation, useSearchParams } from "react-router";

import { useAuth } from "@/features/auth";
import { routes, safeRedirectPath } from "@/shared/config";
import { FullscreenSpinner } from "@/shared/ui/spinner";

/** Пускает только вошедших; остальных — на /login с адресом возврата. */
export function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <FullscreenSpinner />;
  if (!user) {
    const next = location.pathname + location.search + location.hash;
    const search = next === routes.home ? "" : `?${new URLSearchParams({ next })}`;
    return <Navigate to={`${routes.login}${search}`} replace />;
  }
  return <Outlet />;
}

/** Страницы для гостей (вход): вошедшего сразу отправляем туда, куда он шёл. */
export function GuestRoute() {
  const { user, loading } = useAuth();
  const [params] = useSearchParams();

  if (loading) return <FullscreenSpinner />;
  if (user) return <Navigate to={safeRedirectPath(params.get("next"))} replace />;
  return <Outlet />;
}
