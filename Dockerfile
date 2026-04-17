# M1 RAG — FastAPI backend (e.g. Render, Fly, Cloud Run).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Some wheels (e.g. chroma) benefit from a compiler; HF/transformers stack is heavy but CPU-only.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY config ./config
COPY phases ./phases
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["python", "-m", "m1_rag.api"]
