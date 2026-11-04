"""Load San Francisco open data (MOHCD affordable housing portfolio) into Elasticsearch.

    uv run python scripts/load_opendata.py            # live from DataSF, snapshot fallback
    uv run python scripts/load_opendata.py --snapshot # use app/data/sf_mohcd_portfolio.json
    uv run python scripts/load_opendata.py --reset    # drop and recreate the index
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from elasticsearch import helpers  # noqa: E402

from app import opendata  # noqa: E402
from app.search import es_client  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true", help="skip the live DataSF fetch")
    ap.add_argument("--reset", action="store_true", help="delete and recreate the index")
    args = ap.parse_args()

    es = es_client()
    if es is None:
        print("ES_URL / ES_API_KEY missing in .env", file=sys.stderr)
        return 1

    rows: list[dict]
    if args.snapshot:
        rows = opendata.load_snapshot()
        print(f"snapshot: {len(rows)} rows")
    else:
        try:
            rows = opendata.fetch_portfolio()
            opendata.SNAPSHOT.write_text(json.dumps(rows))
            print(f"DataSF live: {len(rows)} rows (snapshot refreshed)")
        except Exception as e:  # network trouble at the venue
            rows = opendata.load_snapshot()
            print(f"DataSF fetch failed ({e}); using snapshot: {len(rows)} rows")

    idx = opendata.INDEX_HOUSING
    if args.reset and es.indices.exists(index=idx):
        es.indices.delete(index=idx)
    if not es.indices.exists(index=idx):
        es.indices.create(index=idx, mappings=opendata.MAPPING)

    docs = [d for d in (opendata.normalize(r) for r in rows) if d]
    ok, errors = helpers.bulk(
        es,
        ({"_index": idx, "_id": d["id"], "_source": d} for d in docs),
        raise_on_error=False,
    )
    es.indices.refresh(index=idx)
    print(f"indexed {ok} docs into {idx}; errors: {len(errors)}")
    if errors:
        print(json.dumps(errors[:3], indent=1)[:1500])

    s = opendata.housing_stats()
    print(f"rental buildings {s['buildings']}, affordable units {s['affordable_units']}, "
          f"neighborhoods {s['neighborhoods']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
