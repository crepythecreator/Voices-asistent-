import { useSyncExternalStore } from "react";

// Счётчик изменений календаря: кто меняет события — вызывает invalidateEvents(),
// кто показывает — подписывается через useEventsRevision() и перезагружает данные.

let revision = 0;
const listeners = new Set<() => void>();

export function invalidateEvents() {
  revision += 1;
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useEventsRevision(): number {
  return useSyncExternalStore(subscribe, () => revision);
}
