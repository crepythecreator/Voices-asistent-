export interface User {
  id: string;
  name: string;
  email?: string | null;
  avatarUrl?: string | null;
  /** Можно ли войти по паролю. Нет — входил только через Яндекс/Google. */
  hasPassword: boolean;
  /** confirm — изменения от ИИ подтверждает пользователь; auto — создание и изменение сразу (удаление — с подтверждением). */
  confirmMode: ConfirmMode;
}

export type ConfirmMode = "confirm" | "auto";
