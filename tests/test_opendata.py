from app import opendata

ROW = {
    "mohcd_development_id": "2019-001",
    "development_name": "Example Apartments",
    "marketing_address": "100 Example St",
    "marketing_zip_code": "94110",
    "city_analysis_marketing": "Mission",
    "tenure": "Rental",
    "project_status": "Construction Complete",
    "housing_program_program_name": "Rental Assistance Demonstration Program",
    "total_project_units": "120",
    "income_restricted_resid_units": "118",
    "_2_bedroom_units_rollup": "30",
    "_3_bedroom_units_rollup": "10.0",
    "estimated_actual_construction": "2018-06-01T00:00:00.000",
    "latitude": "37.76",
    "longitude": "-122.41",
}


def test_normalize_maps_fields_and_housing_type():
    d = opendata.normalize(ROW)
    assert d["id"] == "2019-001"
    assert d["housing_type"] == "project_based"
    assert d["affordable_units"] == 118
    assert d["family_size_units"] == 40
    assert d["location"] == {"lat": 37.76, "lon": -122.41}
    assert d["completed"] == "2018-06-01"


def test_normalize_handles_missing_and_bad_values():
    assert opendata.normalize({}) is None
    d = opendata.normalize({"mohcd_development_id": "x", "total_project_units": "n/a",
                            "latitude": "bad", "longitude": "-122"})
    assert d["total_units"] == 0
    assert "location" not in d
    assert d["housing_type"] == "other"


def test_distance_km():
    a = {"lat": 37.7749, "lon": -122.4194}
    b = {"lat": 37.7849, "lon": -122.4094}
    assert 1.3 < opendata.distance_km(a, b) < 1.5
    assert opendata.distance_km(a, None) is None


class FakeES:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def search(self, **kw):
        self.calls.append(kw)
        return self.response


def test_housing_stats_reads_aggregations(monkeypatch):
    fake = FakeES({
        "hits": {"total": {"value": 570}},
        "aggregations": {
            "units": {"value": 32360.0},
            "affordable_units": {"value": 31981.0},
            "family_size_units": {"value": 9000.0},
            "neighborhoods": {"value": 38},
            "by_neighborhood": {"buckets": [
                {"key": "Tenderloin", "doc_count": 80, "units": {"value": 6000.0}}]},
            "by_program": {"buckets": [
                {"key": "Multifamily Rental Program", "doc_count": 200, "units": {"value": 15000.0}}]},
        },
    })
    monkeypatch.setattr(opendata, "_es", lambda: fake)
    s = opendata.housing_stats()
    assert s["buildings"] == 570
    assert s["affordable_units"] == 31981
    assert s["by_neighborhood"][0] == {"neighborhood": "Tenderloin", "buildings": 80, "units": 6000}
    assert s["query"]["query"]["bool"]["filter"] == [{"term": {"tenure": "Rental"}}]
    assert fake.calls[0]["index"] == opendata.INDEX_HOUSING


def test_snapshot_is_present_and_parseable():
    rows = opendata.load_snapshot()
    docs = [d for d in (opendata.normalize(r) for r in rows) if d]
    assert len(docs) > 500
    assert sum(1 for d in docs if d["tenure"] == "Rental") > 400


# ---------- freshness: DataSF metadata, sync record, auto-refresh ----------

from datetime import datetime, timedelta, timezone  # noqa: E402


class FakeIndices:
    def __init__(self, existing=()):
        self.existing = set(existing)
        self.created = []

    def exists(self, index):
        return index in self.existing

    def create(self, index, **kw):
        self.existing.add(index)
        self.created.append(index)

    def delete(self, index):
        self.existing.discard(index)

    def refresh(self, index):
        pass


