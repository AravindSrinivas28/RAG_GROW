/**
 * Single-flight "get or create" thread for boot and send — avoids duplicate
 * POST /threads when React Strict Mode runs effects twice in development.
 */

import { apiCreateThread } from "@/lib/api";
import {
  LS_ACTIVE,
  loadThreads,
  saveThreads,
  type ThreadEntry,
} from "@/lib/m1rag-storage";

let inflight: Promise<string> | null = null;

export async function ensureServerThread(
  switchThread: (id: string) => void,
): Promise<string> {
  const list = loadThreads();
  const active = localStorage.getItem(LS_ACTIVE);
  if (active && list.some((t) => t.id === active)) {
    switchThread(active);
    return active;
  }

  if (!inflight) {
    inflight = (async () => {
      const created = await apiCreateThread();
      const id = created.thread_id;
      const fresh = loadThreads();
      const label = `Chat ${fresh.length + 1}`;
      const next: ThreadEntry[] = [
        ...fresh,
        { id, label, createdAt: Date.now() },
      ];
      saveThreads(next);
      switchThread(id);
      return id;
    })().finally(() => {
      inflight = null;
    });
  }
  return inflight;
}
