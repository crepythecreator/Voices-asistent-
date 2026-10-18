import { useState } from "react";

import { cn } from "@/shared/lib/cn";
import { Button } from "@/shared/ui/button";
import { Spinner } from "@/shared/ui/spinner";
import { useAuth } from "../model/AuthProvider";

interface Props {
  /** Куда вернуть пользователя после входа. */
  next?: string;
  className?: string;
}

export function YandexLoginButton({ next, className }: Props) {
  const { login } = useAuth();
  const [redirecting, setRedirecting] = useState(false);

  return (
    <Button
      size="lg"
      className={cn("h-11 w-full bg-black text-white hover:bg-black/85 dark:bg-white dark:text-black dark:hover:bg-white/90", className)}
      disabled={redirecting}
      onClick={() => {
        setRedirecting(true);
        login(next);
      }}
    >
      {redirecting ? <Spinner className="text-current" /> : <YandexLogo />}
      Войти с Яндекс ID
    </Button>
  );
}

function YandexLogo() {
  return (
    <span className="flex size-5 items-center justify-center rounded-full bg-[#FC3F1D] text-xs font-bold text-white">Я</span>
  );
}
