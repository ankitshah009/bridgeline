"use client";

import type { TFn } from "./i18n";
import { DistBadge, ErrorCard, PAYER, PAY_KEYS, PayBar, PayLegend, Thinking, TIER_LABEL, money, type Any } from "./helpers";
import { payLabels } from "./MatchStep";

export type DetailState = { loading: boolean; error: unknown; detail: Any };

function Ring({ pct, color }: { pct: number; color: string }) {
  const r = 22, c = 2 * Math.PI * r, v = (Math.max(0, Math.min(100, Number(pct) || 0)) / 100) * c;
  return (
    <svg className="ring" viewBox="0 0 56 56" aria-hidden="true">
      <circle cx="28" cy="28" r={r} fill="none" stroke="#e7e0d0" strokeWidth="7" />
      <circle cx="28" cy="28" r={r} fill="none" stroke={color} strokeWidth="7" strokeLinecap="round" strokeDasharray={`${v} ${c}`} transform="rotate(-90 28 28)" />
      <text x="28" y="33" textAnchor="middle" fontFamily="DM Sans, system-ui" fontWeight="800" fontSize="14" fill="#15182c">{pct}%</text>
    </svg>
  );
}

/* "Check these first": free help a resident may qualify for before the grant pays. */
const CATEGORY_WORDS: [RegExp, RegExp][] = [
  [/child|kid|care|preschool|early learning/i, /child|care/i],
  [/transit|muni|transport|clipper|bus|fare/i, /transit|muni|transport|clipper|fare|bus|pass/i],
  [/device|laptop|computer|tech/i, /laptop|device|computer|hotspot/i],
  [/internet|broadband|wifi|hotspot/i, /internet|broadband|hotspot|wi-?fi/i],
  [/tuition|training|education|school/i, /tuition|book|fee|material/i],
  [/exam|cert|test/i, /exam|cert/i],
];

function lineMatches(line: Any, resource: Any, check: Any): boolean {
  const item = `${line.item || ""} ${line.note || ""}`;
  const named = check?.item || check?.line;
  if (named && String(line.item || "").toLowerCase() === String(named).toLowerCase()) return true;
  const cat = `${resource?.category || ""} ${resource?.provides || ""} ${check?.program || ""}`;
  return CATEGORY_WORDS.some(([catRe, lineRe]) => catRe.test(cat) && lineRe.test(item));
}

function StatusPill({ status }: { status?: string }) {
  const s = String(status || "").toLowerCase();
  if (s.startsWith("avail")) return <span className="badge badge-green">Available</span>;
  if (s.startsWith("confirm") || s.startsWith("check") || s.startsWith("verify")) return <span className="badge badge-yellow">Confirm</span>;
  return status ? <span className="badge">{status}</span> : null;
}

