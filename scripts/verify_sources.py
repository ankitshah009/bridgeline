"""Check every program and free-help source URL live, compare with Mistral, store in Elasticsearch.

    uv run python scripts/verify_sources.py          # fetch + Mistral comparison + store
    uv run python scripts/verify_sources.py --no-ai  # HTTP checks only
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import freshness  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-ai", action="store_true", help="HTTP checks only, skip the Mistral comparison")
    args = ap.parse_args()
    res = freshness.run(use_ai=not args.no_ai)
    print(f"checked {res['total']} sources in {res['seconds']} s: ok {res['ok']}, flagged {res['flagged']}, "
          f"broken {res['broken']}, unverified (site blocks bots) {res['unverified']}; stored {res['stored']}")
    for d in sorted(res["items"], key=lambda d: (d["state"] == "ok", d["kind"], d["id"])):
        if d["state"] != "ok":
            print(f"  [{d['state']:10}] {d['kind']:8} {d['name'][:44]:44} HTTP {d['http_status']}  {d.get('note') or ''}"[:220])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
