import { useState, type FormEvent } from "react";

import { errorMessage } from "@/shared/lib/errorMessage";
import { Button } from "@/shared/ui/button";
import { FormError } from "@/shared/ui/form-error";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Spinner } from "@/shared/ui/spinner";
import { useAuth } from "../model/AuthProvider";

/** Вход по почте и паролю. После успеха гостевой роут сам уведёт на `next`. */
export function LoginForm() {
  const { loginWithPassword } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await loginWithPassword(email, password);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="grid gap-4">
      <FormError message={error} />
      <div className="grid gap-2">
        <Label htmlFor="email">Почта</Label>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="password">Пароль</Label>
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      <Button type="submit" className="h-10 w-full" disabled={busy}>
        {busy && <Spinner className="size-4 text-current" />}
        Войти
      </Button>
    </form>
  );
}
