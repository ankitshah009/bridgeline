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
