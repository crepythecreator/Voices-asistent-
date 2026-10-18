import { Moon, Sun } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { useTheme } from "../model/useTheme";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <Button variant="ghost" size="icon" onClick={toggle} aria-label="Сменить тему">
      {theme === "dark" ? <Sun /> : <Moon />}
    </Button>
  );
}
