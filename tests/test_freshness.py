import asyncio

import httpx
import pytest

from app import freshness


def test_sources_cover_resources_and_programs():
    srcs = freshness.sources()
    kinds = {s["kind"] for s in srcs}
    assert kinds == {"resource", "program"}
    assert all(s["url"].startswith("http") for s in srcs)
    assert len({(s["kind"], s["id"]) for s in srcs}) == len(srcs)


def test_page_text_strips_scripts_and_tags():
    html = "<html><script>alert('x')</script><style>p{}</style><h1>Free&nbsp;classes</h1><p>Evenings</p></html>"
    assert freshness.page_text(html) == "Free classes Evenings"


@pytest.mark.parametrize("status,ok,ex,expected", [
    (200, True, {"differs_from_listing": False, "still_offered": True}, ("ok", False)),
    (200, True, {"differs_from_listing": True, "still_offered": "unknown"}, ("flagged", True)),
    (200, True, {"differs_from_listing": False, "still_offered": False}, ("flagged", True)),
    (200, True, None, ("ok", False)),
    (404, False, None, ("broken", False)),
    (None, False, None, ("broken", False)),
    (403, False, None, ("unverified", False)),
])
def test_classify(status, ok, ex, expected):
    assert freshness.classify(status, ok, ex) == expected


def _transport(routes: dict[str, tuple[int, str]]):
    def handler(request: httpx.Request) -> httpx.Response:
        status, body = routes.get(str(request.url), (404, "missing"))
        if status == 0:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(status, text=body, headers={"content-type": "text/html"})
    return httpx.MockTransport(handler)


def test_check_one_records_results_without_raising(monkeypatch):
    page = "<p>" + "City College evening IT certificate, free tuition. " * 10 + "</p>"
    routes = {"https://ok.example/": (200, page), "https://blocked.example/": (403, "no"),
              "https://down.example/": (0, "")}
    monkeypatch.setattr(freshness, "extract", lambda src, text: {
        "still_offered": True, "next_date": "Jan 2027", "cost_note": None,
        "differs_from_listing": False, "note": "Matches listing."})
    srcs = [{"id": i, "kind": "resource", "name": i, "url": u, "listing": {}}
            for i, u in (("a", "https://ok.example/"), ("b", "https://blocked.example/"), ("c", "https://down.example/"))]

    async def go():
        async with httpx.AsyncClient(transport=_transport(routes)) as client:
            sem = asyncio.Semaphore(4)
            return await asyncio.gather(*(freshness.check_one(client, s, sem, deadline=1e12) for s in srcs))

    a, b, c = asyncio.run(go())
    assert (a["state"], a["http_status"], a["extraction"]["next_date"]) == ("ok", 200, "Jan 2027")
    assert (b["state"], b["http_status"]) == ("unverified", 403)
    assert c["state"] == "broken" and c["error"].startswith("ConnectError")


def test_extraction_failure_is_recorded(monkeypatch):
    def bad(src, text):
        raise RuntimeError("mistral down")
    monkeypatch.setattr(freshness, "extract", bad)
    page = "<p>" + "x " * 300 + "</p>"

    async def go():
        async with httpx.AsyncClient(transport=_transport({"https://ok.example/": (200, page)})) as client:
            return await freshness.check_one(client, {"id": "a", "kind": "program", "name": "a",
                                                      "url": "https://ok.example/", "listing": {}},
                                             asyncio.Semaphore(1), deadline=1e12)

    d = asyncio.run(go())
    assert d["state"] == "ok" and "mistral down" in d["error"]


def test_summarize_and_attach():
    docs = [{"kind": "resource", "id": "r1", "state": "ok", "ok": True, "checked_at": "2026-11-04T03:00:00+00:00"},
            {"kind": "program", "id": "p1", "state": "flagged", "ok": True, "flagged": True,
             "checked_at": "2026-11-04T03:01:00+00:00"},
            {"kind": "resource", "id": "r2", "state": "broken", "ok": False, "checked_at": None}]
    s = freshness.summarize(docs)
    assert (s["total"], s["ok"], s["flagged"], s["broken"]) == (3, 1, 1, 1)
    assert s["checked_at_latest"] == "2026-11-04T03:01:00+00:00"
    checks = {f"{d['kind']}:{d['id']}": freshness.live_check(d) for d in docs}
    items = [{"id": "r1", "kind": "resource"}, {"id": "p1", "provider": "X"}, {"id": "zz", "kind": "resource"}]
    freshness.attach(items, checks)
    assert items[0]["live_check"]["state"] == "ok"
    assert items[1]["live_check"]["flagged"] is True
    assert "live_check" not in items[2]


def test_attach_never_raises_when_es_fails(monkeypatch):
    monkeypatch.setattr(freshness, "_es", lambda: (_ for _ in ()).throw(RuntimeError("no es")))
    items = [{"id": "r1", "kind": "resource"}]
    assert freshness.attach(items) == items
    assert "live_check" not in items[0]


def test_start_background_refuses_second_run(monkeypatch):
    import threading
    gate = threading.Event()
    monkeypatch.setattr(freshness, "run", lambda use_ai=True: gate.wait(2))
    assert freshness.start_background() is True
    assert freshness.start_background() is False
    gate.set()


def _one_ok_page(monkeypatch, extract_fn, deadline=1e12):
    monkeypatch.setattr(freshness, "extract", extract_fn)
    page = "<p>" + "x " * 300 + "</p>"

    async def go():
        async with httpx.AsyncClient(transport=_transport({"https://ok.example/": (200, page)})) as client:
            return await freshness.check_one(client, {"id": "a", "kind": "resource", "name": "a",
                                                      "url": "https://ok.example/", "listing": {}},
                                             asyncio.Semaphore(1), deadline=deadline)
    return asyncio.run(go())


def test_rate_limit_is_skipped_not_retried(monkeypatch):
    calls = []

    def limited(src, text):
        calls.append(1)
        raise freshness.RateLimited("429")
    d = _one_ok_page(monkeypatch, limited)
    assert calls == [1]
    assert d["state"] == "ok" and d["error"].startswith("not extracted") and "429" in d["error"]
    assert "not compared" in d["note"]


def test_queued_comparison_past_deadline_is_skipped(monkeypatch):
    d = _one_ok_page(monkeypatch, lambda src, text: pytest.fail("should not call Mistral"), deadline=0)
    assert d["error"] == "not extracted: run time limit"


def test_check_model_is_separate_and_small_by_default():
    from app import config
    assert config.MISTRAL_CHECK_MODEL
    assert freshness.AI_CONCURRENCY == 1 and freshness.AI_MIN_SPACING_S >= 1.5