class SyncES:
    """Fake client covering what the freshness code touches."""

    def __init__(self, sync_doc=None):
        self.indices = FakeIndices({opendata.INDEX_SYNC} if sync_doc else ())
        self.docs = {opendata.SYNC_ID: sync_doc} if sync_doc else {}

    def index(self, index, id, document, refresh=None):
        self.indices.existing.add(index)
        self.docs[id] = document

    def get(self, index, id):
        if id not in self.docs:
            raise KeyError(id)
        return {"_source": self.docs[id]}

    def search(self, **kw):
        return {
            "hits": {"total": {"value": 1}},
            "aggregations": {
                "units": {"value": 10.0}, "affordable_units": {"value": 9.0},
                "family_size_units": {"value": 1.0}, "neighborhoods": {"value": 1},
                "by_neighborhood": {"buckets": []}, "by_program": {"buckets": []},
            },
        }


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_fetch_metadata_converts_rows_updated_epoch(monkeypatch):
    monkeypatch.setattr(opendata.httpx, "get", lambda url, timeout: FakeResponse(
        {"name": "MOHCD portfolio", "rowsUpdatedAt": 1779396593}))
    meta = opendata.fetch_metadata()
    assert meta["source_updated_at"] == "2026-05-21T20:49:53Z"


def test_write_and_read_sync_roundtrip():
    es = SyncES()
    doc = opendata.write_sync(es, rows=850, source_updated_at="2026-05-21T20:49:53Z", origin="datasf-live")
    assert opendata.INDEX_SYNC in es.indices.created
    back = opendata.read_sync(es)
    assert back == doc and back["rows"] == 850 and back["synced_at"].endswith("Z")


def test_read_sync_is_none_safe():
    assert opendata.read_sync(SyncES()) is None          # no index yet
    assert opendata.read_sync(object()) is None          # broken client never raises


def test_needs_refresh_rules():
    now = datetime(2026, 11, 4, 3, 0, tzinfo=timezone.utc)
    fresh = {"synced_at": "2026-11-04T02:00:00Z"}
    assert opendata.needs_refresh(None, "2026-05-21T20:49:53Z", now) is True
    assert opendata.needs_refresh(fresh, "2026-05-21T20:49:53Z", now) is False
    assert opendata.needs_refresh(fresh, "2026-11-04T02:30:00Z", now) is True   # DataSF changed after sync
    stale = {"synced_at": (now - timedelta(hours=25)).isoformat()}
    assert opendata.needs_refresh(stale, None, now) is True                      # older than 24 h


def test_housing_stats_includes_freshness(monkeypatch):
    es = SyncES({"source_updated_at": "2026-05-21T20:49:53Z", "synced_at": "2026-11-04T02:54:53Z",
                 "origin": "datasf-live", "rows": 850})
    monkeypatch.setattr(opendata, "_es", lambda: es)
    s = opendata.housing_stats()
    assert s["source_updated_at"] == "2026-05-21T20:49:53Z"
    assert s["synced_at"] == "2026-11-04T02:54:53Z"
    assert s["sync_origin"] == "datasf-live"


def test_auto_refresh_never_raises(monkeypatch):
    import app.search as search

    def boom():
        raise RuntimeError("cluster down")

    monkeypatch.setattr(search, "es_client", boom)
    msg = opendata.auto_refresh()
    assert msg.startswith("opendata auto-refresh: failed")


def test_auto_refresh_skips_when_up_to_date(monkeypatch):
    import app.search as search

    es = SyncES({"synced_at": opendata._iso(opendata._now()), "source_updated_at": "2026-05-21T20:49:53Z"})
    monkeypatch.setattr(search, "es_client", lambda: es)
    monkeypatch.setattr(opendata, "fetch_metadata", lambda: {"source_updated_at": "2026-05-21T20:49:53Z"})
    monkeypatch.setattr(opendata, "load_portfolio", lambda es: (_ for _ in ()).throw(AssertionError("no reload")))
    assert "up to date" in opendata.auto_refresh()


def test_load_portfolio_falls_back_to_snapshot_and_writes_sync(monkeypatch):
    import elasticsearch.helpers as helpers

    es = SyncES()
    monkeypatch.setattr(opendata, "fetch_portfolio", lambda: (_ for _ in ()).throw(OSError("offline")))
    monkeypatch.setattr(opendata, "fetch_metadata", lambda: (_ for _ in ()).throw(OSError("offline")))
    monkeypatch.setattr(helpers, "bulk", lambda es, actions, raise_on_error=False: (len(list(actions)), []))
    res = opendata.load_portfolio(es)
    assert res["origin"] == "snapshot" and res["indexed"] > 500
    assert res["sync"]["source_updated_at"] is None and opendata.read_sync(es)["origin"] == "snapshot"
