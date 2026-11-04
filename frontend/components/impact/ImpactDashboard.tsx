"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { api, ApiError } from "@/lib/api";
import { CountUp, Donut, HBar, Ring, SplitBar, StackBar, compactMoney, fmt, money, type PaySlice } from "./charts";
import type { Budget, Health, Housing, Impact, Loaded } from "./types";

const REFRESH_MS = 5000;
const AWARDED = ["approved", "enrolled", "completed", "placed"] as const;
const TIER_LABEL: Record<string, string> = { starter: "Starter · $500", stay_in_training: "Stay-in-Training · $2,500", career: "Career · $6,000" };
const LANG_LABEL: Record<string, string> = { en: "English", es: "Español", zh: "繁體中文", "zh-Hant": "繁體中文", tl: "Filipino", fil: "Filipino", vi: "Tiếng Việt" };
const FUNNEL_COLORS = ["var(--blue)", "#5a7dff", "var(--purple)", "#8f6bff", "var(--green-hi)", "var(--orange)"];

function toErr(e: unknown): { message: string; stage: string } {
  if (e instanceof ApiError) return { message: e.message, stage: e.stage || "server" };
  if (e instanceof Error) return { message: e.message, stage: "network" };
  return { message: String(e), stage: "server" };
}

const empty = <T,>(): Loaded<T> => ({ data: null, error: null, at: null });

function useLive<T>(path: string, every: number | null) {
  const [state, setState] = useState<Loaded<T>>(empty<T>());
  const load = useCallback(async () => {
    try {
      const data = await api<T>(path);
      setState({ data, error: null, at: Date.now() });
    } catch (e) {
      // keep last good data on screen, but show the failure
      setState((s) => ({ ...s, error: toErr(e), at: Date.now() }));
    }
  }, [path]);
  useEffect(() => {
    load();
    if (!every) return;
    const id = setInterval(() => {
      if (!document.hidden) load();
    }, every);
    return () => clearInterval(id);
  }, [load, every]);
  return state;
}

function ErrorCard({ error, context }: { error: { message: string; stage: string }; context: string }) {
  const label: Record<string, string> = { mistral: "Mistral", elastic: "Elasticsearch", network: "Network", server: "Server", api: "Server" };
  return (
    <div className="error-card" role="alert">
      <div>
        <span className="stage">{label[error.stage] ?? error.stage}</span>
        <strong>{context}</strong>
      </div>
      <div className="small">{error.message}</div>
      <div className="tiny muted">Nothing here is faked. This step failed, so no numbers are shown for it.</div>
    </div>
  );
}

function Skeleton({ h = 140 }: { h?: number }) {
  return <div className="skeleton" style={{ minHeight: h }} />;
}

function HealthPills({ h }: { h: Loaded<Health> }) {
  if (!h.data && !h.error) return <span className="imp-pill"><i />Checking Mistral and Elastic…</span>;
  if (!h.data) return <span className="imp-pill bad"><i />Server unreachable: {h.error?.message}</span>;
  const e = h.data.elastic ?? ({} as Health["elastic"]);
  return (
    <>
      <span className={`imp-pill ${h.data.mistral ? "ok" : "bad"}`}>
        <i />
        Mistral {h.data.mistral ? h.data.mistral_model ?? "connected" : "not configured"}
      </span>
      <span className={`imp-pill ${e.connected ? "ok" : "bad"}`}>
        <i />
        Elastic {e.connected ? e.cluster ?? "connected" : e.error ?? "not connected"}
      </span>
      {e.inference_id ? (
        <span className="imp-pill ok">
          <i />
          Embeddings · {e.inference_id}
        </span>
      ) : null}
      {e.connected ? (
        <span className="imp-pill">
          <i />
          {fmt(e.programs)} programs · {fmt(e.applications)} applications indexed
        </span>
      ) : null}
    </>
  );
}

