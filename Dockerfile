# Optional Phase 0 parity image for ingest/API (extend in later phases).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY config ./config
COPY src ./src

RUN pip install --no-cache-dir .

# Default: show help until pipeline entrypoints exist
CMD ["python", "-c", "import m1_rag; print('m1_rag', m1_rag.__version__)"]
