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


RATE_LIMIT_BACKOFF_S = (1.0, 2.0, 4.0)  # total wait at most 7 s before giving up


def _is_rate_limited(exc: Exception) -> bool:
    """Transient upstream conditions worth a short backoff: rate limits (429) and Mistral outages (502/503)."""
    text = str(exc)[:400]
    low = text.lower()
    return (
        any(f"Status {code}" in text for code in (429, 502, 503))
        or "rate limit" in low or "rate_limited" in text
        or "service unavailable" in low or "overloaded" in low
    )


def _complete(**kwargs):
    """Retry dropped connections once and rate limits (429) with backoff; never timeouts or other API errors."""
    import time

    waits = list(RATE_LIMIT_BACKOFF_S)
    reconnected = False
    while True:
        try:
            return _mistral().chat.complete(**kwargs)
        except Exception as exc:
            name = type(exc).__name__ + str(exc)[:200]
            if not reconnected and any(s in name for s in ("ConnectError", "SSL", "RemoteProtocolError", "ReadError")):
                reconnected = True
                continue
            if waits and _is_rate_limited(exc):
                time.sleep(waits.pop(0))
                continue
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
The resident lives in San Francisco affordable housing. Bridgeline funds tech and digital-skills training, but you
must record the resident's OWN goal faithfully. Never turn a non-tech goal (nursing, medical assistant, trades,
cooking, driving...) into a tech goal, and never invent a goal the message does not state.
Return ONLY a JSON object with exactly these keys:
- language: ISO code of the resident's message, one of en, es, zh, tl, vi (Traditional Chinese -> zh, Filipino/Tagalog -> tl)
- goal: short English goal in the resident's own meaning, e.g. "Become a medical assistant" or "Get an entry-level
  IT support job"; null if the message states no goal (for example a greeting like "hi")
- needs_clarification: true if the message has no clear goal, so a navigator must ask before matching
- follow_up: if needs_clarification, one short friendly question in the resident's language asking what work they
  want, when they could study, and whether they have kids who need care; otherwise null
- in_scope: true if the goal is tech, digital skills, computers, or learning to use technology; false if the stated
  goal is another field; true when there is no goal yet
- wants_digital_skills: true if the resident also says they want computer or digital skills (even with a non-tech goal)
- scope_note: if in_scope is false, one warm sentence in the resident's language saying Bridgeline focuses on tech
  training and showing free City training for their goal; otherwise null
- age_group: "under_25", "25_54" or "55_plus" ONLY if the resident states their age or says they are a senior or
  a young adult; otherwise null. Never guess age.
- career_tracks: English list from: "digital basics", "IT support", "help desk", "data center operations", "cybersecurity", "software development", "data analytics", "digital marketing", "UX design", "cloud".
  Use [] for a non-tech goal (add "digital basics" only if wants_digital_skills) and [] when there is no goal.
- experience: short English description of computer and work experience
- current_work: short English description of current job and hours, or "" if none
- availability: one of evenings, daytime, weekends, full-time, flexible (when they can attend training)
- hours_per_week_available: integer hours per week they could train (estimate; evenings-only ~8, full-time 40)
- needs_childcare: true if they mention children who need care while they train
- children: integer number of children mentioned, 0 if none
- has_computer: false unless they say they have a computer or laptop (a phone does not count)
- commute: one of muni, walk, bike, car, unknown
- summary: one English sentence for the navigator
- search_query: one English sentence describing the ideal training program for semantic search (level, schedule,
  field). For a non-tech goal describe free job training for THAT goal; with no goal use "beginner digital skills"
- display: object with keys goal, availability, experience, current_work: the same facts, short, written in the
  resident's own language (the language of their message) for profile cards they will read; goal "" if none
