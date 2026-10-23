import { useState, type FormEvent } from "react";

import { MIN_PASSWORD_LENGTH } from "@/shared/config";
import { errorMessage } from "@/shared/lib/errorMessage";
import { Button } from "@/shared/ui/button";
import { FormError } from "@/shared/ui/form-error";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Spinner } from "@/shared/ui/spinner";
import { useAuth } from "../model/AuthProvider";

/** Регистрация по почте и паролю. После успеха гостевой роут сам уведёт на `next`. */
export function RegisterForm() {
  const { register } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Пароль должен быть не короче ${MIN_PASSWORD_LENGTH} символов`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await register(email, password, name.trim());
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="grid gap-4">
      <FormError message={error} />
      <div className="grid gap-2">
        <Label htmlFor="name">Имя</Label>
        <Input
          id="name"
          autoComplete="name"
          placeholder="Как к вам обращаться"
          required
          maxLength={100}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>
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
          autoComplete="new-password"
          required
          minLength={MIN_PASSWORD_LENGTH}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <p className="text-xs text-muted-foreground">Не короче {MIN_PASSWORD_LENGTH} символов</p>
      </div>
      <Button type="submit" className="h-10 w-full" disabled={busy}>
        {busy && <Spinner className="size-4 text-current" />}
        Зарегистрироваться
      </Button>
    </form>
  );
}
