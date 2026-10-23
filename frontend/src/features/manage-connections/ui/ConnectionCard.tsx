import { useState } from "react";
import { AlertCircle, CalendarCheck, Link2, Unlink } from "lucide-react";

import type { Connection } from "@/entities/connection";
import { invalidateEvents } from "@/entities/event";
import { errorMessage } from "@/shared/lib/errorMessage";
import { Button } from "@/shared/ui/button";
import { ProviderIcon } from "@/shared/ui/provider-icon";
import { Spinner } from "@/shared/ui/spinner";
import { Switch } from "@/shared/ui/switch";
import { connectUrl, disconnect, setSync } from "../api/connectionsApi";

interface Props {
  connection: Connection;
  onChange: (connection: Connection) => void;
}

export function ConnectionCard({ connection: c, onChange }: Props) {
  const [busy, setBusy] = useState<"sync" | "disconnect" | "connect" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (kind: "sync" | "disconnect", fn: () => Promise<void>) => {
    setBusy(kind);
    setError(null);
    try {
      await fn();
      invalidateEvents(); // занятость и статусы выгрузки в календаре поменялись
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };

  const connect = () => {
    setBusy("connect");
    window.location.href = connectUrl(c.provider);
  };

  const toggleSync = (enabled: boolean) => run("sync", async () => onChange(await setSync(c, enabled)));

  const remove = () => {
    if (!window.confirm(`Отключить ${c.title}? События, уже выгруженные в его календарь, там останутся.`)) return;
    void run("disconnect", async () => {
      await disconnect(c.provider);
      onChange({ ...c, connected: false, email: null, calendarAccess: false, syncEnabled: false, calendarStatus: null });
    });
  };

  return (
    <div className="flex flex-col gap-3 rounded-xl border p-4">
      <div className="flex items-center gap-3">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg border bg-background">
          <ProviderIcon provider={c.provider} className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="font-medium">{c.title}</div>
          <div className="truncate text-sm text-muted-foreground">{c.connected ? (c.email ?? "Подключён") : "Не подключён"}</div>
        </div>
        {c.connected ? (
          <Button variant="ghost" size="sm" onClick={remove} disabled={busy !== null}>
            {busy === "disconnect" ? <Spinner className="size-4" /> : <Unlink />}
            Отключить
          </Button>
        ) : (
          <Button variant="outline" size="sm" onClick={connect} disabled={busy !== null}>
            {busy === "connect" ? <Spinner className="size-4" /> : <Link2 />}
            Подключить
          </Button>
        )}
      </div>

      {c.connected && c.calendarAccess && (
        <div className="flex flex-col gap-2 rounded-lg bg-muted/50 p-3">
          <label className="flex items-center justify-between gap-3 text-sm">
            <span>
              <span className="font-medium">Синхронизировать календарь</span>
              <span className="block text-xs text-muted-foreground">
                События ассистента появятся в отдельном календаре, занятость — учитывается
              </span>
            </span>
            <Switch checked={c.syncEnabled} onCheckedChange={toggleSync} disabled={busy !== null} aria-label="Синхронизировать календарь" />
          </label>
          {c.syncEnabled && c.calendarStatus === "ok" && (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <CalendarCheck className="size-3.5" /> Календарь подключён
            </span>
          )}
          {c.syncEnabled && c.calendarStatus === "pending" && (
            <span className="text-xs text-muted-foreground">Календарь настраивается…</span>
          )}
          {c.calendarStatus === "error" && c.calendarError && (
            <span className="flex items-start gap-1.5 text-xs text-destructive">
              <AlertCircle className="mt-px size-3.5 shrink-0" /> {c.calendarError}
            </span>
          )}
        </div>
      )}

      {c.connected && !c.calendarAccess && (
        <div className="flex items-center justify-between gap-3 rounded-lg bg-muted/50 p-3 text-sm">
          <span className="text-muted-foreground">Доступ к календарю не выдан</span>
          <Button size="sm" variant="outline" onClick={connect} disabled={busy !== null}>
            {busy === "connect" && <Spinner className="size-4" />}
            Выдать доступ к календарю
          </Button>
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
