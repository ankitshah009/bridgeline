"""Set up Elastic for Bridgeline: Mistral inference endpoint, indices, catalog and simulated pilot cohort.

Usage:
  uv run python scripts/setup_elastic.py           # idempotent: create what's missing, (re)index catalog + cohort
  uv run python scripts/setup_elastic.py --reset   # delete indices (and the Mistral endpoint) and rebuild
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from elasticsearch import ApiError, NotFoundError, helpers  # noqa: E402

from app import config  # noqa: E402
from app.catalog import load_pilot_cohort, load_programs, resident_cost, search_text  # noqa: E402
from app.search import _body, applications_mapping, current_inference_id, es_client, programs_mapping  # noqa: E402


def _exists(es, inference_id: str) -> bool:
    try:
        es.inference.get(inference_id=inference_id)
        return True
    except NotFoundError:
        return False


def ensure_inference(es) -> str:
    """Prefer a Mistral embeddings endpoint; fall back to Elastic's multilingual E5, then any embedding endpoint."""
    if _exists(es, config.INFERENCE_ID):
        print(f"inference: using existing endpoint {config.INFERENCE_ID}")
        return config.INFERENCE_ID
    if config.MISTRAL_API_KEY:
        try:
            es.options(request_timeout=120).inference.put(
                task_type="text_embedding",
                inference_id=config.INFERENCE_ID,
                inference_config={
                    "service": "mistral",
                    "service_settings": {"api_key": config.MISTRAL_API_KEY, "model": config.MISTRAL_EMBED_MODEL},
                },
            )
            print(f"inference: created {config.INFERENCE_ID} (service=mistral, model={config.MISTRAL_EMBED_MODEL})")
            return config.INFERENCE_ID
        except ApiError as exc:
            print(f"inference: Mistral endpoint failed ({exc.meta.status}: {str(exc)[:300]}); falling back")
    else:
        print("inference: MISTRAL_API_KEY not set; falling back")
    if _exists(es, config.FALLBACK_INFERENCE_ID):
        print(f"inference: using fallback {config.FALLBACK_INFERENCE_ID}")
        return config.FALLBACK_INFERENCE_ID
    endpoints = _body(es.inference.get()).get("endpoints", [])
    for task in ("text_embedding", "sparse_embedding"):
        for ep in endpoints:
            if ep.get("task_type") == task:
                print(f"inference: using available endpoint {ep['inference_id']}")
                return ep["inference_id"]
    raise SystemExit("inference: no embedding endpoint available on this cluster")


def reset(es) -> None:
    for index in (config.INDEX_PROGRAMS, config.INDEX_APPLICATIONS):
        if es.indices.exists(index=index):
            es.indices.delete(index=index)
            print(f"reset: deleted index {index}")
    if _exists(es, config.INFERENCE_ID):
        es.inference.delete(inference_id=config.INFERENCE_ID, force=True)
        print(f"reset: deleted inference endpoint {config.INFERENCE_ID}")


def ensure_indices(es, inference_id: str) -> None:
    if es.indices.exists(index=config.INDEX_PROGRAMS):
        existing = current_inference_id(es)
        if existing != inference_id:
            print(f"programs: index uses inference {existing!r}, wanted {inference_id!r}; run with --reset to switch")
    else:
        es.indices.create(index=config.INDEX_PROGRAMS, mappings=programs_mapping(inference_id))
        print(f"programs: created {config.INDEX_PROGRAMS} (description: semantic_text -> {inference_id})")
    if not es.indices.exists(index=config.INDEX_APPLICATIONS):
        es.indices.create(index=config.INDEX_APPLICATIONS, mappings=applications_mapping())
        print(f"applications: created {config.INDEX_APPLICATIONS}")


def program_docs() -> list[dict]:
    docs = []
    for p in load_programs():
        doc = dict(p)
        doc["resident_cost_usd"] = resident_cost(p)
        doc["search_text"] = search_text(p)
        docs.append(doc)
    return docs


def index_all(es) -> None:
    slow = es.options(request_timeout=300)
    programs = program_docs()
    started = time.perf_counter()
    ok, errors = helpers.bulk(slow, ({"_index": config.INDEX_PROGRAMS, "_id": d["id"], "_source": d} for d in programs),
                              raise_on_error=False, chunk_size=50)
    print(f"programs: indexed {ok}/{len(programs)} with embeddings in {time.perf_counter() - started:.1f}s")
    for err in errors[:3]:
        print("  error:", str(err)[:300])
    cohort = load_pilot_cohort()
    ok, errors = helpers.bulk(slow, ({"_index": config.INDEX_APPLICATIONS, "_id": d["id"], "_source": d} for d in cohort),
                              raise_on_error=False)
    print(f"applications: indexed {ok}/{len(cohort)} simulated pilot cohort docs")
    for err in errors[:3]:
        print("  error:", str(err)[:300])
    es.indices.refresh(index=[config.INDEX_PROGRAMS, config.INDEX_APPLICATIONS])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="delete indices and the Mistral endpoint, then rebuild")
    args = parser.parse_args()
    es = es_client()
    if es is None:
        raise SystemExit("Set ES_URL and ES_API_KEY in .env first")
    info = _body(es.info())
    print(f"connected: {info.get('cluster_name') or info.get('name')} (version {info.get('version', {}).get('number', '?')})")
    if args.reset:
        reset(es)
    inference_id = ensure_inference(es)
    ensure_indices(es, inference_id)
    index_all(es)
    for index in (config.INDEX_PROGRAMS, config.INDEX_APPLICATIONS):
        print(f"count {index}: {_body(es.count(index=index))['count']}")


if __name__ == "__main__":
    main()
