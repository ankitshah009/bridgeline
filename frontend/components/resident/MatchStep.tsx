"use client";

import type { TFn } from "./i18n";
import { DistBadge, ErrorCard, PayBar, PayLegend, Thinking, TIER_LABEL, money, type Any } from "./helpers";
import { OutOfScopeCard } from "./Alternatives";

export type MatchState = {
  loading: boolean; error: unknown; programs: Any[] | null; ms: number | null; query: string | null;
  /** Set when the backend says the resident's goal is outside tech training. */
  outOfScope?: boolean;
  /** Free help for the path the resident actually described (resources index). */
  alternatives?: Any[] | null;
  /** Child care and transit help that applies to any path. */
  supports?: Any[] | null;
  /** Backend could not plan without more detail; ask the follow-up instead of showing nothing. */
  needsClarification?: boolean;
  followUp?: string | null;
};

/** The backend's role for a program; falls back to the position heuristic for older responses. */
export function matchRole(programs: Any[], i: number): "goal" | "on_ramp" | "other" | null {
  const r = programs[i]?.match_role;
  if (r === "goal" || r === "on_ramp" || r === "other") return r;
  return isOnRamp(programs, i) ? "on_ramp" : null;
}

/** A digital-basics program listed below a goal-specific one is the on-ramp to it, not the destination. */
export function isOnRamp(programs: Any[], i: number): boolean {
  if (i === 0 || programs[i]?.level !== "basics") return false;
  return programs.slice(0, i).some((q) => q?.level && q.level !== "basics");
}

export const SCHED: Record<string, string> = {
  "full-time-day": "Full-time · days", "part-time-day": "Part-time · days", "part-time-evening": "Evenings", "self-paced": "Self-paced",
};
const LEVEL: Record<string, [string, string]> = {
  basics: ["Digital basics", "badge-yellow"], entry: ["Entry level", "badge-blue"], career: ["Career program", "badge-purple"],
};

export const payLabels = (t: TFn) => ({
  free_program: t("pay_free"), public_aid: t("pay_public"), grant: t("pay_grant"), resident: t("pay_resident"),
});

function ProgramCard({ p, i, t, onOpen, disabled, role }: { p: Any; i: number; t: TFn; onOpen: (id: string) => void; disabled: boolean; role: string | null }) {
  const w = p.waterfall || {}, tot = w.totals || {};
  const lv = LEVEL[p.level] || [p.level || "Program", "badge-ink"];
  const resident = Number(tot.resident) || 0;
  const free = p.tuition_usd === 0 || p.free_to_resident;
  // A program known not to be running this term is shown last, muted, with the reason.
  const notRunning = p.offered_now === false;
  // Translated badges replace the backend's English "Matches your goal ·" / "On-ramp…·" / "Not running this term ·" prefixes.
  const roleBadge = role === "goal" || role === "on_ramp" || notRunning;
  const fit = roleBadge
    ? String(p.fit || "").replace(/^(matches your goal|on-ramp[^·]*|not running this term)\s*·\s*/i, "")
    : p.fit;
  const best = i === 0 && !notRunning;
  return (
    <button type="button" className={"prog" + (best ? " best" : "")} onClick={() => onOpen(p.id)} disabled={disabled}>
      {best && <span className="ribbon">⚡ {t("best_fit")}</span>}
      <div className="row">
        <span className={"badge " + lv[1]}>{lv[0]}</span>
        {notRunning && <span className="badge badge-off">{t("not_running")}</span>}
        {role === "goal" && <span className="badge badge-green">{t("goal_match")}</span>}
        {role === "on_ramp" && <span className="badge badge-blue" title={t("on_ramp_hint")}>{t("on_ramp")}</span>}
        {fit && <span className="badge badge-ink">{fit}</span>}
        {w.tier && <span className="badge badge-purple">{TIER_LABEL[w.tier] || w.tier}</span>}
      </div>
      <h3>{p.name}</h3>
      <div className="provider">{p.provider}</div>
      <div className="facts">
        {free ? <span className="badge badge-green">Free tuition</span> : <span className="badge badge-orange">Tuition {money(p.tuition_usd)}</span>}
        {p.schedule && <span className="badge">{SCHED[p.schedule] || p.schedule}</span>}
        {p.hours_per_week ? <span className="badge">{p.hours_per_week} h/wk{p.weeks ? ` × ${p.weeks} wks` : ""}</span> : null}
        {p.format && <span className="badge">{p.format}</span>}
        {p.neighborhood && <span className="badge">{p.neighborhood}</span>}
        <DistBadge km={p.distance_km} label={t("mi_home")} />
        {p.stipend && <span className="badge badge-yellow" title="Stipends may count as income">Stipend: check rent</span>}
        {p.illustrative && <span className="badge badge-red">Illustrative</span>}
      </div>
      {p._why && <div className="why">{p._why}</div>}
      {notRunning && p.availability_note && <div className="not-running-note">{p.availability_note}</div>}
      <PayBar totals={tot} />
      <PayLegend totals={tot} labels={payLabels(t)} />
      <div className="youpay">
        <span>
          <span className="small muted" style={{ fontWeight: 700 }}>{t("you_pay")}</span>{" "}
          <span className={"big" + (resident > 0 ? " nonzero" : "")}>{money(resident)}</span>
        </span>
        <span className="go">{t("see_plan")}</span>
      </div>
    </button>
  );
}

