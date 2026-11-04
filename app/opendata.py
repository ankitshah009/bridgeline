"""San Francisco open data in Elasticsearch: the MOHCD affordable housing portfolio.

Source: DataSF, "Mayor's Office of Housing and Community Development Affordable Housing
Portfolio" (dataset pyxv-n29e, https://data.sf.gov/d/pyxv-n29e). A snapshot is kept in
app/data/sf_mohcd_portfolio.json so the demo does not depend on DataSF being up.
"""
from __future__ import annotations

import json
import logging
import math
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app import config

log = logging.getLogger("bridgeline.opendata")

INDEX_HOUSING = "homebase-sf-housing"
INDEX_SYNC = "homebase-sync"
SYNC_ID = "sf-housing"
REFRESH_AFTER = timedelta(hours=24)
DATASET_ID = "pyxv-n29e"
DATASET_URL = f"https://data.sf.gov/d/{DATASET_ID}"
METADATA_URL = f"https://data.sf.gov/api/views/{DATASET_ID}.json"
SNAPSHOT = config.DATA_DIR / "sf_mohcd_portfolio.json"
SOURCE_LABEL = "DataSF · MOHCD Affordable Housing Portfolio (pyxv-n29e)"

# MOHCD program -> housing type used by the benefits check. This is an inference for
# routing only; the operator confirms the real program type for each household.
PROGRAM_TO_HOUSING_TYPE = {
    "Rental Assistance Demonstration Program": "project_based",
    "HOPE SF": "public_housing",
    "Multifamily Rental Program": "LIHTC",
    "Multifamily Securities Program": "LIHTC",
    "Small Sites Program": "small_sites",
    "Inclusionary Housing Program": "inclusionary",
    "Transitional": "supportive",
}

MAPPING = {
    "properties": {
        "id": {"type": "keyword"},
        "name": {"type": "search_as_you_type"},
        "address": {"type": "search_as_you_type"},
        "zip": {"type": "keyword"},
        "neighborhood": {"type": "keyword"},
        "supervisor_district": {"type": "keyword"},
        "tenure": {"type": "keyword"},
        "status": {"type": "keyword"},
        "general_program": {"type": "keyword"},
        "program": {"type": "keyword"},
        "housing_type": {"type": "keyword"},
        "total_units": {"type": "integer"},
        "affordable_units": {"type": "integer"},
        "senior_units": {"type": "integer"},
        "tay_units": {"type": "integer"},
        "homeless_units": {"type": "integer"},
        "family_size_units": {"type": "integer"},
        "completed": {"type": "date"},
        "location": {"type": "geo_point"},
    }
}


def _int(v: Any) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def normalize(row: dict) -> dict | None:
    """One DataSF row -> one index document. Returns None for rows we can't use."""
    if not row.get("mohcd_development_id"):
        return None
    program = row.get("housing_program_program_name") or ""
    doc = {
        "id": row["mohcd_development_id"],
        "name": row.get("development_name") or row.get("marketing_address") or "",
        "address": row.get("marketing_address") or "",
        "zip": row.get("marketing_zip_code"),
        "neighborhood": row.get("city_analysis_marketing") or row.get("planning_neighborhood"),
        "supervisor_district": row.get("supervisor_district"),
        "tenure": row.get("tenure"),
        "status": row.get("project_status"),
        "general_program": row.get("general_housing_program"),
        "program": program,
        "housing_type": PROGRAM_TO_HOUSING_TYPE.get(program, "other"),
        "total_units": _int(row.get("total_project_units")),
        "affordable_units": _int(row.get("income_restricted_resid_units")),
        "senior_units": _int(row.get("senior_units_rollup")),
        "tay_units": _int(row.get("tay_units_rollup")),
        "homeless_units": _int(row.get("homeless_units_rollup")),
        "family_size_units": sum(
            _int(row.get(k))
            for k in ("_2_bedroom_units_rollup", "_3_bedroom_units_rollup",
                      "_4_bedroom_units_rollup", "_5_bedroom_units_rollup")
        ),
        "completed": (row.get("estimated_actual_construction") or "")[:10] or None,
    }
    lat, lon = row.get("latitude"), row.get("longitude")
    try:
        if lat and lon:
            doc["location"] = {"lat": float(lat), "lon": float(lon)}
    except ValueError:
        pass
    return doc


