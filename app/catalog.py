"""Static catalog: training programs, demo properties, funding sources, simulated pilot cohort."""
import json
from functools import lru_cache

from app.config import DATA_DIR


def _load(name: str):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _programs() -> tuple:
    return tuple(_load("programs.json"))


@lru_cache(maxsize=1)
def _properties() -> tuple:
    return tuple(_load("properties.json"))


def load_programs() -> list[dict]:
    return [dict(p) for p in _programs()]


def load_properties() -> list[dict]:
    return [dict(p) for p in _properties()]


def load_funding_sources() -> list[dict]:
    return sorted(_load("funding_sources.json"), key=lambda s: s["order"])


def load_pilot_cohort() -> list[dict]:
    return _load("pilot_cohort.json")


def get_program(pid: str) -> dict | None:
    return next((dict(p) for p in _programs() if p["id"] == pid), None)


def get_property(code: str) -> dict | None:
    code = (code or "").strip().upper()
    return next((dict(p) for p in _properties() if p["code"] == code), None)


def resident_cost(program: dict) -> float:
    """Sticker cost of a program to the resident before any aid (tuition + materials + exam fees)."""
    return float(program.get("tuition_usd", 0) + program.get("materials_usd", 0) + program.get("exam_fees_usd", 0))


def search_text(program: dict) -> str:
    """Lexical text for BM25 matching alongside the semantic description."""
    return " ".join([program["name"], program["provider"], " ".join(program.get("career_tracks", [])),
                     program.get("schedule", ""), program.get("neighborhood", ""), program["description"]])