export function MatchStep({
  t, state, onOpen, busy, scopeNote, onBackToPlan,
}: {
  t: TFn; state: MatchState; onOpen: (id: string) => void; busy: boolean; scopeNote?: string | null; onBackToPlan?: () => void;
}) {
  const programs = state.programs || [];
  const outOfScope = Boolean(state.outOfScope);
  return (
    <section className="screen" aria-labelledby="matchTitle">
      <div className="section-head">
        <span className="kicker">{t("step_match_k")}</span>
        <h2 id="matchTitle">{t("match_title")}</h2>
        <p>{t("match_sub")}</p>
      </div>
      <div className="stack" aria-live="polite">
        {state.loading && (
          <>
            <Thinking msg={t("searching")} />
            <div className="skeleton" />
            <div className="skeleton" />
          </>
        )}
        {!state.loading && state.error != null && <ErrorCard error={state.error} context="Couldn't search programs" />}
        {!state.loading && state.error == null && state.needsClarification && (
          <div className="followup">
            <div className="kicker">{t("clarify_title")}</div>
            <p className="followup-q">{state.followUp || t("clarify_default")}</p>
            {onBackToPlan && <button type="button" className="btn btn-primary" onClick={onBackToPlan}>{t("clarify_back")}</button>}
          </div>
        )}
        {!state.loading && state.error == null && outOfScope && (
          <OutOfScopeCard t={t} note={scopeNote} alternatives={state.alternatives ?? []} supports={state.supports} loading={false} hasTech={false} />
        )}
        {!state.loading && state.error == null && !outOfScope && !state.needsClarification && state.programs && programs.length === 0 && (
          <div className="card-flat">{t("no_match")}</div>
        )}
        {!state.loading && programs.length > 0 && (
          <>
            {outOfScope && <div className="kicker" style={{ marginTop: 8 }}>{t("oos_tech_heading")}</div>}
            <div className="search-proof">
              <span className="badge badge-blue">Elasticsearch</span>
              <span>{programs.length} matches · semantic search{state.ms != null ? ` · ${state.ms} ms` : ""}</span>
              {state.query && <code>{state.query}</code>}
            </div>
            {programs.map((p, i) => (
              <ProgramCard key={p.id} p={p} i={i} t={t} onOpen={onOpen} disabled={busy} role={matchRole(programs, i)} />
            ))}
          </>
        )}
      </div>
    </section>
  );
}