def fetch_portfolio(timeout: float = 30.0) -> list[dict]:
    """Download the live dataset from DataSF (SODA API)."""
    r = httpx.get(f"https://data.sf.gov/resource/{DATASET_ID}.json",
                  params={"$limit": 50000}, timeout=timeout)
    r.raise_for_status()
    return r.json()


def load_snapshot() -> list[dict]:
    return json.loads(SNAPSHOT.read_text())


def _es():
    from app.search import es_client  # owned by the search module; reuse its client

    es = es_client()
    if es is None:
        raise RuntimeError("Elasticsearch is not configured (ES_URL / ES_API_KEY)")
    return es


# ---------- freshness: DataSF metadata + sync record ----------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_metadata(timeout: float = 15.0) -> dict:
    """When DataSF last updated the dataset's rows (Socrata view metadata)."""
    r = httpx.get(METADATA_URL, timeout=timeout)
    r.raise_for_status()
    meta = r.json()
    epoch = meta.get("rowsUpdatedAt") or meta.get("viewLastModified")
    return {
        "name": meta.get("name"),
        "source_updated_at": _iso(datetime.fromtimestamp(int(epoch), timezone.utc)) if epoch else None,
    }


def write_sync(es, rows: int, source_updated_at: str | None, origin: str) -> dict:
    """Record what was loaded and when, in a tiny `homebase-sync` index."""
    doc = {
        "dataset": DATASET_ID,
        "source_updated_at": source_updated_at,
        "synced_at": _iso(_now()),
        "rows": rows,
        "origin": origin,  # "datasf-live" or "snapshot"
    }
    if not es.indices.exists(index=INDEX_SYNC):
        es.indices.create(index=INDEX_SYNC, mappings={"properties": {
            "dataset": {"type": "keyword"}, "source_updated_at": {"type": "date"},
            "synced_at": {"type": "date"}, "rows": {"type": "integer"}, "origin": {"type": "keyword"},
        }})
    es.index(index=INDEX_SYNC, id=SYNC_ID, document=doc, refresh=True)
    return doc


def read_sync(es=None) -> dict | None:
    """The last sync record, or None if it doesn't exist or can't be read."""
    try:
        es = es or _es()
        if not es.indices.exists(index=INDEX_SYNC):
            return None
        res = es.get(index=INDEX_SYNC, id=SYNC_ID)
        return dict(res["_source"])
    except Exception:  # missing doc, network, auth: freshness is informational only
        return None


def load_portfolio(es, *, use_snapshot: bool = False, reset: bool = False) -> dict:
    """Fetch (live, else snapshot), index into Elasticsearch, and write the sync record."""
    origin = "snapshot"
    rows: list[dict]
    if use_snapshot:
        rows = load_snapshot()
    else:
        try:
            rows = fetch_portfolio()
            SNAPSHOT.write_text(json.dumps(rows))
            origin = "datasf-live"
        except Exception as e:  # network trouble at the venue
            log.warning("DataSF fetch failed (%s); using snapshot", e)
            rows = load_snapshot()
    try:
        source_updated_at = fetch_metadata()["source_updated_at"]
    except Exception:
        source_updated_at = None

    from elasticsearch import helpers

    if reset and es.indices.exists(index=INDEX_HOUSING):
        es.indices.delete(index=INDEX_HOUSING)
    if not es.indices.exists(index=INDEX_HOUSING):
        es.indices.create(index=INDEX_HOUSING, mappings=MAPPING)
    docs = [d for d in (normalize(r) for r in rows) if d]
    ok, errors = helpers.bulk(
        es, ({"_index": INDEX_HOUSING, "_id": d["id"], "_source": d} for d in docs),
        raise_on_error=False,
    )
    es.indices.refresh(index=INDEX_HOUSING)
    sync = write_sync(es, rows=ok, source_updated_at=source_updated_at, origin=origin)
    return {"rows": len(rows), "indexed": ok, "errors": errors, "origin": origin, "sync": sync}


def needs_refresh(sync: dict | None, source_updated_at: str | None, now: datetime | None = None) -> bool:
    """Reload when never synced, when DataSF changed after our last sync, or after 24 h."""
    if not sync:
        return True
    synced = _parse(sync.get("synced_at"))
    if synced is None:
        return True
    source = _parse(source_updated_at)
    if source is not None and source > synced:
        return True
    return (now or _now()) - synced > REFRESH_AFTER


