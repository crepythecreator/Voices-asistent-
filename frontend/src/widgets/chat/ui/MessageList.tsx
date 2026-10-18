import { useEffect, useRef } from "react";

import { ActionCard, type ProposedAction } from "@/entities/action";
import { MessageItem, type Message } from "@/entities/message";
import { ActionDecision } from "@/features/confirm-action";

interface Props {
  messages: Message[];
  onActionResolved: (action: ProposedAction) => void;
}

export function MessageList({ messages, onActionResolved }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-6">
      {messages.map((m) => (
        <div key={m.id} className="flex flex-col gap-2">
          <MessageItem message={m} />
          {m.actions && m.actions.length > 0 && (
            <div className="ml-11 flex max-w-[80%] flex-col gap-2">
              {m.actions.map((a) => (
                <ActionCard key={a.id} action={a} controls={<ActionDecision action={a} onResolved={onActionResolved} />} />
              ))}
            </div>
          )}
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}