function HousingContext({ s }: { s: Loaded<Housing> }) {
  if (!s.data && s.error) return <ErrorCard error={s.error} context="Couldn't load DataSF housing context from Elasticsearch" />;
  if (!s.data) return <Skeleton h={260} />;
  const d = s.data;
  const nb = (d.by_neighborhood ?? []).slice(0, 10);
  const maxN = Math.max(1, ...nb.map((x) => x.units || 0));
  const prog = (d.by_program ?? []).slice(0, 6);
  const maxP = Math.max(1, ...prog.map((x) => x.units || 0));
  const homes = d.affordable_units || d.units;
  const pilotShare = homes ? (1000 / homes) * 100 : null;
  return (
    <>
      <div className="imp-ctx-stats">
        <div>
          <b className="c-purple"><CountUp value={d.buildings} /></b>
          <span>affordable rental buildings</span>
        </div>
        <div>
          <b className="c-green"><CountUp value={homes} /></b>
          <span>income-restricted homes</span>
        </div>
        <div>
          <b className="c-orange"><CountUp value={d.neighborhoods} /></b>
          <span>neighborhoods</span>
        </div>
        <div className="pilot">
          <b>1,000</b>
          <span>
            homes in the pilot{pilotShare != null ? ` (${pilotShare.toFixed(1)}% of the city's stock)` : ""}, 3,000 by end of 2028
          </span>
        </div>
      </div>
      <div className="imp-ctx-grid">
        <div className="card">
          <span className="kicker">Affordable homes by neighborhood · top 10</span>
          <div className="imp-bars">
            {nb.map((x) => (
              <HBar
                key={x.neighborhood}
                label={x.neighborhood}
                value={x.units}
                max={maxN}
                color="var(--purple)"
                right={
                  <>
                    {fmt(x.units)} <small>· {fmt(x.buildings)} bldgs</small>
                  </>
                }
              />
            ))}
          </div>
        </div>
        <div className="card">
          <span className="kicker">By housing program</span>
          <div className="imp-bars">
            {prog.map((x) => (
              <HBar key={x.program} label={x.program} value={x.units} max={maxP} color="var(--orange)" right={fmt(x.units)} />
            ))}
          </div>
          <p className="imp-note">
            Each housing program counts income differently. That&apos;s why a benefits check runs before every award, and the grant pays
            vendors instead of giving residents cash.
          </p>
        </div>
      </div>
      <p className="imp-note imp-src">
        Source:{" "}
        {d.source_url ? (
          <a href={d.source_url} target="_blank" rel="noopener noreferrer">
            {d.source} ↗
          </a>
        ) : (
          d.source
        )}{" "}
        · rental buildings only · aggregated live in Elasticsearch
      </p>
    </>
  );
}

function Kpi({
  label,
  value,
  target,
  frac,
  tone,
  sub,
  pulse,
}: {
  label: string;
  value: ReactNode;
  target: string;
  frac: number;
  tone: "green" | "yellow" | "purple" | "blue";
  sub?: string;
  pulse?: boolean;
}) {
  return (
    <div className={`imp-kpi${pulse ? " pulse" : ""}`}>
      <span className="k">{label}</span>
      <div className="imp-kpi-row">
        <span className="v">{value}</span>
        <Ring frac={frac} tone={tone}>
          <b>{Number.isFinite(frac) ? `${Math.round(Math.min(frac, 9.99) * 100)}%` : "—"}</b>
          <small>of goal</small>
        </Ring>
      </div>
      <span className="tgt">{target}</span>
      {sub ? <span className="sub">{sub}</span> : null}
    </div>
  );
}

