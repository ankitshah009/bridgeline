"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { HTML_LANG, LANG_NAMES, makeT, normLang, type Lang } from "./i18n";
import { STATUS_LABEL, call, reducedMotion, type Any } from "./helpers";
import { PathProgress } from "./PathProgress";
import { JoinStep } from "./JoinStep";
import { PlanStep, intakeView, type IntakeState, type ScopeState } from "./PlanStep";
import { MatchStep, type MatchState } from "./MatchStep";
import { DetailStep, type DetailState } from "./DetailStep";
import { StatusStep, statusStep } from "./StatusStep";

type Screen = "join" | "plan" | "match" | "detail" | "status";
const STEP_OF: Record<Screen, number> = { join: 0, plan: 1, match: 2, detail: 3, status: 4 };

const store = {
  get(k: string) {
    try { return localStorage.getItem(k); } catch { return null; }
  },
  set(k: string, v: string) {
    try { localStorage.setItem(k, v); } catch { /* private mode */ }
  },
  del(k: string) {
    try { localStorage.removeItem(k); } catch { /* private mode */ }
  },
};

const EMPTY_INTAKE: IntakeState = { loading: false, error: null, profile: null, ms: null };
const EMPTY_MATCH: MatchState = { loading: false, error: null, programs: null, ms: null, query: null };
const EMPTY_DETAIL: DetailState = { loading: false, error: null, detail: null };
const EMPTY_SCOPE: ScopeState = { loading: false, alternatives: null, supports: null, techCount: 0 };

/** Deterministic pseudo-random in [0, 1) so confetti stays pure during render. */
const seeded = (n: number) => {
  const x = Math.sin(n * 12.9898 + 78.233) * 43758.5453;
  return x - Math.floor(x);
};

