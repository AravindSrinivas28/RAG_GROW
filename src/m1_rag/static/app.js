/**
 * Phase 8 minimal UI — threads in localStorage, API same-origin.
 */
(function () {
  "use strict";

  const API = "";
  const LS_THREADS = "m1rag_thread_list_v1";
  const LS_ACTIVE = "m1rag_active_thread_v1";

  function msgKey(threadId) {
    return "m1rag_msgs_v1_" + threadId;
  }

  function loadThreads() {
    try {
      const raw = localStorage.getItem(LS_THREADS);
      if (!raw) return [];
      const data = JSON.parse(raw);
      return Array.isArray(data) ? data : [];
    } catch {
      return [];
    }
  }

  function saveThreads(list) {
    localStorage.setItem(LS_THREADS, JSON.stringify(list));
  }

  function loadMessages(threadId) {
    try {
      const raw = localStorage.getItem(msgKey(threadId));
      if (!raw) return [];
      const data = JSON.parse(raw);
      return Array.isArray(data) ? data : [];
    } catch {
      return [];
    }
  }

  function saveMessages(threadId, msgs) {
    localStorage.setItem(msgKey(threadId), JSON.stringify(msgs));
  }

  const el = {
    threadList: document.getElementById("thread-list"),
    messages: document.getElementById("messages"),
    welcome: document.getElementById("welcome"),
    composer: document.getElementById("composer"),
    input: document.getElementById("user-input"),
    btnSend: document.getElementById("btn-send"),
    btnNew: document.getElementById("btn-new-thread"),
    error: document.getElementById("error-line"),
  };

  let currentThreadId = null;

  function showError(msg) {
    if (!msg) {
      el.error.hidden = true;
      el.error.textContent = "";
      return;
    }
    el.error.hidden = false;
    el.error.textContent = msg;
  }

  async function apiCreateThread() {
    const r = await fetch(API + "/threads", { method: "POST" });
    if (!r.ok) throw new Error("Could not create conversation (" + r.status + ")");
    return r.json();
  }

  async function apiPostMessage(threadId, content) {
    const r = await fetch(API + "/threads/" + encodeURIComponent(threadId) + "/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    const text = await r.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error("Invalid response from server.");
    }
    if (!r.ok) {
      const detail = data.detail || data.message || text || "Request failed";
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }

  function renderThreadList() {
    const threads = loadThreads();
    el.threadList.innerHTML = "";
    threads.forEach(function (t, idx) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = t.label || "Chat " + (idx + 1);
      if (t.id === currentThreadId) btn.classList.add("is-active");
      btn.addEventListener("click", function () {
        switchThread(t.id);
      });
      li.appendChild(btn);
      el.threadList.appendChild(li);
    });
  }

  function renderMessages(msgs) {
    el.messages.innerHTML = "";
    if (!msgs.length) {
      el.messages.hidden = true;
      el.welcome.hidden = false;
      return;
    }
    el.welcome.hidden = true;
    el.messages.hidden = false;

    msgs.forEach(function (m) {
      const wrap = document.createElement("div");
      wrap.className = "bubble bubble--user";
      if (m.role === "assistant") {
        wrap.className = "bubble bubble--assistant";
        const p = document.createElement("p");
        p.textContent = m.answer_text || "";
        wrap.appendChild(p);
        const cite = (m.citation_url || "").trim();
        if (cite) {
          const meta = document.createElement("p");
          meta.className = "bubble__meta";
          meta.appendChild(document.createTextNode("Source: "));
          const a = document.createElement("a");
          a.href = cite;
          a.target = "_blank";
          a.rel = "noopener noreferrer";
          a.textContent = cite;
          meta.appendChild(a);
          wrap.appendChild(meta);
        }
        const foot = (m.footer_line || "").trim();
        if (foot) {
          const f = document.createElement("p");
          f.className = "bubble__footer";
          f.textContent = foot;
          wrap.appendChild(f);
        }
      } else {
        wrap.textContent = m.content || "";
      }
      el.messages.appendChild(wrap);
    });
    el.messages.scrollTop = el.messages.scrollHeight;
  }

  function switchThread(threadId) {
    currentThreadId = threadId;
    localStorage.setItem(LS_ACTIVE, threadId);
    renderThreadList();
    renderMessages(loadMessages(threadId));
  }

  async function ensureThread() {
    let threads = loadThreads();
    let active = localStorage.getItem(LS_ACTIVE);
    if (active && threads.some(function (t) { return t.id === active; })) {
      currentThreadId = active;
      renderThreadList();
      renderMessages(loadMessages(active));
      return;
    }
    const created = await apiCreateThread();
    const id = created.thread_id;
    const label = "Chat " + (threads.length + 1);
    threads.push({ id: id, label: label, createdAt: Date.now() });
    saveThreads(threads);
    switchThread(id);
  }

  async function onNewThread() {
    showError(null);
    const created = await apiCreateThread();
    const threads = loadThreads();
    const label = "Chat " + (threads.length + 1);
    threads.push({ id: created.thread_id, label: label, createdAt: Date.now() });
    saveThreads(threads);
    switchThread(created.thread_id);
  }

  async function onSubmit(ev) {
    ev.preventDefault();
    showError(null);
    const content = (el.input.value || "").trim();
    if (!content) return;

    el.btnSend.disabled = true;
    try {
      if (!currentThreadId) await ensureThread();

      const msgs = loadMessages(currentThreadId);
      msgs.push({ role: "user", content: content });
      saveMessages(currentThreadId, msgs);
      el.input.value = "";
      renderMessages(msgs);

      const data = await apiPostMessage(currentThreadId, content);
      const a = data.assistant || {};
      msgs.push({
        role: "assistant",
        answer_text: a.answer_text || "",
        citation_url: a.citation_url || "",
        last_updated: a.last_updated || "",
        footer_line: a.footer_line || "",
      });
      saveMessages(currentThreadId, msgs);
      renderMessages(msgs);
    } catch (e) {
      showError(e.message || String(e));
    } finally {
      el.btnSend.disabled = false;
    }
  }

  function onExampleClick(question) {
    el.input.value = question;
    el.input.focus();
    el.composer.requestSubmit();
  }

  document.querySelectorAll(".chip[data-question]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      onExampleClick(btn.getAttribute("data-question") || "");
    });
  });

  el.composer.addEventListener("submit", onSubmit);
  el.btnNew.addEventListener("click", function () {
    onNewThread().catch(function (e) {
      showError(e.message || String(e));
    });
  });

  ensureThread().catch(function (e) {
    showError(e.message || String(e));
  });
})();
