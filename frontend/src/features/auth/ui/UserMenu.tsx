import { LogOut } from "lucide-react";

import { UserAvatar } from "@/entities/user";
import { Button } from "@/shared/ui/button";
import { useAuth } from "../model/AuthProvider";

/** Аватар текущего пользователя и выход. Защищённые роуты сами уведут на /login. */
export function UserMenu() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <div className="flex items-center gap-2">
      <UserAvatar user={user} />
      <Button variant="ghost" size="icon" onClick={logout} aria-label="Выйти" title="Выйти">
        <LogOut />
      </Button>
    </div>
  );
}