function BudgetCard({ b }: { b?: Budget }) {
  if (!b) return <p className="muted small">No budget returned.</p>;
  const pool = b.items.find((i) => /grant pool/i.test(i.item))?.amount ?? 0;
  const nav = b.items.find((i) => /navigator/i.test(i.item))?.amount ?? 0;
  const rest = Math.max(0, b.total - pool - nav);
  return (
    <div className="imp-budget">
      <div className="imp-budget-top">
        <Donut size={150}
          parts={[
            { value: pool, color: "var(--purple)" },
            { value: nav, color: "var(--green-hi)" },
            { value: rest, color: "#c9d7ff" },
          ]}
          label={
            <>
              <b>{money(b.total)}</b>
              <span>pilot total</span>
            </>
          }
        />
        <div className="imp-unit">
          <div>
            <b>{money(b.per_recipient ?? (b.recipients ? b.total / b.recipients : 0))}</b>
            <span>per grant recipient ({b.recipients ?? "—"})</span>
          </div>
          <div className="hi">
            <b>{money(b.per_successful_outcome ?? (b.expected_successes ? b.total / b.expected_successes : 0))}</b>
            <span>per successful outcome ({b.expected_successes ?? "—"} placed or earning more)</span>
          </div>
        </div>
      </div>
      <table>
        <tbody>
          {b.items.map((i) => (
            <tr key={i.item}>
              <td>
                <i
                  className="sw"
                  style={{ background: /grant pool/i.test(i.item) ? "var(--purple)" : /navigator/i.test(i.item) ? "var(--green-hi)" : "#c9d7ff" }}
                />
                {i.item}
              </td>
              <td className="num">{money(i.amount)}</td>
            </tr>
          ))}
          <tr className="total">
            <td>Total</td>
            <td className="num">{money(b.total)}</td>
          </tr>
        </tbody>
      </table>
      <p className="imp-note">
        {b.note ?? "Planning assumptions, not quotes."} The navigator is a lasting cost and shouldn&apos;t be cut to raise the grant share.
      </p>
    </div>
  );
}

function Scorecard({ s, flash }: { s: Loaded<Impact>; flash: Set<string> }) {
  if (!s.data && s.error) return <ErrorCard error={s.error} context="Couldn't load pilot aggregates from Elasticsearch" />;
  if (!s.data) return <Skeleton h={180} />;
  const d = s.data;
  const t = d.targets ?? {};
  const bs = d.by_status ?? {};
  const awarded = AWARDED.reduce((n, k) => n + (bs[k] ?? 0), 0);
  const enrolled = bs.enrolled ?? 0;
  const completed = d.outcomes?.completed ?? 0;
  const placed = d.outcomes?.placed_or_raise ?? 0;
  const completionTarget = t.completion_rate ?? 0.7;
  const placementTarget = t.placement_rate ?? 0.7;
  const decisionTarget = t.decision_days ?? 10;
  const activatedTarget = t.activated ?? 200;
  const compRate = awarded ? completed / awarded : 0;
  const placeRate = completed ? placed / completed : 0;
  const mdd = d.median_decision_days;
  return (
    <div className="imp-kpis">
      <Kpi
        label="Residents activated"
        value={<CountUp value={d.total} />}
        target={`Pilot target ${fmt(activatedTarget)}`}
        frac={d.total / activatedTarget}
        tone="blue"
        pulse={flash.has("total")}
      />
      <Kpi
        label="Grants approved"
        value={<CountUp value={awarded} />}
        target="Pilot gate 20 · Prove phase 40"
        frac={awarded / 40}
        tone="purple"
        pulse={flash.has("awarded")}
      />
      <Kpi
        label="Completed training"
        value={awarded ? `${Math.round(compRate * 100)}%` : "—"}
        target={`Target ${Math.round(completionTarget * 100)}% of recipients`}
        frac={compRate / completionTarget}
        tone={compRate >= completionTarget ? "green" : "yellow"}
        sub={enrolled ? `${fmt(enrolled)} still in training` : undefined}
        pulse={flash.has("completed")}
      />
      <Kpi
        label="Placed or earning more"
        value={completed ? `${Math.round(placeRate * 100)}%` : "—"}
        target={`Target ${Math.round(placementTarget * 100)}% of completers in 180 days`}
        frac={placeRate / placementTarget}
        tone={placeRate >= placementTarget ? "green" : "yellow"}
        pulse={flash.has("placed")}
      />
      <Kpi
        label="Median days to decision"
        value={mdd == null ? "—" : Number(mdd).toFixed(1)}
        target={`Target ≤ ${decisionTarget} business days`}
        frac={mdd == null ? 0 : Math.min(1, decisionTarget / Math.max(Number(mdd), 0.1))}
        tone={mdd != null && mdd > decisionTarget ? "yellow" : "green"}
      />
    </div>
  );
}

