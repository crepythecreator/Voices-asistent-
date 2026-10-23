import { useState, type FormEvent } from "react";
import { Check } from "lucide-react";

import { api, delay } from "@/shared/api";
import { MIN_PASSWORD_LENGTH, USE_MOCKS } from "@/shared/config";
import { errorMessage } from "@/shared/lib/errorMessage";
import { Button } from "@/shared/ui/button";
import { FormError } from "@/shared/ui/form-error";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Spinner } from "@/shared/ui/spinner";

interface Props {
  /** Пароль уже есть — нужен текущий. Нет — пользователь входил только через Яндекс/Google. */
  hasPassword: boolean;
  /** Почта аккаунта; без неё вход по паролю невозможен. */
  email?: string | null;
  onSuccess?: () => void;
}

export function PasswordForm({ hasPassword, email, onSuccess }: Props) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  if (!email) {
    return <p className="text-sm text-muted-foreground">У аккаунта нет почты — вход по паролю недоступен.</p>;
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setDone(false);
    if (next.length < MIN_PASSWORD_LENGTH) return setError(`Пароль должен быть не короче ${MIN_PASSWORD_LENGTH} символов`);
    if (next !== repeat) return setError("Пароли не совпадают");
    setBusy(true);
    setError(null);
    try {
      if (USE_MOCKS) await delay(300);
      else
        await api<void>("/account/password", {
          method: "POST",
          body: JSON.stringify({ currentPassword: hasPassword ? current : null, newPassword: next }),
        });
      setCurrent("");
      setNext("");
      setRepeat("");
      setDone(true);
      onSuccess?.();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="grid max-w-sm gap-4">
      {!hasPassword && (
        <p className="text-sm text-muted-foreground">
          Задайте пароль, чтобы входить по почте <span className="font-medium text-foreground">{email}</span> без Яндекса и
          Google.
        </p>
      )}
      <FormError message={error} />
      {hasPassword && (
        <div className="grid gap-2">
          <Label htmlFor="current-password">Текущий пароль</Label>
          <Input
            id="current-password"
            type="password"
            autoComplete="current-password"
            required
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
          />
        </div>
      )}
      <div className="grid gap-2">
        <Label htmlFor="new-password">Новый пароль</Label>
        <Input
          id="new-password"
          type="password"
          autoComplete="new-password"
          required
          minLength={MIN_PASSWORD_LENGTH}
          value={next}
          onChange={(e) => setNext(e.target.value)}
        />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="repeat-password">Повторите пароль</Label>
        <Input
          id="repeat-password"
          type="password"
          autoComplete="new-password"
          required
          value={repeat}
          onChange={(e) => setRepeat(e.target.value)}
        />
      </div>
      <div className="flex items-center gap-3">
        <Button type="submit" disabled={busy}>
          {busy && <Spinner className="size-4 text-current" />}
          {hasPassword ? "Сменить пароль" : "Задать пароль"}
        </Button>
        {done && (
          <span className="flex items-center gap-1 text-sm text-muted-foreground">
            <Check className="size-4" /> Сохранено. Другие устройства вышли из аккаунта.
          </span>
        )}
      </div>
    </form>
  );
}
