"""Phase 9: lightweight index stats for regression spot-checks (rag-architecture.md §10.2)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from m1_rag.settings import AppSettings
from m1_rag.vector_store import get_collection


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> None:
    app = AppSettings.load()
    persist = Path(app.yaml.vector_db.persist_directory)
    if not persist.is_absolute():
        persist = _project_root() / persist
    try:
        col = get_collection(persist, app.yaml.vector_db.collection_name)
        n = col.count()
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)
    out = {
        "ok": True,
        "collection": app.yaml.vector_db.collection_name,
        "persist_directory": str(persist.resolve()),
        "approx_row_count": n,
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
