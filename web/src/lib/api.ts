/** Calls the FastAPI M1 RAG backend (Phase 7). */

export function getApiBase(): string {
  const raw = process.env.NEXT_PUBLIC_M1_RAG_API_URL ?? "http://127.0.0.1:8000";
  return raw.replace(/\/+$/, "");
}

export type CreateThreadResponse = { thread_id: string };

export type AssistantPayload = {
  answer_text: string;
  citation_url?: string;
  last_updated?: string;
  footer_line?: string;
  refusal?: boolean;
  abstain?: boolean;
  abstain_reason?: string | null;
  route?: string;
  model_id?: string | null;
};

export type PostMessageResponse = {
  thread_id: string;
  assistant: AssistantPayload;
};

export async function apiCreateThread(): Promise<CreateThreadResponse> {
  const r = await fetch(`${getApiBase()}/threads`, { method: "POST" });
  if (!r.ok) throw new Error(`Could not create conversation (${r.status})`);
  return r.json() as Promise<CreateThreadResponse>;
}

export async function apiPostMessage(
  threadId: string,
  content: string,
): Promise<PostMessageResponse> {
  const r = await fetch(
    `${getApiBase()}/threads/${encodeURIComponent(threadId)}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    },
  );
  const text = await r.text();
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error("Invalid response from server.");
  }
  if (!r.ok) {
    const d = data as { detail?: unknown; message?: unknown };
    const detail = (d.detail ?? d.message ?? text) || "Request failed";
    throw new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail),
    );
  }
  return data as PostMessageResponse;
}
