/** Calls the FastAPI M1 RAG backend (Phase 7). */

/** Long enough for Render cold start + embedding + LLM (ms). */
const DEFAULT_FETCH_TIMEOUT_MS = 180_000;

function useVercelSameOriginProxy(): boolean {
  return process.env.NEXT_PUBLIC_API_VIA_VERCEL_PROXY === "1";
}

/**
 * Base URL for FastAPI calls.
 * - Default local: http://127.0.0.1:8000
 * - Production: NEXT_PUBLIC_M1_RAG_API_URL (direct to Render, cross-origin)
 * - If NEXT_PUBLIC_API_VIA_VERCEL_PROXY=1: same-origin `/api/m1` (rewritten by Next.js to Render — avoids Safari “Load failed” on some cross-origin requests)
 */
/** Always the configured backend (`NEXT_PUBLIC_M1_RAG_API_URL`), never the `/api/m1` proxy. */
function getDirectApiBase(): string {
  const fromEnv = process.env.NEXT_PUBLIC_M1_RAG_API_URL;
  const raw =
    fromEnv !== undefined && String(fromEnv).trim() !== ""
      ? String(fromEnv).trim()
      : "http://127.0.0.1:8000";
  return raw.replace(/\/+$/, "");
}

export function getApiBase(): string {
  if (typeof window !== "undefined" && useVercelSameOriginProxy()) {
    return `${window.location.origin}/api/m1`;
  }

  return getDirectApiBase();
}

/**
 * Base URL for `POST .../messages` (RAG + LLM — can take minutes).
 * When same-origin proxy is enabled, we still call Render **directly** here so
 * Vercel’s serverless function is not in the middle (Hobby ~10s limit → 502).
 * `POST /threads` stays on the fast proxy path for Safari-friendly same-origin.
 */
export function getMessagesApiBase(): string {
  if (typeof window !== "undefined" && useVercelSameOriginProxy()) {
    return getDirectApiBase();
  }
  return getApiBase();
}

/**
 * HTTPS pages (Vercel) cannot call http://127.0.0.1 — the browser blocks it and
 * Safari reports "Load failed". Fail fast with a clear message.
 */
export function validateApiUrlForBrowser(base: string): void {
  if (typeof window === "undefined") return;

  let url: URL;
  try {
    url = new URL(base);
  } catch {
    throw new Error(
      `Invalid API URL: "${base}". Use https://your-service.onrender.com`,
    );
  }

  if (window.location.protocol !== "https:") return;

  if (url.hostname === "localhost" || url.hostname === "127.0.0.1") {
    throw new Error(
      "API URL still points to localhost. In Vercel → Settings → Environment Variables, set NEXT_PUBLIC_M1_RAG_API_URL=https://YOUR-SERVICE.onrender.com (no trailing slash), save, then Redeploy (Production).",
    );
  }
  if (url.protocol === "http:") {
    throw new Error(
      "API URL must use https:// when the site is served over HTTPS. Set NEXT_PUBLIC_M1_RAG_API_URL to your Render https URL and redeploy.",
    );
  }
}

export function validateApiBaseForBrowser(): void {
  validateApiUrlForBrowser(getApiBase());
}

function wrapNetworkError(
  e: unknown,
  kind: "threads" | "messages",
): Error {
  if (e instanceof Error && e.name === "AbortError") return e;

  const msg = e instanceof Error ? e.message : String(e);
  const lower = msg.toLowerCase();
  if (
    lower.includes("load failed") ||
    lower.includes("failed to fetch") ||
    lower.includes("networkerror") ||
    lower === "network request failed"
  ) {
    const base =
      kind === "messages" ? getMessagesApiBase() : getApiBase();
    if (useVercelSameOriginProxy() && kind === "threads") {
      return new Error(
        `Cannot reach API via Vercel proxy (${base}). Ensure NEXT_PUBLIC_M1_RAG_API_URL is set, redeploy, and that Render is running. (${msg})`,
      );
    }
    return new Error(
      `Cannot reach ${base}. Set NEXT_PUBLIC_M1_RAG_API_URL in Vercel to your Render https URL, redeploy, and ensure the Render service is running. (${msg})`,
    );
  }
  return e instanceof Error ? e : new Error(msg);
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

/** Server no longer has this thread_id (e.g. Render restarted; SQLite was ephemeral). */
export class ThreadGoneError extends Error {
  constructor() {
    super("thread not found");
    this.name = "ThreadGoneError";
  }
}

export async function apiCreateThread(): Promise<CreateThreadResponse> {
  validateApiUrlForBrowser(getApiBase());

  let r: Response;
  try {
    r = await fetchWithTimeout(`${getApiBase()}/threads`, { method: "POST" });
  } catch (e: unknown) {
    if (e instanceof Error && e.name === "AbortError") {
      throw new Error(
        `Request timed out after ${DEFAULT_FETCH_TIMEOUT_MS / 1000}s (is the API waking up on Render?)`,
      );
    }
    throw wrapNetworkError(e, "threads");
  }
  if (!r.ok) throw new Error(`Could not create conversation (${r.status})`);
  return r.json() as Promise<CreateThreadResponse>;
}

export async function apiPostMessage(
  threadId: string,
  content: string,
): Promise<PostMessageResponse> {
  validateApiUrlForBrowser(getMessagesApiBase());

  let r: Response;
  try {
    r = await fetchWithTimeout(
      `${getMessagesApiBase()}/threads/${encodeURIComponent(threadId)}/messages`,
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
    throw wrapNetworkError(e, "messages");
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
    const msg = typeof detail === "string" ? detail : JSON.stringify(detail);
    if (
      r.status === 404 &&
      typeof detail === "string" &&
      detail.toLowerCase().includes("thread not found")
    ) {
      throw new ThreadGoneError();
    }
    throw new Error(msg);
  }
  return data as PostMessageResponse;
}
