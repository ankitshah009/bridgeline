"""Mistral calls: intake parsing and plan drafting.

AI drafts and translates. It never decides eligibility or awards; app/rules.py and people do.
Failures raise AIError; callers show the failure instead of inventing output.
"""
from __future__ import annotations

import json
import re

from app import config

TIMEOUT_MS = 35_000  # Mistral Large can take 10-30 s on long prompts

AVAILABILITY = {"evenings", "daytime", "weekends", "full-time", "flexible"}
LANGS = {"en", "es", "zh", "tl", "vi"}


class AIError(RuntimeError):
    pass


_client = None


def api_key() -> str:
    """Key from config, re-reading .env if it was filled in after the server started."""
    if not config.MISTRAL_API_KEY:
        from dotenv import dotenv_values

        config.MISTRAL_API_KEY = (dotenv_values(config.ROOT / ".env").get("MISTRAL_API_KEY") or "").strip()
    return config.MISTRAL_API_KEY


def _mistral():
    global _client
    key = api_key()
    if not key:
        raise AIError("MISTRAL_API_KEY is not set in .env")
    if _client is None:
        from mistralai.client import Mistral

        _client = Mistral(api_key=key, timeout_ms=TIMEOUT_MS)
    return _client


def _complete(**kwargs):
    """One retry on dropped connections (seen as SSL EOF); never on timeouts or API errors."""
    try:
        return _mistral().chat.complete(**kwargs)
    except Exception as exc:
        name = type(exc).__name__ + str(exc)[:200]
        if any(s in name for s in ("ConnectError", "SSL", "RemoteProtocolError", "ReadError")):
            return _mistral().chat.complete(**kwargs)
        raise


def _chat_json(system: str, user: str, temperature: float = 0.1, max_tokens: int = 900) -> dict:
    try:
        resp = _complete(
            model=config.MISTRAL_CHAT_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_ms=TIMEOUT_MS,
        )
        content = resp.choices[0].message.content
        if isinstance(content, list):  # content chunks
            content = "".join(getattr(c, "text", "") or "" for c in content)
        return json.loads(content)
    except AIError:
        raise
    except Exception as exc:  # network, auth, bad JSON
        raise AIError(f"Mistral call failed: {type(exc).__name__}: {exc}") from exc


INTAKE_SYSTEM = """You turn a resident's message (any language) into a profile for a career navigator.
The resident lives in San Francisco affordable housing and wants digital skills or a tech-related job.
Return ONLY a JSON object with exactly these keys:
- language: ISO code of the resident's message, one of en, es, zh, tl, vi (Traditional Chinese -> zh, Filipino/Tagalog -> tl)
- goal: short English goal, e.g. "Get an entry-level IT support job"
- career_tracks: English list from: "digital basics", "IT support", "help desk", "data center operations", "cybersecurity", "software development", "data analytics", "digital marketing", "UX design", "cloud"
- experience: short English description of computer and work experience
- current_work: short English description of current job and hours, or "" if none
- availability: one of evenings, daytime, weekends, full-time, flexible (when they can attend training)
- hours_per_week_available: integer hours per week they could train (estimate; evenings-only ~8, full-time 40)
- needs_childcare: true if they mention children who need care while they train
- children: integer number of children mentioned, 0 if none
- has_computer: false unless they say they have a computer or laptop (a phone does not count)
- commute: one of muni, walk, bike, car, unknown
- summary: one English sentence for the navigator
- search_query: one English sentence describing the ideal training program for semantic search (level, schedule, field)
- display: object with keys goal, availability, experience, current_work: the same facts, short, written in the
  resident's own language (the language of their message) for profile cards they will read
Rules: never record race, ethnicity, religion or immigration status, even if mentioned. Do not judge eligibility."""


def _bool(v, default=False) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "yes", "1", "si", "sí")
    if isinstance(v, (int, float)):
        return bool(v)
    return default


