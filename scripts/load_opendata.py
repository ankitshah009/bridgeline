"""Load San Francisco open data (MOHCD affordable housing portfolio) into Elasticsearch.

    uv run python scripts/load_opendata.py            # live from DataSF, snapshot fallback
    uv run python scripts/load_opendata.py --snapshot # use app/data/sf_mohcd_portfolio.json
    uv run python scripts/load_opendata.py --reset    # drop and recreate the index

Every run also records DataSF's own "rows updated" time and our sync time in the
`homebase-sync` index, which the impact page shows as data freshness.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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

    res = opendata.load_portfolio(es, use_snapshot=args.snapshot, reset=args.reset)
    print(f"{res['origin']}: {res['rows']} rows; indexed {res['indexed']} into "
          f"{opendata.INDEX_HOUSING}; errors: {len(res['errors'])}")
    if res["errors"]:
        print(json.dumps(res["errors"][:3], indent=1)[:1500])
    sync = res["sync"]
    print(f"sync: DataSF rows updated {sync['source_updated_at']}, synced {sync['synced_at']}")

    s = opendata.housing_stats()
    print(f"rental buildings {s['buildings']}, affordable units {s['affordable_units']}, "
          f"neighborhoods {s['neighborhoods']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
