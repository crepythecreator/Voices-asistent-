export const routes = {
  home: "/",
  login: "/login",
  register: "/register",
  settings: "/settings",
} as const;

/** Пускаем только относительные пути внутри приложения — защита от open redirect. */
export function safeRedirectPath(path: string | null | undefined, fallback: string = routes.home): string {
  if (!path || !path.startsWith("/") || path.startsWith("//") || path.startsWith("/\\")) return fallback;
  return path;
}