Rules: never record race, ethnicity, religion or immigration status, even if mentioned. Do not judge eligibility."""


def _bool(v, default=False) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "yes", "1", "si", "sí")
    if isinstance(v, (int, float)):
        return bool(v)
    return default


AGE_GROUPS = {"under_25", "25_54", "55_plus"}

# Messages that carry no goal at all. Matched after lowercasing and stripping punctuation.
GREETINGS = {
    "hi", "hello", "hey", "hiya", "yo", "help", "ok", "okay", "yes", "no", "thanks", "thank you", "start",
    "hola", "buenas", "buenos dias", "buenas tardes", "ayuda", "si", "sí",
    "你好", "您好", "哈囉", "嗨", "幫忙",
    "kumusta", "kamusta", "hello po", "tulong",
    "xin chào", "chào", "chao", "giúp",
}

FOLLOW_UP = {
    "en": "Happy to help! What kind of work would you like to do, when could you study, and do you have kids who need care while you train?",
    "es": "¡Con gusto te ayudo! ¿Qué tipo de trabajo te gustaría hacer, cuándo podrías estudiar y tienes hijos que necesiten cuidado mientras estudias?",
    "zh": "很樂意幫忙！你想做什麼樣的工作？什麼時間可以上課？上課時有孩子需要照顧嗎？",
    "tl": "Masaya kaming tumulong! Anong klaseng trabaho ang gusto mo, kailan ka pwedeng mag-aral, at may mga anak ka bang kailangang alagaan habang nag-aaral ka?",
    "vi": "Rất vui được giúp bạn! Bạn muốn làm công việc gì, khi nào bạn có thể học, và bạn có con nhỏ cần người trông khi đi học không?",
}

SCOPE_NOTE = {
    "en": "Bridgeline focuses on tech training, so here is free City training for your goal.",
    "es": "Bridgeline se enfoca en capacitación en tecnología, así que aquí tienes capacitación gratuita de la Ciudad para tu meta.",
    "zh": "Bridgeline 專注於科技培訓，以下是符合你目標的免費市政府培訓。",
    "tl": "Nakatuon ang Bridgeline sa tech training, kaya narito ang libreng training ng Lungsod para sa iyong layunin.",
    "vi": "Bridgeline tập trung vào đào tạo công nghệ, vì vậy đây là các chương trình đào tạo miễn phí của Thành phố cho mục tiêu của bạn.",
}


def is_greeting_only(text: str) -> bool:
    """True when the message is only a greeting or a filler word, so there is no goal to record."""
    t = re.sub(r"[\s!?.,¡¿~。！？，…]+", " ", (text or "").lower()).strip()
    return not t or t in GREETINGS


def _goal(value) -> str | None:
    g = str(value).strip() if value is not None else ""
    return None if not g or g.lower() in ("null", "none", "n/a", "unknown") else g


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
    tracks = [str(t) for t in tracks][:4]

    goal = _goal(raw.get("goal"))
    needs_clarification = _bool(raw.get("needs_clarification"), False) or goal is None or is_greeting_only(text)
    in_scope = _bool(raw.get("in_scope"), True)
    wants_digital = _bool(raw.get("wants_digital_skills"), False)
    if needs_clarification:
        goal, in_scope, tracks = None, True, []  # never invent a goal; ask first
    elif not in_scope:
        tracks = ["digital basics"] if wants_digital else []  # never recast a non-tech goal as tech
    age_group = str(raw.get("age_group") or "").strip().lower() or None
    if age_group not in AGE_GROUPS:
        age_group = None
    follow_up = (str(raw.get("follow_up") or "").strip() or FOLLOW_UP.get(lang, FOLLOW_UP["en"])) if needs_clarification else None
    scope_note = None if in_scope else (str(raw.get("scope_note") or "").strip() or SCOPE_NOTE.get(lang, SCOPE_NOTE["en"]))
    default_query = "beginner digital skills" if needs_clarification else (goal or "beginner tech training")

    profile = {
        "language": lang,
        "goal": goal,
        "needs_clarification": needs_clarification,
        "follow_up": follow_up,
        "in_scope": in_scope,
        "wants_digital_skills": wants_digital,
        "scope_note": scope_note,
        "age_group": age_group,
        "career_tracks": tracks,
        "experience": str(raw.get("experience") or ""),
        "current_work": str(raw.get("current_work") or ""),
        "availability": availability,
        "hours_per_week_available": hours,
        "needs_childcare": _bool(raw["needs_childcare"]) if raw.get("needs_childcare") is not None else children > 0,
        "children": children,
        "has_computer": _bool(raw.get("has_computer"), False),
        "commute": str(raw.get("commute") or "unknown"),
        "summary": str(raw.get("summary") or ""),
        "search_query": "beginner digital skills" if needs_clarification
        else str(raw.get("search_query") or default_query),
        "original_text": text,
    }
    disp = raw.get("display") if isinstance(raw.get("display"), dict) else {}
    profile["display"] = {k: str(disp.get(k) or profile[k] or "") for k in ("goal", "availability", "experience", "current_work")}
    if needs_clarification:
        profile["display"]["goal"] = ""
    return profile


GREETING_LANG = {"hola": "es", "buenas": "es", "buenos dias": "es", "buenas tardes": "es", "ayuda": "es",
                 "你好": "zh", "您好": "zh", "哈囉": "zh", "嗨": "zh", "幫忙": "zh",
                 "kumusta": "tl", "kamusta": "tl", "hello po": "tl", "tulong": "tl",
                 "xin chào": "vi", "chào": "vi", "chao": "vi", "giúp": "vi"}


def parse_intake(text: str, language_hint: str | None = None) -> dict:
    text = (text or "").strip()
    if not text:
        raise AIError("Empty intake text")
    if is_greeting_only(text):
        # Nothing to extract, so no model call: ask the follow-up instead of inventing a goal.
        key = re.sub(r"[\s!?.,¡¿~。！？，…]+", " ", text.lower()).strip()
        lang = GREETING_LANG.get(key) or (language_hint if language_hint in LANGS else "en")
        return _normalize_profile({"language": lang, "goal": None, "needs_clarification": True}, text, language_hint)
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
