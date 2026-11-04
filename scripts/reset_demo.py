"""Reset the live demo: delete every non-simulated application in Elasticsearch.

The simulated pilot cohort (simulated: true) is kept, so the impact page still shows the
illustrative pilot. Run right before going on stage, then open http://localhost:3000/?new=1.

    uv run python scripts/reset_demo.py          # dry run: list what would be deleted
    uv run python scripts/reset_demo.py --yes    # delete
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.search import es_client  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="actually delete")
    args = ap.parse_args()

    es = es_client()
    if es is None:
        print("ES_URL / ES_API_KEY missing", file=sys.stderr)
        return 1
    live = {"bool": {"must_not": [{"term": {"simulated": True}}]}}
    hits = es.search(index=config.INDEX_APPLICATIONS, query=live, size=200,
                     source=["id", "status", "program_name", "created_at"])["hits"]["hits"]
    for h in hits:
        s = h["_source"]
        print(f"  {s.get('id')}  {s.get('status'):10}  {s.get('program_name', '')[:50]}  {s.get('created_at', '')[:19]}")
    if not args.yes:
        print(f"{len(hits)} live application(s); re-run with --yes to delete")
        return 0
    r = es.delete_by_query(index=config.INDEX_APPLICATIONS, query=live, refresh=True)
    total = es.count(index=config.INDEX_APPLICATIONS)["count"]
    print(f"deleted {r['deleted']} live application(s); {total} simulated remain")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
