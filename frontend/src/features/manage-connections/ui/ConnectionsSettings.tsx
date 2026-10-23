import { useEffect, useState } from "react";

import { getConnections, type Connection } from "@/entities/connection";
import { Spinner } from "@/shared/ui/spinner";
import { ConnectionCard } from "./ConnectionCard";

/** Список Яндекс/Google: подключение, доступ к календарю, синхронизация, отключение. */
export function ConnectionsSettings() {
  const [connections, setConnections] = useState<Connection[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getConnections()
      .then(setConnections)
      .catch(() => setFailed(true));
  }, []);

  if (failed) return <p className="text-sm text-destructive">Не удалось загрузить подключения</p>;
  if (!connections) return <Spinner />;
  if (!connections.length) {
    return <p className="text-sm text-muted-foreground">Вход через Яндекс и Google не настроен на сервере.</p>;
  }

  const update = (next: Connection) => setConnections((prev) => prev!.map((c) => (c.provider === next.provider ? next : c)));

  return (
    <div className="flex flex-col gap-3">
      {connections.map((c) => (
        <ConnectionCard key={c.provider} connection={c} onChange={update} />
      ))}
    </div>
  );
}