def _normalize_profile(raw: dict, text: str, language_hint: str | None) -> dict:
    lang = str(raw.get("language") or language_hint or "en").lower().split("-")[0]
    if lang not in LANGS:
        lang = language_hint if language_hint in LANGS else "en"
    availability = str(raw.get("availability") or "flexible").lower()
    if availability not in AVAILABILITY:
        availability = "flexible"
    try:
        hours = int(round(float(raw.get("hours_per_week_available") or 0)))
    except (TypeError, ValueError):
        hours = 0
    if hours <= 0:
        hours = {"evenings": 8, "weekends": 8, "daytime": 20, "full-time": 40}.get(availability, 15)
    try:
        children = max(int(raw.get("children") or 0), 0)
    except (TypeError, ValueError):
        children = 0
    tracks = raw.get("career_tracks") or []
    if isinstance(tracks, str):
        tracks = [tracks]
    profile = {
        "language": lang,
        "goal": str(raw.get("goal") or "Explore a tech career"),
        "career_tracks": [str(t) for t in tracks][:4],
        "experience": str(raw.get("experience") or ""),
        "current_work": str(raw.get("current_work") or ""),
        "availability": availability,
        "hours_per_week_available": hours,
        "needs_childcare": _bool(raw["needs_childcare"]) if raw.get("needs_childcare") is not None else children > 0,
        "children": children,
        "has_computer": _bool(raw.get("has_computer"), False),
        "commute": str(raw.get("commute") or "unknown"),
        "summary": str(raw.get("summary") or ""),
        "search_query": str(raw.get("search_query") or raw.get("goal") or "beginner tech training"),
        "original_text": text,
    }
    disp = raw.get("display") if isinstance(raw.get("display"), dict) else {}
    profile["display"] = {k: str(disp.get(k) or profile[k]) for k in ("goal", "availability", "experience", "current_work")}
    return profile


def parse_intake(text: str, language_hint: str | None = None) -> dict:
    text = (text or "").strip()
    if not text:
        raise AIError("Empty intake text")
    hint = f"\n(UI language: {language_hint})" if language_hint else ""
    raw = _chat_json(INTAKE_SYSTEM, f"Resident's message:\n{text}{hint}")
    return _normalize_profile(raw, text, language_hint)


LANG_NAMES = {"en": "English", "es": "Spanish", "zh": "Traditional Chinese", "tl": "Filipino", "vi": "Vietnamese"}

PLAN_SYSTEM = """You draft a training plan for a San Francisco affordable-housing resident and their career navigator.
You do NOT decide eligibility or grant awards: a navigator and the grant committee do. Never promise approval.
Use only the facts given (program, funding lines, benefits check). Do not invent dates, rates or outcomes.
Name payers exactly as in payer_label: the training program is free, and the Bridgeline grant pays support costs.
Never say the city or the government pays unless a "Public aid" line is present.
Return ONLY a JSON object with keys:
- headline: short, warm headline in {lang} (max 10 words)
- steps: 3 to 5 short steps in {lang}, from now to the first day of class and the first job
- steps_en: the same steps in English, for the navigator
- message: 2-4 warm, plain sentences to the resident in {lang}, at a 6th-grade reading level. Say who pays for what,
  that money goes straight to providers (no cash), and that their navigator will review the plan.
- navigator_note: 2-3 English sentences for the navigator: fit, what to verify, next action
- risks: list of up to 3 short English risks to completion (schedule, child care, device, confidence)"""


def _unnumber(step) -> str:
    """The UI numbers steps itself; drop '1.' / '2)' prefixes the model adds."""
    return re.sub(r"^\s*\d+[.)]\s*", "", str(step))


def draft_plan(profile: dict, program: dict, waterfall: dict, benefits: dict) -> dict:
    lang = profile.get("language") or "en"
    facts = {
        "profile": {k: profile.get(k) for k in ("goal", "experience", "current_work", "availability",
                                                "hours_per_week_available", "needs_childcare", "children",
                                                "has_computer", "summary")},
        "program": {k: program.get(k) for k in ("name", "provider", "schedule", "hours_per_week", "weeks",
                                                "format", "neighborhood", "requirements", "free_to_resident",
                                                "verify_note")},
        "funding": {
            "tier": waterfall.get("tier_label"),
            "lines": [{k: l.get(k) for k in ("item", "amount", "payer_label", "paid_to")} for l in waterfall.get("lines", [])],
            "resident_pays": waterfall.get("totals", {}).get("resident", 0),
            "notes": waterfall.get("notes", []),
        },
        "benefits": {"status": benefits.get("status"), "summary": benefits.get("summary")},
    }
    raw = _chat_json(
        PLAN_SYSTEM.replace("{lang}", LANG_NAMES.get(lang, "English")),
        json.dumps(facts, ensure_ascii=False),
        temperature=0.3,
    )
    steps = raw.get("steps") or []
    steps_en = raw.get("steps_en") or (steps if lang == "en" else [])
    risks = raw.get("risks") or []
    return {
        "headline": str(raw.get("headline") or ""),
        "steps": [_unnumber(s) for s in steps][:5],
        "steps_en": [_unnumber(s) for s in steps_en][:5],
        "message": str(raw.get("message") or ""),
        "navigator_note": str(raw.get("navigator_note") or ""),
        "risks": [str(r) for r in risks][:3],
        "language": lang,
        "model": config.MISTRAL_CHAT_MODEL,
        "ai_draft": True,
    }