function Confetti() {
  const colors = ["#1fb24e", "#ffc933", "#6d4dff", "#ff7a2f", "#2f6bff", "#ff4f7e"];
  const bits = useMemo(
    () => Array.from({ length: 70 }, (_, i) => ({
      left: seeded(i * 3) * 100, delay: seeded(i * 3 + 1) * 0.6, rot: seeded(i * 3 + 2) * 360, color: colors[i % colors.length],
    })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );
  return (
    <div className="celebrate" aria-hidden="true">
      {bits.map((b, i) => (
        <i key={i} style={{ left: b.left + "%", background: b.color, animationDelay: b.delay + "s", transform: `rotate(${b.rot}deg)` }} />
      ))}
    </div>
  );
}

export function ResidentApp() {
  const [lang, setLang] = useState<Lang>("en");
  const t = useMemo(() => makeT(lang), [lang]);
  const [screen, setScreen] = useState<Screen>("join");
  const [property, setProperty] = useState<Any>(null);
  const [building, setBuilding] = useState<Any>(null);
  const [story, setStoryRaw] = useState("");
  const [intake, setIntake] = useState<IntakeState>(EMPTY_INTAKE);
  const [match, setMatch] = useState<MatchState>(EMPTY_MATCH);
  const [detail, setDetail] = useState<DetailState>(EMPTY_DETAIL);
  // Honesty states: a follow-up question when the story is too thin, and free help for non-tech goals.
  const [scope, setScope] = useState<ScopeState>(EMPTY_SCOPE);
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState<unknown>(null);
  const [app, setApp] = useState<Any>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [party, setParty] = useState(0);
  const prevStatus = useRef<string | null>(null);

  const busy = intake.loading || match.loading || detail.loading || applying || scope.loading;
  const view = intakeView(intake.profile);

  /* language */
  const applyLang = useCallback((l: Lang) => {
    setLang(l);
    store.set("hb.lang", l);
  }, []);
  useEffect(() => {
    document.documentElement.lang = HTML_LANG[lang];
  }, [lang]);

  const go = useCallback((s: Screen) => {
    setScreen(s);
    window.scrollTo({ top: 0, behavior: reducedMotion() ? "auto" : "smooth" });
  }, []);

  const showToast = useCallback((m: string) => {
    setToast(m);
    window.setTimeout(() => setToast((cur) => (cur === m ? null : cur)), 3800);
  }, []);

  /* boot: restore language + an application in progress; /?new=1 is the demo reset */
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.has("new")) {
      store.del("hb.app");
      store.del("hb.lang");
      const l = normLang(params.get("lang"));
      // eslint-disable-next-line react-hooks/set-state-in-effect -- restore from URL/localStorage after hydration
      if (l) setLang(l);
      return;
    }
    const l = normLang(store.get("hb.lang")) || normLang(params.get("lang"));
    if (l) setLang(l);
    const saved = store.get("hb.app");
    if (saved) {
      call(`/api/applications/${encodeURIComponent(saved)}`)
        .then((r) => {
          prevStatus.current = r.application.status;
          setApp(r.application);
          setScreen("status");
        })
        .catch(() => store.del("hb.app"));
    }
  }, []);

  /* live status polling (navigator approves on another screen): every 3 s, plus an
     immediate refetch when the tab becomes visible or the window regains focus, because
     browsers throttle timers in background tabs. */
  const appId: string | undefined = app?.id;
  useEffect(() => {
    if (screen !== "status" || !appId) return;
    let alive = true;
    let inFlight = false;
    const refresh = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const r = await call(`/api/applications/${encodeURIComponent(appId)}`);
        if (!alive) return;
        const a = r.application;
        setApp((old: Any) => {
          const changed = !old || a.status !== old.status || (a.payments || []).length !== (old.payments || []).length;
          return changed ? a : old;
        });
        if (a.status !== prevStatus.current) {
          if (a.status === "approved") {
            if (!reducedMotion()) setParty((n) => n + 1);
            showToast("✅ " + makeT(lang)("status_approved"));
          } else {
            showToast(STATUS_LABEL[a.status] || a.status);
          }
          prevStatus.current = a.status;
        }
      } catch {
        /* keep last known state; next poll retries */
      } finally {
        inFlight = false;
      }
    };
    const onVisible = () => {
      if (document.visibilityState === "visible") refresh();
    };
    const id = window.setInterval(refresh, 3000);
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("focus", refresh);
    refresh();
    return () => {
      alive = false;
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("focus", refresh);
    };
  }, [screen, appId, lang, showToast]);

  useEffect(() => {
    if (!party) return;
    const id = window.setTimeout(() => setParty(0), 3400);
    return () => window.clearTimeout(id);
  }, [party]);

  /* actions */
  const setStory = (s: string) => {
    setStoryRaw(s);
    if (intake.profile || intake.error) {
      setIntake(EMPTY_INTAKE);
      setScope(EMPTY_SCOPE);
    }
  };

  /* Goal outside tech: fetch free help for the path the resident described (and any tech options). */
  const checkScope = async (profile: Any) => {
    setScope({ ...EMPTY_SCOPE, loading: true });
    try {
      const r = await call("/api/match", { profile, property_code: property?.code, building_id: building?.id });
      const programs: Any[] = r.programs || [];
      const alternatives: Any[] = Array.isArray(r.alternatives) ? r.alternatives : [];
      const supports: Any[] = Array.isArray(r.supports) ? r.supports : [];
      setScope({ loading: false, alternatives, supports, techCount: programs.length });
      setMatch({ loading: false, error: null, programs, ms: r.ms ?? null, query: r.query ?? null, outOfScope: true, alternatives, supports });
    } catch (e) {
      setScope({ loading: false, alternatives: null, supports: null, techCount: 0, error: e });
    }
  };

  const doIntake = async (textArg?: string) => {
    const text = (textArg ?? story).trim();
    if (!text || busy) return;
    setIntake({ ...EMPTY_INTAKE, loading: true });
    setScope(EMPTY_SCOPE);
    try {
      const r = await call("/api/intake", { text, language: lang });
      setIntake({ loading: false, error: null, profile: r.profile, ms: r.ms ?? null });
      const nl = normLang(r.profile?.language);
      if (nl && nl !== lang) applyLang(nl);
      if (intakeView(r.profile) === "out_of_scope") checkScope(r.profile);
    } catch (e) {
      setIntake({ ...EMPTY_INTAKE, error: e });
    }
  };

  const doMatch = async () => {
    if (!intake.profile || busy) return;
    go("match");
    setMatch({ ...EMPTY_MATCH, loading: true });
    try {
      const r = await call("/api/match", { profile: intake.profile, property_code: property?.code, building_id: building?.id });
      setMatch({
        loading: false, error: null, programs: r.programs || [], ms: r.ms ?? null, query: r.query ?? null,
        outOfScope: Boolean(r.out_of_scope), alternatives: Array.isArray(r.alternatives) ? r.alternatives : null,
        supports: Array.isArray(r.supports) ? r.supports : null,
        needsClarification: Boolean(r.needs_clarification), followUp: r.follow_up ?? null,
      });
    } catch (e) {
      setMatch({ ...EMPTY_MATCH, error: e });
    }
  };

  /* The resident answers Mistral's follow-up: plan again from the original story plus the answer. */
  const answerFollowUp = (answer: string) => {
    const combined = `${story.trim()}\n${answer.trim()}`;
    setStoryRaw(combined);
    doIntake(combined);
  };

  const openPlan = async (pid: string) => {
    if (busy) return;
    setApplyError(null);
    go("detail");
    setDetail({ ...EMPTY_DETAIL, loading: true });
    try {
      const r = await call("/api/plan", { profile: intake.profile, program_id: pid, property_code: property?.code, building_id: building?.id });
      setDetail({ loading: false, error: null, detail: r });
    } catch (e) {
      setDetail({ ...EMPTY_DETAIL, error: e });
    }
  };

  const doApply = async () => {
    const d = detail.detail;
    if (!d || busy) return;
    setApplying(true);
    setApplyError(null);
    try {
      const r = await call("/api/applications", {
        profile: intake.profile, program_id: d.program?.id, property_code: property?.code, building_id: building?.id,
        waterfall: d.waterfall, benefits: d.benefits, plan: d.plan,
      });
      prevStatus.current = r.application.status;
      setApp(r.application);
      store.set("hb.app", r.application.id);
      go("status");
    } catch (e) {
      setApplyError(e);
      window.scrollTo({ top: 0, behavior: reducedMotion() ? "auto" : "smooth" });
    } finally {
      setApplying(false);
    }
  };

  const startOver = () => {
    store.del("hb.app");
    store.del("hb.lang");
    setLang("en");
    prevStatus.current = null;
    setProperty(null); setBuilding(null); setStoryRaw("");
    setIntake(EMPTY_INTAKE); setMatch(EMPTY_MATCH); setDetail(EMPTY_DETAIL);
    setScope(EMPTY_SCOPE);
    setApp(null); setApplyError(null);
    go("join");
  };

  /* sticky CTA */
  let cta: { label: string; onClick: () => void; disabled: boolean } | null = null;
  if (screen === "plan") {
    if (view === "none") cta = { label: t("build_plan"), onClick: () => doIntake(), disabled: !story.trim() || busy };
    else if (view === "profile") cta = { label: t("find_programs") + " →", onClick: doMatch, disabled: busy };
    else if (view === "out_of_scope" && scope.techCount > 0) {
      cta = { label: intake.profile?.wants_digital_skills ? t("oos_digital") : t("oos_tech"), onClick: () => go("match"), disabled: busy };
    }
    // "clarify": the follow-up card has its own send button.
  } else if (screen === "detail" && detail.detail) {
    cta = { label: t("apply"), onClick: doApply, disabled: busy };
  }

  const current = screen === "status" ? statusStep(app?.status) : STEP_OF[screen];

  return (
    <div className="resident">
      <div className="langbar">
        <span className="small muted langbar-k">{LANG_NAMES[lang]}</span>
        <label className="sr-only" htmlFor="lang">Language</label>
        <select id="lang" className="lang-select" aria-label="Language" value={lang} onChange={(e) => applyLang(e.target.value as Lang)}>
          {(Object.keys(LANG_NAMES) as Lang[]).map((l) => <option key={l} value={l}>{LANG_NAMES[l]}</option>)}
        </select>
      </div>

      <PathProgress current={current} t={t} />

      <div className="app" key={screen}>
        {screen === "join" && (
          <JoinStep t={t} building={building} setBuilding={setBuilding} onJoined={(p) => { setProperty(p); go("plan"); }} />
        )}
        {screen === "plan" && (
          <PlanStep
            t={t} lang={lang} property={property} story={story} setStory={setStory} intake={intake} onIntake={doIntake}
            view={view} scope={scope} onAnswer={answerFollowUp} onSeeTech={() => go("match")}
          />
        )}
        {screen === "match" && (
          <MatchStep
            t={t} state={match} onOpen={openPlan} busy={busy} scopeNote={intake.profile?.scope_note}
            onBackToPlan={() => { setMatch(EMPTY_MATCH); go("plan"); }}
          />
        )}
        {screen === "detail" && (
          <DetailStep t={t} state={detail} applyError={applyError} onBack={() => { setDetail(EMPTY_DETAIL); go("match"); }} />
        )}
        {screen === "status" && app && <StatusStep t={t} app={app} property={property} onStartOver={startOver} />}
      </div>

      {/* eslint-disable-next-line react-hooks/refs -- cta handlers only run on click, never during render */}
      {cta && (
        <div className="sticky-cta">
          <div className="inner">
            <button type="button" className="btn btn-primary btn-block" onClick={cta.onClick} disabled={cta.disabled}>
              {screen === "detail" && applying ? "…" : cta.label}
            </button>
          </div>
        </div>
      )}

      {toast && <div className="toast" role="status">{toast}</div>}
      {party > 0 && <Confetti key={party} />}

    </div>
  );
}
