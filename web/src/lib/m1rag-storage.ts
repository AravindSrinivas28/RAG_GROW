/**
 * Thread list and message cache — same keys as Phase 8 static UI (`static/app.js`)
 * so switching between FastAPI-served HTML and Next.js keeps separate browser profiles only.
 */

export const LS_THREADS = "m1rag_thread_list_v1";
export const LS_ACTIVE = "m1rag_active_thread_v1";

export function msgKey(threadId: string): string {
  return `m1rag_msgs_v1_${threadId}`;
}

export type ThreadEntry = {
  id: string;
  label: string;
  createdAt: number;
};

export type ChatMessage =
  | { role: "user"; content: string }
  | {
      role: "assistant";
      answer_text: string;
      citation_url?: string;
      last_updated?: string;
      footer_line?: string;
      refusal?: boolean;
      abstain?: boolean;
    };

export function loadThreads(): ThreadEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(LS_THREADS);
    if (!raw) return [];
    const data = JSON.parse(raw) as unknown;
    return Array.isArray(data) ? (data as ThreadEntry[]) : [];
  } catch {
    return [];
  }
}

export function saveThreads(list: ThreadEntry[]): void {
  localStorage.setItem(LS_THREADS, JSON.stringify(list));
}

export function loadMessages(threadId: string): ChatMessage[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(msgKey(threadId));
    if (!raw) return [];
    const data = JSON.parse(raw) as unknown;
    return Array.isArray(data) ? (data as ChatMessage[]) : [];
  } catch {
    return [];
  }
}

export function saveMessages(threadId: string, msgs: ChatMessage[]): void {
  localStorage.setItem(msgKey(threadId), JSON.stringify(msgs));
}
