"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiCreateThread, apiPostMessage, getApiBase } from "@/lib/api";
import { ensureServerThread } from "@/lib/ensure-thread";
import type { ChatMessage, ThreadEntry } from "@/lib/m1rag-storage";
import {
  LS_ACTIVE,
  loadMessages,
  loadThreads,
  saveMessages,
  saveThreads,
} from "@/lib/m1rag-storage";

const EXAMPLES: { label: string; question: string }[] = [
  { label: "Minimum SIP", question: "What is the minimum SIP amount for this scheme?" },
  { label: "Expense ratio", question: "What is the expense ratio?" },
  { label: "Exit load", question: "What is the exit load?" },
];

export function ChatApp() {
  const [threads, setThreads] = useState<ThreadEntry[]>([]);
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [bootError, setBootError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const switchThread = useCallback((threadId: string) => {
    setCurrentThreadId(threadId);
    localStorage.setItem(LS_ACTIVE, threadId);
    setThreads(loadThreads());
    setMessages(loadMessages(threadId));
  }, []);

  const ensureThreadId = useCallback(async (): Promise<string> => {
    return ensureServerThread(switchThread);
  }, [switchThread]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        await ensureThreadId();
      } catch (e) {
        if (!cancelled) {
          setBootError(
            e instanceof Error ? e.message : "Could not reach the API.",
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ensureThreadId]);

  const sendMessage = useCallback(
    async (content: string) => {
      const trimmed = content.trim();
      if (!trimmed) return;

      setError(null);
      setSending(true);
      try {
        const tid = await ensureThreadId();
        const msgs: ChatMessage[] = [
          ...loadMessages(tid),
          { role: "user", content: trimmed },
        ];
        saveMessages(tid, msgs);
        setInput("");
        setMessages(msgs);

        const data = await apiPostMessage(tid, trimmed);
        const a = data.assistant;
        const assistantMsg: ChatMessage = {
          role: "assistant",
          answer_text: a.answer_text ?? "",
          citation_url: a.citation_url,
          last_updated: a.last_updated,
          footer_line: a.footer_line,
          refusal: a.refusal,
          abstain: a.abstain,
        };
        const withAssistant = [...msgs, assistantMsg];
        saveMessages(tid, withAssistant);
        setMessages(withAssistant);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setSending(false);
      }
    },
    [ensureThreadId],
  );

  async function onNewThread() {
    setError(null);
    const created = await apiCreateThread();
    const list = loadThreads();
    const label = `Chat ${list.length + 1}`;
    const next = [
      ...list,
      { id: created.thread_id, label, createdAt: Date.now() },
    ];
    saveThreads(next);
    switchThread(created.thread_id);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    await sendMessage(input);
  }

  const showWelcome = messages.length === 0;

  return (
    <>
      <header className="top-bar" role="banner">
        <div className="top-bar__inner">
          <h1 className="brand">M1 RAG</h1>
          <p className="disclaimer" id="disclaimer">
            Facts-only. No investment advice.
          </p>
        </div>
      </header>

      <div className="layout">
        <aside className="sidebar" aria-label="Conversations">
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => {
              void onNewThread().catch((err: unknown) =>
                setError(err instanceof Error ? err.message : String(err)),
              );
            }}
          >
            New conversation
          </button>
          <ul className="thread-list">
            {threads.map((t, idx) => (
              <li key={t.id}>
                <button
                  type="button"
                  className={t.id === currentThreadId ? "is-active" : undefined}
                  onClick={() => switchThread(t.id)}
                >
                  {t.label || `Chat ${idx + 1}`}
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <main className="chat" aria-live="polite">
          {bootError ? (
            <section className="welcome">
              <h2>API unavailable</h2>
              <p className="api-hint">
                Start the backend (e.g. <code>m1-rag-api</code> on{" "}
                <code>{getApiBase()}</code>
                ) or set{" "}
                <code>NEXT_PUBLIC_M1_RAG_API_URL</code> in{" "}
                <code>.env.local</code>.
              </p>
              <p className="error" role="alert">
                {bootError}
              </p>
            </section>
          ) : (
            <>
              <section className="welcome" hidden={!showWelcome}>
                <h2>Welcome</h2>
                <p>
                  Ask factual questions about mutual fund schemes using
                  information from our indexed official sources. Answers include
                  one source link and a last-updated line when available.
                </p>
                <p className="welcome__examples-label">Try an example:</p>
                <div className="examples">
                  {EXAMPLES.map(({ label, question }) => (
                    <button
                      key={question}
                      type="button"
                      className="chip"
                      disabled={sending}
                      onClick={() => void sendMessage(question)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </section>

              <div className="messages" hidden={showWelcome}>
                {messages.map((m, i) => (
                  <MessageBubble key={i} message={m} />
                ))}
                <div ref={messagesEndRef} />
              </div>

              <form
                id="composer"
                className="composer"
                autoComplete="off"
                onSubmit={(e) => void onSubmit(e)}
              >
                <label className="sr-only" htmlFor="user-input">
                  Your question
                </label>
                <textarea
                  id="user-input"
                  name="content"
                  rows={2}
                  maxLength={4000}
                  placeholder="Ask a factual question (no PAN, Aadhaar, or account numbers)…"
                  required
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={!!bootError}
                />
                <button
                  type="submit"
                  className="btn btn--send"
                  disabled={sending || !!bootError}
                  aria-busy={sending}
                >
                  {sending ? "Sending…" : "Send"}
                </button>
              </form>
              {error ? (
                <p className="error" role="alert">
                  {error}
                </p>
              ) : null}
            </>
          )}
        </main>
      </div>
    </>
  );
}

function MessageBubble({ message: m }: { message: ChatMessage }) {
  if (m.role === "user") {
    return <div className="bubble bubble--user">{m.content}</div>;
  }

  const cite = (m.citation_url ?? "").trim();
  const foot = (m.footer_line ?? "").trim();
  const flags: string[] = [];
  if (m.refusal) flags.push("Refusal");
  if (m.abstain) flags.push("Abstain");

  return (
    <div className="bubble bubble--assistant">
      {flags.length > 0 ? (
        <p className="bubble__flags">{flags.join(" · ")}</p>
      ) : null}
      <p>{m.answer_text}</p>
      {cite ? (
        <p className="bubble__meta">
          Source:{" "}
          <a href={cite} target="_blank" rel="noopener noreferrer">
            {cite}
          </a>
        </p>
      ) : null}
      {foot ? <p className="bubble__footer">{foot}</p> : null}
    </div>
  );
}
