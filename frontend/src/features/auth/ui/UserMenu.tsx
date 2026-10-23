import { LogOut, Settings } from "lucide-react";
import { Link } from "react-router";

import { UserAvatar } from "@/entities/user";
import { routes } from "@/shared/config";
import { Button } from "@/shared/ui/button";
import { useAuth } from "../model/AuthProvider";

/** Аватар со ссылкой на настройки и выход. Защищённые роуты сами уведут на /login. */
export function UserMenu() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <div className="flex items-center gap-1">
      <Button variant="ghost" size="icon" asChild aria-label="Настройки" title="Настройки">
        <Link to={routes.settings}>
          <Settings />
        </Link>
      </Button>
      <Link to={routes.settings} className="rounded-full outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50">
        <UserAvatar user={user} />
      </Link>
      <Button variant="ghost" size="icon" onClick={logout} aria-label="Выйти" title="Выйти">
        <LogOut />
      </Button>
    </div>
  );
}