function FunnelCard({ d }: { d: Impact }) {
  const bs = d.by_status ?? {};
  const awarded = AWARDED.reduce((n, k) => n + (bs[k] ?? 0), 0);
  const stages =
    d.funnel && d.funnel.length
      ? d.funnel
      : [
          { stage: "Applied", count: d.total },
          { stage: "Grant approved", count: awarded },
          { stage: "Completed", count: d.outcomes?.completed ?? 0 },
          { stage: "Job or raise", count: d.outcomes?.placed_or_raise ?? 0 },
        ];
  const max = Math.max(1, ...stages.map((s) => s.count));
  return (
    <div className="card">
      <span className="kicker">Funnel · join to job</span>
      <div className="imp-funnel">
        {stages.map((s, i) => (
          <div className="frow" key={s.stage}>
            <span className="fl">{s.stage}</span>
            <span className="fbar">
              <span style={{ width: `${Math.max(2, (100 * s.count) / max)}%`, background: FUNNEL_COLORS[i % FUNNEL_COLORS.length] }} />
            </span>
            <b>{fmt(s.count)}</b>
          </div>
        ))}
      </div>
      <div className="imp-chips">
        {Object.entries(d.by_tier ?? {}).map(([k, v]) => (
          <span key={k} className="badge badge-purple">
            {TIER_LABEL[k] ?? k}: {fmt(v)}
          </span>
        ))}
      </div>
    </div>
  );
}

function DollarsCard({ d }: { d: Impact }) {
  const free = d.dollars?.free_program_value ?? 0;
  const pub = d.dollars?.public_aid ?? 0;
  const grant = d.dollars?.grant ?? 0;
  const lev = grant > 0 ? (free + pub) / grant : null;
  const slices: PaySlice[] = [
    { key: "free", label: "Free programs (value, planning assumption)", amount: free, color: "var(--pay-free)" },
    { key: "public", label: "Public aid (WIOA etc.)", amount: pub, color: "var(--pay-public)" },
    { key: "grant", label: "Bridgeline grant, paid to vendors", amount: grant, color: "var(--pay-grant)" },
  ];
  return (
    <div className="card imp-dollars">
      <span className="kicker">Who paid for training · awarded applications</span>
      {lev != null ? (
        <p className="imp-lever">
          Every <span className="x">$1</span> of grant unlocked <span className="x">${lev.toFixed(2)}</span> of free and public
          training.
        </p>
      ) : (
        <p className="imp-lever">No grant dollars awarded yet.</p>
      )}
      <StackBar slices={slices} />
      <div className="imp-legend">
        {slices.map((s) => (
          <span key={s.key}>
            <i style={{ background: s.color }} />
            {s.label} <strong>{compactMoney(s.amount)}</strong>
          </span>
        ))}
        <span>
          <i style={{ background: "var(--pay-resident)" }} />
          Cash to residents <strong>$0</strong>
        </span>
      </div>
      <p className="imp-note">
        Free-program value is a planning assumption: the market cost of a seat that a free provider funds. Grant dollars go straight to
        training providers and vendors. Residents get no cash and no stipends, so the grant is designed not to change their rent.
      </p>
    </div>
  );
}

