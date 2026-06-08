"use client";

import { useState, type FormEvent } from "react";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type ChatSidebarProps = {
  messages: ChatMessage[];
  onSend: (message: string) => Promise<void>;
  isLoading: boolean;
  error: string | null;
};

export const ChatSidebar = ({ messages, onSend, isLoading, error }: ChatSidebarProps) => {
  const [text, setText] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) {
      return;
    }

    await onSend(trimmed);
    setText("");
  };

  return (
    <aside className="flex min-h-[720px] w-full max-w-[420px] flex-col gap-4 rounded-3xl border border-[var(--stroke)] bg-[var(--surface-strong)] p-5 shadow-[var(--shadow)]">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">AI Assistant</p>
        <h2 className="mt-3 text-xl font-semibold text-[var(--navy-dark)]">Ask about your board</h2>
        <p className="mt-2 text-sm leading-6 text-[var(--gray-text)]">
          Ask for card details, column status, or board summaries.
        </p>
      </div>

      <div className="flex-1 overflow-hidden rounded-3xl bg-white p-4 shadow-[inset_0_1px_0_rgba(0,0,0,0.04)]">
        <div className="flex h-full flex-col gap-3 overflow-y-auto pr-1">
          {messages.length === 0 ? (
            <div className="mt-10 text-sm leading-6 text-[var(--gray-text)]">
              Start by asking something like "What is in Review?" or "Tell me more about the Done cards."
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`rounded-2xl p-3 text-sm shadow-[var(--shadow)] ${
                  message.role === "user"
                    ? "bg-[var(--surface)] text-[var(--navy-dark)] self-end"
                    : "bg-[var(--primary-blue)] text-white self-start"
                }`}
              >
                <p>{message.content}</p>
              </div>
            ))
          )}
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
      ) : null}

      <form onSubmit={handleSubmit} className="grid gap-3">
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Ask about a card or the board..."
          className="min-h-[96px] w-full resize-none rounded-2xl border border-[var(--stroke)] bg-white px-3 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
        />
        <button
          type="submit"
          disabled={isLoading}
          className="rounded-full bg-[var(--secondary-purple)] px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading ? "Thinking…" : "Send question"}
        </button>
      </form>
    </aside>
  );
};
