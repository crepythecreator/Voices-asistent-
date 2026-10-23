export interface User {
  id: string;
  name: string;
  email?: string | null;
  avatarUrl?: string | null;
  /** Можно ли войти по паролю. Нет — входил только через Яндекс/Google. */
  hasPassword: boolean;
}
