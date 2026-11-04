import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from elastic_transport import ApiResponseMeta, HttpHeaders, NodeConfig
from elasticsearch import BadRequestError, NotFoundError

from app import catalog, config, search


def _meta(status: int) -> ApiResponseMeta:
    return ApiResponseMeta(status=status, http_version="1.1", headers=HttpHeaders(), duration=0.0,
                           node=NodeConfig("https", "localhost", 443))


def _hit(pid: str, score: float, highlight: str | None = None) -> dict:
    doc = catalog.get_program(pid)
    doc["search_text"] = "x"
    hit = {"_id": pid, "_score": score, "_source": doc}
    if highlight:
        hit["highlight"] = {"description": [highlight]}
    return hit


@pytest.fixture
def es(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(search, "es_client", lambda: client)
    return client


EVENING_PARENT = {
    "language": "es", "availability": "evenings", "hours_per_week_available": 10,
    "career_tracks": ["IT support"], "needs_childcare": True,
    "search_query": "part-time evening IT support training for beginners",
}


def test_search_ranks_free_evening_program_first(es):
    es.search.return_value = {"hits": {"hits": [
        _hit("per-scholas-it-support", 0.92),
        _hit("illustrative-evening-it-cloud-bootcamp", 0.90),
        _hit("ccsf-it-support-certificate", 0.88, "evening sections that fit around a daytime job"),
        _hit("jvs-techsf-it", 0.85),
    ]}}
    results = search.search_programs("", EVENING_PARENT, k=3)
    assert [r["id"] for r in results][0] == "ccsf-it-support-certificate"
    top = results[0]
    assert "Evening classes: fits your schedule" in top["_why"] and "Free tuition" in top["_why"]
    assert top["_highlight"].startswith("evening sections")
    assert len(results) == 3
    # full-time daytime program ranks below the evening options for an evening-only resident
    assert results.index(next(r for r in results if r["id"] == "ccsf-it-support-certificate")) == 0
    body = es.search.call_args.kwargs["body"]
    assert body["query"]["bool"]["should"][0]["semantic"]["query"] == EVENING_PARENT["search_query"]
    assert body["query"]["bool"]["must_not"] == [{"term": {"isa_or_required_loan": True}}]
    assert es.search.call_args.kwargs["index"] == config.INDEX_PROGRAMS


def test_search_retries_without_highlight_on_bad_request(es):
    ok = {"hits": {"hits": [_hit("sfpl-tech-help", 1.0)]}}
    es.search.side_effect = [BadRequestError("no semantic highlighter", _meta(400), {}), ok]
    results = search.search_programs("computer basics", {"availability": "daytime"})
    assert results[0]["id"] == "sfpl-tech-help" and results[0]["_highlight"] is None
    assert "highlight" not in es.search.call_args_list[1].kwargs["body"]


def test_search_raises_when_not_configured(monkeypatch):
    monkeypatch.setattr(search, "es_client", lambda: None)
    with pytest.raises(RuntimeError, match="ES_URL"):
        search.search_programs("it", {})


def test_search_empty(es):
    es.search.return_value = {"hits": {"hits": []}}
    assert search.search_programs("it", {}) == []


def test_stipend_flagged(es):
    es.search.return_value = {"hits": {"hits": [_hit("year-up-bay-area", 1.0)]}}
    assert "benefits check" in search.search_programs("it", {"availability": "full-time"})[0]["_why"]


def test_impact_stats_parses_aggregations(es):
    es.search.return_value = {
        "took": 7,
        "hits": {"total": {"value": 50, "relation": "eq"}},
        "aggregations": {
            "by_status": {"buckets": [{"key": "placed", "doc_count": 9}, {"key": "completed", "doc_count": 6},
                                      {"key": "enrolled", "doc_count": 12}, {"key": "approved", "doc_count": 6},
                                      {"key": "declined", "doc_count": 3}, {"key": "submitted", "doc_count": 14}]},
            "by_tier": {"buckets": [{"key": "stay_in_training", "doc_count": 27}]},
            "by_language": {"buckets": [{"key": "es", "doc_count": 13}]},
            "by_property": {"buckets": [{"key": "Mission Commons (demo)", "doc_count": 11, "approved": {"doc_count": 8}}]},
            "awarded": {"doc_count": 33, "free_program_value": {"value": 90000.0},
                        "public_aid": {"value": 11000.0}, "grant": {"value": 52190.5}},
            "completed": {"doc_count": 15},
            "placed_or_raise": {"doc_count": 9},
            "decision_days": {"values": {"50.0": 5.96}},
            "simulated": {"doc_count": 48},
        },
    }
    stats = search.impact_stats()
    assert stats["total"] == 50 and stats["live_count"] == 2 and stats["simulated_count"] == 48
    assert stats["dollars"] == {"free_program_value": 90000.0, "public_aid": 11000.0, "grant": 52190.5}
    assert stats["outcomes"] == {"completed": 15, "placed_or_raise": 9}
    assert stats["median_decision_days"] == 6.0
    assert stats["by_property"] == [{"property": "Mission Commons (demo)", "residents": 11, "approved": 8}]
    funnel = {f["stage"]: f["count"] for f in stats["funnel"]}
    assert funnel["Grant approved"] == 33 and funnel["Enrolled"] == 27 and funnel["Job or raise"] == 9
    assert stats["query"]["aggs"]["awarded"]["filter"]["terms"]["status"] == search.AWARDED_STATUSES
    assert stats["took_ms"] == 7


def test_application_crud(es):
    doc = {"id": "HB-2026-0001", "status": "submitted"}
    saved = search.save_application(doc)
    assert es.index.call_args.kwargs["id"] == "HB-2026-0001" and "created_at" in saved
    es.get.return_value = {"_source": {**saved, "status": "approved"}}
    updated = search.update_application("HB-2026-0001", {"status": "approved"})
    assert updated["status"] == "approved"
    assert es.update.call_args.kwargs["doc"]["status"] == "approved"
    es.get.side_effect = NotFoundError("missing", _meta(404), {})
    assert search.get_application("nope") is None


def test_list_applications_excludes_simulated(es):
    es.search.return_value = {"hits": {"hits": [{"_source": {"id": "HB-1"}}]}}
    assert search.list_applications(include_simulated=False) == [{"id": "HB-1"}]
    body = es.search.call_args.kwargs["body"]
    assert body["query"] == {"bool": {"must_not": [{"term": {"simulated": True}}]}}
    assert body["sort"] == [{"created_at": {"order": "desc"}}]


def test_es_status(es, monkeypatch):
    es.info.return_value = {"cluster_name": "homebase", "version": {"number": "9.5.0"}}
    es.indices.get_mapping.return_value = {config.INDEX_PROGRAMS: {"mappings": {"properties": {
        "description": {"type": "semantic_text", "inference_id": config.INFERENCE_ID}}}}}
    es.count.side_effect = [{"count": 16}, {"count": 49}]
    status = search.es_status()
    assert status == {"connected": True, "cluster": "homebase", "inference_id": config.INFERENCE_ID,
                      "programs": 16, "applications": 49, "error": None}


def test_es_status_unconfigured(monkeypatch):
    monkeypatch.setattr(search, "es_client", lambda: None)
    status = search.es_status()
    assert status["connected"] is False and "ES_URL" in status["error"]


def test_mappings():
    m = search.programs_mapping("my-endpoint")
    assert m["properties"]["description"] == {"type": "semantic_text", "inference_id": "my-endpoint"}
    assert m["properties"]["location"]["type"] == "geo_point"
    a = search.applications_mapping()
    assert a["dynamic"] is False and a["properties"]["grant_amount"]["type"] == "float"


def _setup_module():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "scripts"))
    return importlib.import_module("setup_elastic")


def test_setup_prefers_mistral_then_falls_back(monkeypatch):
    setup = _setup_module()
    es = MagicMock()
    es.inference.get.side_effect = NotFoundError("missing", _meta(404), {})
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "k")
    assert setup.ensure_inference(es) == config.INFERENCE_ID
    put = es.options.return_value.inference.put.call_args.kwargs
    assert put["inference_config"]["service"] == "mistral" and put["task_type"] == "text_embedding"

    from elasticsearch import ApiError
    es2 = MagicMock()
    es2.inference.get.side_effect = [NotFoundError("missing", _meta(404), {}), {"endpoints": []}]
    es2.options.return_value.inference.put.side_effect = ApiError("bad key", _meta(400), {})
    assert setup.ensure_inference(es2) == config.FALLBACK_INFERENCE_ID


def test_setup_program_docs_have_search_fields():
    setup = _setup_module()
    docs = setup.program_docs()
    assert all("resident_cost_usd" in d and d["search_text"] for d in docs)