function Resources({ resources }: { resources: Any[] }) {
  return (
    <div className="card resources">
      <div className="kicker">Check these first</div>
      <h3 style={{ marginTop: 6 }}>Free help you may qualify for</h3>
      <p className="small muted" style={{ marginTop: 4 }}>Your navigator checks these before the grant pays, so the grant only covers what&apos;s left.</p>
      <div className="res-list">
        {resources.map((x, i) => (
          <div className="res" key={x.id ?? i}>
            <div className="row" style={{ gap: 6 }}>
              <StatusPill status={x.status} />
              {x.category && <span className="badge">{x.category}</span>}
            </div>
            <div className="res-name">{x.program}</div>
            {x.provides && <div className="small">{x.provides}</div>}
            {x.who && <div className="small muted">Who: {x.who}</div>}
            {x.status_note && <div className="tiny muted">{x.status_note}</div>}
            {x._why && <div className="why" style={{ margin: "6px 0 0" }}>{x._why}</div>}
            {x.source_url && (
              <a className="small" href={x.source_url} target="_blank" rel="noopener noreferrer">Source ↗</a>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function Detail({ t, r }: { t: TFn; r: Any }) {
  const w = r.waterfall || {}, tot = w.totals || {}, p = r.program || {}, b = r.benefits || {}, plan = r.plan || {};
  const resources: Any[] = Array.isArray(r.resources) ? r.resources : [];
  const resById = new Map<string, Any>(resources.map((x) => [x.id, x]));
  const checks: Any[] = Array.isArray(w.checks_first) ? w.checks_first : [];
  const lines: Any[] = w.lines || [];
  const placed = new Set<number>();
  const checksFor = (line: Any) =>
    checks.filter((c, ci) => {
      const ok = lineMatches(line, resById.get(c.resource_id), c);
      if (ok) placed.add(ci);
      return ok;
    });
  const lineChecks = lines.map(checksFor);
  const unplaced = checks.filter((_, ci) => !placed.has(ci));
  const resident = Number(tot.resident) || 0;
  const value = PAY_KEYS.reduce((a, k) => a + (Number(tot[k]) || 0), 0);
  const L = payLabels(t) as Record<string, string>;
  const sched: Any[] = w.payment_schedule || [];
  const tuition = sched.filter((m) => Number(m.pct) < 100 || m.milestone !== "enrollment");
  const upfront = sched.filter((m) => !tuition.includes(m));
  const MS: Record<string, string> = { enrollment: t("ms_enroll"), completion: t("ms_complete"), placement: t("ms_place") };
  const colors = ["#1fb24e", "#2f6bff", "#6d4dff"];
  const ok = b.status === "protected";

  return (
    <>
      <div className="card-navy zero-hero">
        <svg className="spark" width="40" height="52" viewBox="0 0 40 52" style={{ top: 14, right: 18 }} aria-hidden="true">
          <path d="M24 0 4 30h12l-4 22 24-32H24z" fill="#ffc933" />
        </svg>
        <svg className="spark" width="80" height="80" viewBox="0 0 80 80" style={{ bottom: -20, left: -20 }} aria-hidden="true">
          <circle cx="40" cy="40" r="38" fill="none" stroke="#2c3670" strokeWidth="3" strokeDasharray="3 7" />
        </svg>
        <div className="kicker">{p.name}</div>
        <div className={"num" + (resident === 0 ? " zero" : "")}>{money(resident)}</div>
        <div className="foryou">{t("for_you")}</div>
        <div className="val">{money(value)} total · {p.provider}</div>
        <PayBar totals={tot} />
        <PayLegend totals={tot} labels={L} />
        {w.tier && (
          <div className="row" style={{ justifyContent: "center", marginTop: 14 }}>
            <span className="badge badge-purple">{TIER_LABEL[w.tier] || w.tier} grant · cap {money(w.tier_cap)}</span>
            {w.within_cap === false ? <span className="badge badge-orange">Over cap: navigator review</span> : <span className="badge badge-green">Within cap</span>}
          </div>
        )}
      </div>

      {(plan.message || plan.headline) && (
        <div className="ai-card">
          <div className="row"><span className="badge badge-ai">✦ {t("ai_label")}</span></div>
          {plan.headline && <h3 style={{ marginTop: 12 }}>{plan.headline}</h3>}
          {plan.message && <div className="bubble">{plan.message}</div>}
          {Array.isArray(plan.steps) && plan.steps.length > 0 && (
            <ol>{plan.steps.map((s: string, i: number) => <li key={i}>{s}</li>)}</ol>
          )}
        </div>
      )}

      <div className="card">
        <div className="kicker">{t("how_paid")}</div>
        {lines.map((l: Any, i: number) => {
          const py = PAYER[l.payer] || { label: l.payer, badge: "" };
          return (
            <div className="wline" key={i}>
              <span className="item">{l.item}</span>
              <span className="amt">{money(l.amount)}</span>
              <div className="sub">
                <span className={"badge " + py.badge}>{L[l.payer] || l.payer_label || py.label}</span>
                {l.paid_to && <span>→ {l.paid_to}</span>}
                {l.note && <span>· {l.note}</span>}
              </div>
              {lineChecks[i].map((c: Any, ci: number) => (
                <div className="check-first" key={ci}>
                  <span className="badge badge-yellow">Check first</span>
                  <span><strong>{c.program}</strong>{c.note ? ` · ${c.note}` : ""}</span>
                </div>
              ))}
            </div>
          );
        })}
        {unplaced.length > 0 && (
          <div className="check-first-list">
            {unplaced.map((c: Any, ci: number) => (
              <div className="check-first" key={ci}>
                <span className="badge badge-yellow">Check first</span>
                <span><strong>{c.program}</strong>{c.note ? ` · ${c.note}` : ""}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {resources.length > 0 && <Resources resources={resources} />}

      {tuition.length > 0 && (
        <div className="card">
          <div className="kicker">{t("milestones")}</div>
          <div className="milestones">
            {tuition.map((m, i) => (
              <div className="ms" key={i}>
                <Ring pct={m.pct} color={colors[i % 3]} />
                <b>{MS[m.milestone] || m.milestone}</b>
                <span>{money(m.amount)}{m.paid_to ? ` → ${m.paid_to}` : ""}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {upfront.length > 0 && (
        <div className="card">
          <div className="kicker">{t("upfront")}</div>
          {upfront.map((m, i) => (
            <div className="wline" key={i}>
              <span className="item">{m.item || m.paid_to || ""}</span>
              <span className="amt">{money(m.amount)}</span>
              <div className="sub"><span>→ {m.paid_to || ""}</span></div>
            </div>
          ))}
        </div>
      )}

      <div className={"shield" + (ok ? "" : " review")}>
        <div className="shield-head">
          <svg width="44" height="50" viewBox="0 0 44 50" aria-hidden="true">
            <path d="M22 2 40 9v14c0 12-8 21-18 25C12 44 4 35 4 23V9z" fill={ok ? "#1fb24e" : "#ffc933"} stroke="#15182c" strokeWidth="3" strokeLinejoin="round" />
            {ok ? (
              <path d="M13 25l6 6 12-13" stroke="#fff" strokeWidth="4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            ) : (
              <path d="M22 14v14M22 35v.5" stroke="#15182c" strokeWidth="4" strokeLinecap="round" />
            )}
          </svg>
          <div>
            <div className="kicker">{t("shield_title")}</div>
            <h3>{ok ? t("shield_ok") : t("shield_review")}</h3>
          </div>
        </div>
        {b.summary && <p className="small" style={{ marginTop: 10 }}>{b.summary}</p>}
        <ul>
          {(b.items || []).map((it: Any, i: number) => (
            <li key={i}>
              <span aria-hidden="true">{it.ok ? "✅" : "⚠️"}</span>
              <span>
                <strong>{it.line}:</strong> {it.treatment}
                {it.cite && <span className="cite">{it.cite}</span>}
              </span>
            </li>
          ))}
        </ul>
        <p className="disclaimer">{b.disclaimer || "Planning guidance, not legal advice. Your building's compliance team confirms before any award."}</p>
      </div>

      <div className="card-flat">
        <div className="kicker">Program</div>
        <h3 style={{ marginTop: 6 }}>{p.name}</h3>
        <p className="muted small">{p.provider}{p.neighborhood ? ` · ${p.neighborhood}` : ""}</p>
        {p.distance_km != null && <div className="row" style={{ marginTop: 6 }}><DistBadge km={p.distance_km} label={t("mi_home")} /></div>}
        {p.description && <p style={{ marginTop: 8 }}>{p.description}</p>}
        {Array.isArray(p.requirements) && p.requirements.length > 0 && (
          <p className="small muted" style={{ marginTop: 8 }}><strong>Provider requirements:</strong> {p.requirements.join("; ")}</p>
        )}
        {p.verify_note && <p className="tiny muted" style={{ marginTop: 6 }}>{p.verify_note}</p>}
        {p.url && <p className="small" style={{ marginTop: 8 }}><a href={p.url} target="_blank" rel="noopener noreferrer">Provider site ↗</a></p>}
      </div>

      {Array.isArray(w.assumptions) && w.assumptions.length > 0 && (
        <details className="assume">
          <summary>Planning assumptions</summary>
          <ul>{w.assumptions.map((a: string, i: number) => <li key={i}>{a}</li>)}</ul>
        </details>
      )}
    </>
  );
}

export function DetailStep({ t, state, onBack, applyError }: { t: TFn; state: DetailState; onBack: () => void; applyError: unknown }) {
  return (
    <section className="screen" aria-labelledby="detailTitle">
      <div className="section-head" style={{ paddingBottom: 8 }}>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onBack}>← <span>{t("back")}</span></button>
      </div>
      <h2 id="detailTitle" className="sr-only">Your plan</h2>
      <div className="stack" aria-live="polite">
        {applyError != null && <ErrorCard error={applyError} context="Couldn't send your application" />}
        {state.loading && (
          <>
            <Thinking msg={t("planning")} />
            <div className="skeleton" style={{ minHeight: 220 }} />
          </>
        )}
        {!state.loading && state.error != null && <ErrorCard error={state.error} context="Couldn't build your plan" />}
        {!state.loading && state.detail && <Detail t={t} r={state.detail} />}
      </div>
    </section>
  );
}