function PropertyCard({ d }: { d: Impact }) {
  const bp = (d.by_property ?? []).slice(0, 8);
  const max = Math.max(1, ...bp.map((x) => x.residents || 0));
  const langs = Object.entries(d.by_language ?? {}).sort((a, b) => b[1] - a[1]);
  const maxL = Math.max(1, ...langs.map(([, v]) => v));
  return (
    <div className="card">
      <span className="kicker">By property · aggregated</span>
      <div className="imp-bars">
        {bp.length ? (
          bp.map((x) => (
            <SplitBar
              key={x.property}
              label={x.property.replace(/\s*\(demo\)\s*$/i, "")}
              a={x.approved || 0}
              b={Math.max(0, (x.residents || 0) - (x.approved || 0))}
              max={max}
              right={
                <>
                  {fmt(x.approved)} / {fmt(x.residents)}
                </>
              }
            />
          ))
        ) : (
          <p className="muted small">No property data yet.</p>
        )}
      </div>
      <div className="imp-legend">
        <span>
          <i style={{ background: "var(--green-hi)" }} />
          Grant approved
        </span>
        <span>
          <i style={{ background: "#c9d7ff" }} />
          Activated, not yet funded
        </span>
      </div>
      <p className="imp-note">
        Demo properties. Operators see these totals only, never an individual resident. Data stays separate from tenancy records.
      </p>
      {langs.length ? (
        <div className="imp-langs">
          <span className="kicker">Applications by language · Mistral intake</span>
          <div className="imp-bars">
            {langs.map(([k, v]) => (
              <HBar key={k} label={LANG_LABEL[k] ?? k} value={v} max={maxL} color="var(--blue)" right={fmt(v)} />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function EsPanel({ impact, housing }: { impact: Loaded<Impact>; housing: Loaded<Housing> }) {
  const blocks: { title: string; took?: number; q: unknown }[] = [];
  if (impact.data?.query) blocks.push({ title: "Pilot scorecard · index homebase-applications", took: impact.data.took_ms, q: impact.data.query });
  if (housing.data?.query)
    blocks.push({ title: "San Francisco context · index homebase-sf-housing (DataSF)", took: housing.data.took_ms ?? housing.data.ms, q: housing.data.query });
  return (
    <details className="imp-es">
      <summary>
        <span className="badge badge-blue">Elasticsearch</span>
        <span>Powered by Elasticsearch: the actual aggregation queries behind this page</span>
      </summary>
      {blocks.length ? (
        blocks.map((b) => (
          <div key={b.title}>
            <h4>
              {b.title}
              {b.took != null ? <span className="took">{b.took} ms</span> : null}
            </h4>
            <pre>{JSON.stringify(b.q, null, 2)}</pre>
          </div>
        ))
      ) : (
        <p className="small" style={{ margin: "0 0 16px" }}>
          No query returned yet.
        </p>
      )}
    </details>
  );
}

export default function ImpactDashboard() {
  const health = useLive<Health>("/api/health", REFRESH_MS);
  const impact = useLive<Impact>("/api/impact", REFRESH_MS);
  const housing = useLive<Housing>("/api/opendata/housing", 60_000);

  // Briefly highlight KPIs that changed since the last refresh (e.g. a navigator approval).
  const prev = useRef<Record<string, number> | null>(null);
  const [flash, setFlash] = useState<Set<string>>(new Set());
  const [toast, setToast] = useState<string | null>(null);
  useEffect(() => {
    const d = impact.data;
    if (!d) return;
    const bs = d.by_status ?? {};
    const now: Record<string, number> = {
      total: d.total,
      awarded: AWARDED.reduce((n, k) => n + (bs[k] ?? 0), 0),
      completed: d.outcomes?.completed ?? 0,
      placed: d.outcomes?.placed_or_raise ?? 0,
      live: d.live_count ?? 0,
    };
    const before = prev.current;
    prev.current = now;
    if (!before) return;
    const changed = new Set(Object.keys(now).filter((k) => now[k] !== before[k]));
    if (!changed.size) return;
    setFlash(changed);
    if (changed.has("awarded") && now.awarded > before.awarded) setToast("A navigator just approved a grant. Totals updated from Elasticsearch.");
    else if (changed.has("live") && now.live > before.live) setToast("New live application indexed in Elasticsearch.");
    else if (changed.has("placed") && now.placed > before.placed) setToast("A resident just reported a job or raise.");
    const t1 = setTimeout(() => setFlash(new Set()), 2200);
    const t2 = setTimeout(() => setToast(null), 4200);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [impact.data]);

  const d = impact.data;
  const updated = impact.at ? new Date(impact.at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" }) : null;

  return (
    <main className="impact-page">
      <section className="imp-hero">
        <svg className="imp-deco" width="360" height="360" viewBox="0 0 320 320" aria-hidden="true">
          <circle cx="200" cy="120" r="110" fill="none" stroke="#2c3670" strokeWidth="2" strokeDasharray="4 10" />
          <circle cx="200" cy="120" r="60" fill="none" stroke="#2c3670" strokeWidth="2" />
          <path d="M150 40 L125 95 H150 L140 140 L180 75 H155Z" fill="#ffc933" />
          <circle cx="290" cy="200" r="14" fill="#6d4dff" />
          <circle cx="95" cy="200" r="9" fill="#1fb24e" />
        </svg>
        <div className="imp-wrap">
          <span className="kicker imp-kicker">Funder &amp; city view · aggregates only</span>
          <h1>
            Training that pays off, <em>without</em> touching anyone&apos;s rent.
          </h1>
          <p className="imp-lede">
            Live from Elasticsearch. No names and no individual records: operators and funders see counts and dollars only.
          </p>
          <div className="imp-health">
            <HealthPills h={health} />
          </div>
        </div>
      </section>

      <section className="imp-block imp-ctx">
        <div className="imp-wrap">
          <div className="imp-sec-title">
            <span className="kicker">San Francisco context · DataSF open data</span>
          </div>
          <HousingContext s={housing} />
        </div>
      </section>

      <section className="imp-block">
        <div className="imp-wrap">
          <div className="imp-sec-title">
            <h2>Pilot scorecard</h2>
            {d ? (
              <span className="imp-cohort">
                <span className="badge badge-yellow">{fmt(d.simulated_count ?? 0)} simulated pilot cohort (illustrative)</span>
                <span className="badge badge-green">
                  <i className="live-dot" />
                  {fmt(d.live_count ?? 0)} live tonight
                </span>
              </span>
            ) : null}
            {updated ? <span className="muted small imp-updated">Updated {updated} · refreshes every 5 s</span> : null}
          </div>
          {impact.error && impact.data ? (
            <div style={{ marginBottom: 12 }}>
              <ErrorCard error={impact.error} context="Latest refresh failed. Showing the last good numbers." />
            </div>
          ) : null}
          <Scorecard s={impact} flash={flash} />
          <p className="imp-note">
            Counts combine the simulated pilot cohort (illustrative, shown to model the pilot targets) with live applications submitted
            tonight. Every number on this page is an Elasticsearch aggregation.
          </p>
        </div>
      </section>

      {d ? (
        <>
          <section className="imp-block imp-tight">
            <div className="imp-wrap imp-grid2">
              <FunnelCard d={d} />
              <DollarsCard d={d} />
            </div>
          </section>
          <section className="imp-block imp-tight">
            <div className="imp-wrap imp-grid2">
              <PropertyCard d={d} />
              <div className="card">
                <span className="kicker">Illustrative pilot budget</span>
                <BudgetCard b={d.budget} />
              </div>
            </div>
          </section>
        </>
      ) : null}

      <section className="imp-block imp-tight">
        <div className="imp-wrap">
          <EsPanel impact={impact} housing={housing} />
        </div>
      </section>

      <footer className="foot">
        Bridgeline · planning figures are proposals, not benchmarks · benefits treatment is planning guidance, not legal
        advice
      </footer>

      {toast ? (
        <div className="imp-toast" role="status" aria-live="polite">
          {toast}
        </div>
      ) : null}
    </main>
  );
}
