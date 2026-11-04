"""Load the SF grants / free-programs list into Elasticsearch (index homebase-resources).

    uv run python scripts/load_resources.py           # idempotent: create if missing, upsert all rows
    uv run python scripts/load_resources.py --reset   # drop and recreate the index
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from elasticsearch import helpers  # noqa: E402

from app import resources  # noqa: E402
from app.search import es_client  # noqa: E402
from scripts.setup_elastic import ensure_inference  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="delete and recreate the index")
    args = ap.parse_args()

    es = es_client()
    if es is None:
        print("ES_URL / ES_API_KEY missing in .env", file=sys.stderr)
        return 1

    idx = resources.INDEX_RESOURCES
    if args.reset and es.indices.exists(index=idx):
        es.indices.delete(index=idx)
        print(f"reset: deleted {idx}")
    if not es.indices.exists(index=idx):
        inference_id = ensure_inference(es)
        es.indices.create(index=idx, mappings=resources.mapping(inference_id))
        print(f"created {idx} (text: semantic_text -> {inference_id})")

    rows = resources.load_resources()
    t0 = time.perf_counter()
    ok, errors = helpers.bulk(
        es.options(request_timeout=120),
        ({"_index": idx, "_id": r["id"], "_source": r | {"text": resources.search_text(r)}} for r in rows),
        raise_on_error=False,
    )
    es.indices.refresh(index=idx)
    print(f"indexed {ok}/{len(rows)} resources in {time.perf_counter() - t0:.1f}s; errors: {len(errors)}")
    if errors:
        print(str(errors[:2])[:1200])
    print("count", es.count(index=idx)["count"])
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
