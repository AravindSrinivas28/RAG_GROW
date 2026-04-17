# M1 RAG — High-level architecture (diagrams)

Pictorial view of the **facts-only mutual fund FAQ assistant**. For narrative detail, see [rag-architecture.md](./rag-architecture.md) and [chunking-embedding-architecture.md](./chunking-embedding-architecture.md).

---

## 1. System context (who talks to what)

Boxes show major deployable pieces and external systems.

```mermaid
flowchart TB
    subgraph users["Users"]
        U[Browser / API client]
    end

    subgraph app["M1 RAG application"]
        UI[Static UI<br/>GET /]
        API[FastAPI<br/>threads + messages]
        RAG[Assistant pipeline<br/>router → retrieve → generate]
        TS[(SQLite<br/>thread store)]
        OBS[Structured logs<br/>m1_rag.chat]
    end

    subgraph data["Local / disk"]
        CH[(Chroma<br/>vector index)]
        STATE[ingest_state.json]
    end

    subgraph external["External services"]
        WEB[Allowlisted web<br/>Groww / AMFI / SEBI]
        HF[Hugging Face Hub<br/>BGE embeddings model]
        LLM[OpenRouter or<br/>OpenAI-compatible API]
    end

    subgraph automation["Automation"]
        GHA[GitHub Actions<br/>scheduled ingest]
    end

    U --> UI
    U --> API
    UI --> API
    API --> RAG
    API --> TS
    API --> OBS
    RAG --> CH
    RAG --> LLM
    GHA --> WEB
    GHA --> HF
    GHA --> CH
    GHA -.->|ephemeral runner| STATE
```

---

## 2. Ingestion pipeline (offline / batch)

Flow from manifest URLs to searchable vectors.

```mermaid
flowchart LR
    subgraph inputs["Inputs"]
        M[corpus_manifest.yaml]
        CFG[config/default.yaml]
    end

    subgraph phase2["Fetch & normalize"]
        SC[scrape_corpus]
        ND[NormalizedDocument<br/>text + metadata + content_hash]
    end

    subgraph phase3["Chunk & embed"]
        CHK[HF tokenizer<br/>sliding windows]
        EMB[sentence-transformers<br/>BAAI/bge-small-en-v1.5]
        VEC[vectors 384-d]
    end

    subgraph store["Index"]
        CHR[Chroma PersistentClient<br/>cosine + metadata]
    end

    M --> SC
    CFG --> SC
    SC --> ND
    ND --> CHK
    CHK --> EMB
    EMB --> VEC
    VEC --> CHR
    ND -.->|skip if hash unchanged| STATE[(ingest state)]
```

**CLI:** `m1-rag-ingest` · **Scheduler:** GitHub Actions cron (same command on a runner; index on runner is usually not persisted unless you add artifacts/deploy).

---

## 3. Query path (online / one user turn)

From HTTP message to answer JSON (and UI).

```mermaid
flowchart TD
    A[POST /threads/id/messages<br/>user text] --> R{Router<br/>rules}
    R -->|advisory / PII| REF[Refusal template<br/>+ educational URL]
    R -->|factual| Q[preprocess_query]
    Q --> E[Embed query<br/>same BGE model]
    E --> CH[(Chroma ANN<br/>top-k + optional filters)]
    CH -->|empty / low confidence| ABS[Abstention message<br/>+ link]
    CH -->|chunks OK| G[Grounded LLM<br/>JSON: answer + citation + date]
    G --> P[Post-checks<br/>≤3 sentences, URL allow-list]
    P --> OUT[Assistant payload +<br/>footer line]
    REF --> OUT
    ABS --> OUT
    OUT --> L[JSON log line<br/>latency, flags, query_hash]
    OUT --> RESP[HTTP response]
```

**Secrets:** LLM key via `.env` (`M1_RAG_OPENROUTER_API_KEY` or `M1_RAG_LLM_API_KEY`). Embeddings run **locally** by default (no embedding API key).

