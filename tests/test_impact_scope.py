"""scope=all|live on the impact aggregations and the /api/impact route."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import main, search

EMPTY_AGGS = {"took": 3, "hits": {"total": {"value": 0, "relation": "eq"}}, "aggregations": {}}


@pytest.fixture
def es(monkeypatch):
    client = MagicMock()
    client.search.return_value = EMPTY_AGGS
    monkeypatch.setattr(search, "es_client", lambda: client)
    return client


def test_default_scope_is_unchanged():
    body = search.impact_query()
    assert "query" not in body
    assert body == search.impact_query("all")


def test_live_scope_excludes_simulated():
    body = search.impact_query("live")
    assert body["query"] == {"bool": {"must_not": [{"term": {"simulated": True}}]}}
    assert body["aggs"] == search.impact_query()["aggs"]


def test_impact_stats_live_sends_filter_and_reports_scope(es):
    stats = search.impact_stats(scope="live")
    sent = es.search.call_args.kwargs["body"]
    assert sent["query"]["bool"]["must_not"] == [{"term": {"simulated": True}}]
    assert stats["scope"] == "live" and stats["total"] == 0 and stats["live_count"] == 0


def test_impact_stats_rejects_unknown_scope(es):
    with pytest.raises(ValueError):
        search.impact_stats(scope="everything")


def test_api_impact_scope_param(monkeypatch):
    calls = []

    def fake_stats(scope="all"):
        calls.append(scope)
        return {"total": 0 if scope == "live" else 48, "query": {}}

    monkeypatch.setattr(main, "_search", lambda: type("S", (), {"impact_stats": staticmethod(fake_stats)}))
    client = TestClient(main.app)
    live = client.get("/api/impact?scope=live").json()
    default = client.get("/api/impact").json()
    assert live["scope"] == "live" and live["total"] == 0
    assert default["scope"] == "all" and default["total"] == 48
    assert calls == ["live", "all"]
    assert client.get("/api/impact?scope=bogus").status_code == 400
