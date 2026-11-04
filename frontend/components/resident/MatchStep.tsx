"use client";

import type { TFn } from "./i18n";
import { DistBadge, ErrorCard, PayBar, PayLegend, Thinking, TIER_LABEL, money, type Any } from "./helpers";

export type MatchState = { loading: boolean; error: unknown; programs: Any[] | null; ms: number | null; query: string | null };

export const SCHED: Record<string, string> = {
  "full-time-day": "Full-time · days", "part-time-day": "Part-time · days", "part-time-evening": "Evenings", "self-paced": "Self-paced",
};
const LEVEL: Record<string, [string, string]> = {
  basics: ["Digital basics", "badge-yellow"], entry: ["Entry level", "badge-blue"], career: ["Career program", "badge-purple"],
};

export const payLabels = (t: TFn) => ({
  free_program: t("pay_free"), public_aid: t("pay_public"), grant: t("pay_grant"), resident: t("pay_resident"),
});

function ProgramCard({ p, i, t, onOpen, disabled }: { p: Any; i: number; t: TFn; onOpen: (id: string) => void; disabled: boolean }) {
  const w = p.waterfall || {}, tot = w.totals || {};
  const lv = LEVEL[p.level] || [p.level || "Program", "badge-ink"];
  const resident = Number(tot.resident) || 0;
  const free = p.tuition_usd === 0 || p.free_to_resident;
  return (
    <button type="button" className={"prog" + (i === 0 ? " best" : "")} onClick={() => onOpen(p.id)} disabled={disabled}>
      {i === 0 && <span className="ribbon">⚡ {t("best_fit")}</span>}
      <div className="row">
        <span className={"badge " + lv[1]}>{lv[0]}</span>
        {p.fit && <span className="badge badge-ink">{p.fit}</span>}
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

export function MatchStep({ t, state, onOpen, busy }: { t: TFn; state: MatchState; onOpen: (id: string) => void; busy: boolean }) {
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
        {!state.loading && state.programs && state.programs.length === 0 && (
          <div className="card-flat">No programs matched. A navigator will reach out to plan with you.</div>
        )}
        {!state.loading && state.programs && state.programs.length > 0 && (
          <>
            <div className="search-proof">
              <span className="badge badge-blue">Elasticsearch</span>
              <span>{state.programs.length} matches · semantic search{state.ms != null ? ` · ${state.ms} ms` : ""}</span>
              {state.query && <code>{state.query}</code>}
            </div>
            {state.programs.map((p, i) => (
              <ProgramCard key={p.id} p={p} i={i} t={t} onOpen={onOpen} disabled={busy} />
            ))}
          </>
        )}
      </div>
    </section>
  );
}