---

## 4. Layered view (logical architecture)

Stacked responsibilities—useful for slides.

```mermaid
flowchart TB
    subgraph presentation["Presentation"]
        WEBUI[Browser UI<br/>disclaimer + chat + threads]
    end

    subgraph api_layer["API"]
        HTTP[FastAPI<br/>/threads, /messages, /health, /static]
    end

    subgraph orchestration["Orchestration"]
        ASST[assistant.run_assistant_turn]
        ROUT[router.classify_route]
    end

    subgraph retrieval["Retrieval"]
        RET[retrieve → RetrievedChunk]
    end

    subgraph generation["Generation"]
        GEN[generation.generate_grounded_answer]
    end

    subgraph data_layer["Data"]
        VDB[(Chroma)]
        SQL[(SQLite threads)]
    end

    subgraph models["Models"]
        BGE[BGE-small embeddings]
        CHAT[Chat LLM via OpenRouter/OpenAI API]
    end

    WEBUI --> HTTP
    HTTP --> ASST
    ASST --> ROUT
    ROUT --> RET
    ROUT --> GEN
    RET --> VDB
    RET --> BGE
    GEN --> CHAT
    HTTP --> SQL
```

---

## 5. Automation vs local dev (two ways to run ingest)

```mermaid
flowchart LR
    subgraph local["Developer machine"]
        L1[git clone]
        L2[m1-rag-ingest]
        L3[data/vector_store persists]
        L1 --> L2 --> L3
    end

    subgraph ci["GitHub Actions"]
        C1[cron / workflow_dispatch]
        C2[m1_rag.ingest]
        C3[runner disk discarded]
        C1 --> C2 --> C3
    end
```

---

## 6. ASCII overview (quick sketch)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           BROWSER (Phase 8 UI)                            │
│                 disclaimer · examples · chat · threads                  │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │ HTTP
┌─────────────────────────────────▼────────────────────────────────────────┐
│                         FastAPI (Phase 7)                                 │
│   GET /  GET /health  POST /threads  POST /threads/{id}/messages         │
│   logs: JSON lines (Phase 9) · thread rows in SQLite                      │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
 ┌─────────────┐           ┌─────────────┐           ┌─────────────┐
 │   Router    │           │  Retrieval  │           │  Refusal    │
 │  (Phase 6)  │           │  (Phase 5)  │           │  templates  │
 └──────┬──────┘           └──────┬──────┘           └─────────────┘
        │                         │
        │                    ┌──────▼──────┐
        │                    │  Chroma    │
        │                    │  + BGE     │
        │                    │  embed q   │
        │                    └──────┬──────┘
        │                           │
        └───────────────────────────┼──────────────────────┐
                                    ▼                      │
                             ┌─────────────┐               │
                             │ Chat LLM    │◄── OpenRouter │
                             │ JSON answer │    / OpenAI   │
                             └─────────────┘               │
                                                           │
┌──────────────────────────────────────────────────────────┴───────────────┐
│ INGEST (manual CLI or GitHub Actions cron)                               │
│  manifest → scrape → normalize → chunk → embed (BGE) → upsert → Chroma  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Rendering these diagrams

- **GitHub:** This file renders Mermaid in the web UI when viewed in the repo.
- **VS Code / Cursor:** Use a Mermaid preview extension, or paste into [mermaid.live](https://mermaid.live).
- **Export PNG/SVG:** Use Mermaid CLI or mermaid.live **Actions → PNG/SVG**.
- **Pre-rendered PNG (all sections):** [docs/diagrams/m1-rag-hld-full.png](./diagrams/m1-rag-hld-full.png) — vertical stack of figures 1–5; individual exports live beside it as `01-system-context.png` … `05-automation-local.png` (sources under [docs/diagrams/sources](./diagrams/sources/)).

---

## Document history

| Version | Description |
|---------|-------------|
| 1.0 | High-level box/flow diagrams for M1 RAG |