def auto_refresh() -> str:
    """Check DataSF and reload if stale. Never raises; returns a one-line status."""
    try:
        from app.search import es_client

        es = es_client()
        if es is None:
            return "opendata auto-refresh: skipped (Elasticsearch not configured)"
        sync = read_sync(es)
        try:
            source_updated_at = fetch_metadata()["source_updated_at"]
        except Exception as e:
            source_updated_at = None
            log.warning("DataSF metadata check failed: %s", e)
        if not needs_refresh(sync, source_updated_at):
            return (f"opendata auto-refresh: up to date (DataSF updated {source_updated_at}, "
                    f"synced {sync.get('synced_at') if sync else None})")
        res = load_portfolio(es)
        return (f"opendata auto-refresh: reloaded {res['indexed']} rows from {res['origin']} "
                f"(DataSF updated {res['sync']['source_updated_at']})")
    except Exception as e:  # never break the API over a background refresh
        return f"opendata auto-refresh: failed ({e.__class__.__name__}: {e})"


def start_auto_refresh() -> threading.Thread:
    """Run auto_refresh() once in a daemon thread so API startup never waits on DataSF."""
    def run():
        msg = auto_refresh()
        log.warning(msg)
        print(msg, flush=True)

    t = threading.Thread(target=run, name="opendata-auto-refresh", daemon=True)
    t.start()
    return t


def housing_query() -> dict:
    """Aggregation body for the city-wide context panel (rental buildings only)."""
    return {
        "size": 0,
        "track_total_hits": True,
        "query": {"bool": {"filter": [{"term": {"tenure": "Rental"}}]}},
        "aggs": {
            "units": {"sum": {"field": "total_units"}},
            "affordable_units": {"sum": {"field": "affordable_units"}},
            "family_size_units": {"sum": {"field": "family_size_units"}},
            "neighborhoods": {"cardinality": {"field": "neighborhood"}},
            "by_neighborhood": {
                "terms": {"field": "neighborhood", "size": 12, "order": {"units": "desc"}},
                "aggs": {"units": {"sum": {"field": "affordable_units"}}},
            },
            "by_program": {
                "terms": {"field": "program", "size": 8},
                "aggs": {"units": {"sum": {"field": "affordable_units"}}},
            },
        },
    }


def housing_stats() -> dict:
    """City-wide affordable rental stock, computed by Elasticsearch aggregations."""
    body = housing_query()
    es = _es()
    res = es.search(index=INDEX_HOUSING, **body)
    a = res["aggregations"]
    sync = read_sync(es) or {}
    return {
        "source": SOURCE_LABEL,
        "source_url": DATASET_URL,
        "source_updated_at": sync.get("source_updated_at"),
        "synced_at": sync.get("synced_at"),
        "sync_origin": sync.get("origin"),
        "buildings": res["hits"]["total"]["value"],
        "units": int(a["units"]["value"]),
        "affordable_units": int(a["affordable_units"]["value"]),
        "family_size_units": int(a["family_size_units"]["value"]),
        "neighborhoods": a["neighborhoods"]["value"],
        "by_neighborhood": [
            {"neighborhood": b["key"], "buildings": b["doc_count"], "units": int(b["units"]["value"])}
            for b in a["by_neighborhood"]["buckets"]
        ],
        "by_program": [
            {"program": b["key"], "buildings": b["doc_count"], "units": int(b["units"]["value"])}
            for b in a["by_program"]["buckets"]
        ],
        "query": body,
    }


def search_buildings(q: str, size: int = 6) -> list[dict]:
    """Find-your-building typeahead over real MOHCD rental buildings."""
    body = {
        "size": size,
        "query": {
            "bool": {
                "filter": [{"term": {"tenure": "Rental"}}],
                "must": [{
                    "multi_match": {
                        "query": q,
                        "type": "bool_prefix",
                        "fields": ["name", "name._2gram", "name._3gram",
                                   "address", "address._2gram", "address._3gram"],
                    }
                }],
            }
        },
    }
    res = _es().search(index=INDEX_HOUSING, **body)
    return [h["_source"] | {"_score": h["_score"]} for h in res["hits"]["hits"]]


def get_building(building_id: str) -> dict | None:
    res = _es().search(index=INDEX_HOUSING, size=1,
                       query={"term": {"id": building_id}})
    hits = res["hits"]["hits"]
    return hits[0]["_source"] if hits else None


def distance_km(a: dict | None, b: dict | None) -> float | None:
    """Great-circle distance between two {lat, lon} points, in km."""
    if not a or not b or "lat" not in a or "lat" not in b:
        return None
    r = 6371.0
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp, dl = p2 - p1, math.radians(b["lon"] - a["lon"])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(h)), 2)
