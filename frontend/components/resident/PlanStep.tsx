"use client";

import { useEffect, useRef, useState } from "react";
import { LANG_NAMES, SPEECH_LANG, normLang, type Lang, type TFn } from "./i18n";
import { Bolt, ErrorCard, Thinking, reducedMotion, type Any } from "./helpers";

export const EXAMPLES: { lang: Lang; flag: string; text: string }[] = [
  { lang: "es", flag: "ES", text: "Trabajo de día cuidando ancianos, tengo dos hijos y quiero trabajar en computadoras. Solo puedo estudiar en la noche." },
  { lang: "zh", flag: "中文", text: "我在餐廳全職工作，想學電腦，找辦公室的工作。我沒有電腦，週末和晚上有空。" },
  { lang: "en", flag: "EN", text: "I got laid off from a warehouse job. I'm good with computers and want an IT help desk job fast. I can study full time." },
];

export type IntakeState = { loading: boolean; error: unknown; profile: Any; ms: number | null };

function ProfileCards({ t, profile, ms }: { t: TFn; profile: Any; ms: number | null }) {
  const p = profile || {};
  // Resident-facing values in their own language when the backend provides them.
  const d = (p.display && typeof p.display === "object" ? p.display : {}) as Any;
  const nl = normLang(p.language);
  const yn = (v: unknown, a: string, b: string) => (v === true ? a : v === false ? b : "—");
  const sched = d.availability
    ? String(d.availability)
    : [p.availability, p.hours_per_week_available ? `${p.hours_per_week_available} h/wk` : null].filter(Boolean).join(" · ");
  const child = p.needs_childcare ? t("needed") + (p.children ? ` · ${p.children}` : "") : p.needs_childcare === false ? t("not_needed") : "—";
  const cards: [string, string, string][] = [
    ["c1 wide", t("k_goal"), d.goal || p.goal || (p.career_tracks || []).join(", ") || "—"],
    ["c2", t("k_sched"), sched || "—"],
    ["c3", t("k_child"), child],
    ["c4", t("k_comp"), yn(p.has_computer, t("has_one"), t("needs_one"))],
    ["c5", t("k_work"), d.current_work || p.current_work || "—"],
    ["", t("k_lang"), (nl && LANG_NAMES[nl]) || p.language || "—"],
    ["", t("k_exp"), d.experience || p.experience || "—"],
  ];
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" });
  }, []);
  return (
    <div className="understood" ref={ref}>
      <div className="understood-head">
        <span className="bolt"><Bolt /></span>
        <h3>{t("understood")}</h3>
        <span className="spacer" />
        <span className="badge badge-ai">Mistral{ms != null ? ` · ${(ms / 1000).toFixed(1)} s` : ""}</span>
      </div>
      {/* The English `summary` is for the navigator; residents see only their own language. */}
      <div className="pgrid">
        {cards.map(([cls, k, v]) => (
          <div key={k} className={"pcard " + cls}>
            <div className="k">{k}</div>
            <div className="v">{v}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

type SR = Any;

export function PlanStep({
  t, lang, property, story, setStory, intake, onIntake,
}: {
  t: TFn; lang: Lang; property: Any; story: string; setStory: (s: string) => void;
  intake: IntakeState; onIntake: (text: string) => void;
}) {
  const [listening, setListening] = useState(false);
  const [micHint, setMicHint] = useState("");
  const [hasSR, setHasSR] = useState(false);
  const recRef = useRef<SR>(null);
  const storyRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const w = window as Any;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- browser-only feature detection after hydration
    setHasSR(Boolean(w.SpeechRecognition || w.webkitSpeechRecognition));
    const id = setTimeout(() => storyRef.current?.focus({ preventScroll: true }), 350);
    return () => {
      clearTimeout(id);
      recRef.current?.stop?.();
    };
  }, []);

  const toggleMic = () => {
    if (recRef.current) {
      recRef.current.stop();
      return;
    }
    const w = window as Any;
    const Ctor = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!Ctor) return;
    const rec = new Ctor();
    rec.lang = SPEECH_LANG[lang] || "en-US";
    rec.interimResults = true;
    rec.continuous = true;
    const base = story ? story.replace(/\s*$/, " ") : "";
    rec.onresult = (ev: Any) => {
      let s = "";
      for (let i = 0; i < ev.results.length; i++) s += ev.results[i][0].transcript;
      setStory(base + s);
    };
    rec.onend = () => {
      recRef.current = null;
      setListening(false);
      setMicHint("");
    };
    rec.onerror = (ev: Any) => setMicHint(ev.error === "not-allowed" ? "Microphone blocked. You can type instead." : "");
    recRef.current = rec;
    setListening(true);
    setMicHint(t("listening"));
    try {
      rec.start();
    } catch {
      recRef.current = null;
      setListening(false);
    }
  };

  return (
    <section className="screen" aria-labelledby="planTitle">
      <div className="section-head">
        <span className="kicker">{t("step_plan_k")}</span>
        <h2 id="planTitle">{t("plan_title")}</h2>
        <p>{t("plan_sub")}</p>
        {property && (
          <div className="welcome">
            <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true">
              <circle cx="14" cy="14" r="13" fill="#1fb24e" />
              <path d="M8 14l4 4 8-9" stroke="#fff" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span>{property.name}{property.neighborhood ? ` · ${property.neighborhood}` : ""}</span>
          </div>
        )}
      </div>
      <div className="stack">
        <div className="field">
          <label htmlFor="story" className="sr-only">Your story</label>
          <textarea
            id="story"
            ref={storyRef}
            className="input"
            rows={5}
            placeholder="I work days as a caregiver, I have two kids…"
            value={story}
            onChange={(e) => setStory(e.target.value)}
          />
        </div>
        {hasSR && (
          <div className="row">
            <button
              type="button"
              className={"btn btn-ghost btn-icon mic" + (listening ? " listening" : "")}
              aria-label="Speak instead of typing"
              aria-pressed={listening}
              title="Speak"
              onClick={toggleMic}
            >
              <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
                <rect x="8" y="2" width="8" height="13" rx="4" fill="currentColor" />
                <path d="M5 11a7 7 0 0 0 14 0M12 18v4M8 22h8" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" />
              </svg>
            </button>
            <span className="small muted">{micHint}</span>
          </div>
        )}
        <div>
          <p className="small muted" style={{ marginBottom: 8, fontWeight: 700 }}>{t("try_one")}</p>
          <div className="example-chips">
            {EXAMPLES.map((ex) => (
              <button
                key={ex.flag}
                type="button"
                className="chip"
                disabled={intake.loading}
                onClick={() => {
                  setStory(ex.text);
                  onIntake(ex.text);
                }}
              >
                <span className="flag">{ex.flag}</span>
                <span>{ex.text}</span>
              </button>
            ))}
          </div>
        </div>
        <div aria-live="polite">
          {intake.loading && <Thinking msg={t("reading")} />}
          {!intake.loading && intake.error != null && <ErrorCard error={intake.error} context="Couldn't read your story" />}
          {!intake.loading && intake.profile && <ProfileCards t={t} profile={intake.profile} ms={intake.ms} />}
        </div>
      </div>
    </section>
  );
}
