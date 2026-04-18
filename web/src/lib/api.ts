/** Calls the FastAPI M1 RAG backend (Phase 7). */

/** Long enough for Render cold start + embedding + LLM (ms). */
const DEFAULT_FETCH_TIMEOUT_MS = 180_000;

export function getApiBase(): string {
  const raw = process.env.NEXT_PUBLIC_M1_RAG_API_URL ?? "http://127.0.0.1:8000";
  return raw.replace(/\/+$/, "");
}

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit = {},
  timeoutMs: number = DEFAULT_FETCH_TIMEOUT_MS,
): Promise<Response> {
  const ctrl = new AbortController();
  const id = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: ctrl.signal });
  } finally {
    clearTimeout(id);
  }
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
  let r: Response;
  try {
    r = await fetchWithTimeout(`${getApiBase()}/threads`, { method: "POST" });
  } catch (e: unknown) {
    if (e instanceof Error && e.name === "AbortError") {
      throw new Error(
        `Request timed out after ${DEFAULT_FETCH_TIMEOUT_MS / 1000}s (is the API waking up on Render?)`,
      );
    }
    throw e;
  }
  if (!r.ok) throw new Error(`Could not create conversation (${r.status})`);
  return r.json() as Promise<CreateThreadResponse>;
}

export async function apiPostMessage(
  threadId: string,
  content: string,
): Promise<PostMessageResponse> {
  let r: Response;
  try {
    r = await fetchWithTimeout(
      `${getApiBase()}/threads/${encodeURIComponent(threadId)}/messages`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      },
    );
  } catch (e: unknown) {
    if (e instanceof Error && e.name === "AbortError") {
      throw new Error(
        `Request timed out after ${DEFAULT_FETCH_TIMEOUT_MS / 1000}s (is the API waking up on Render?)`,
      );
    }
    throw e;
  }
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
