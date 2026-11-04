"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import {
  ErrorCard,
  HOUSING,
  PAYER,
  PayBar,
  PayLegend,
  STATUS_LABEL,
  TIER_LABEL,
  langName,
  money,
  relTime,
} from "./shared";
import "./navigator.css";

/* eslint-disable @typescript-eslint/no-explicit-any */
type App = Record<string, any>;
type Filter = "live" | "sim" | "all";

const PENDING = ["submitted", "in_review", "needs_info"];
const APPROVEDISH = ["approved", "enrolled", "completed", "placed"];
const MILESTONES = ["enrolled", "completed", "placed"] as const;
const MS_LABEL: Record<string, string> = { enrolled: "Enrolled", completed: "Completed", placed: "Placed / raise" };
const MS_STATUS_IDX: Record<string, number> = { approved: 0, enrolled: 1, completed: 2, placed: 3 };

type CheckItem = { key: string; label: string; detail: string; cite?: string; warn?: boolean; group?: string };

function checklist(a: App): CheckItem[] {
  const b = a.benefits ?? {};
  const items: CheckItem[] = [
    { key: "residence", label: "Residence confirmed by operator", detail: a.property_name || a.property_code || "" },
    { key: "waterfall", label: "Free and public sources checked first", detail: "Grant covers only the remainder" },
    { key: "vendors", label: "All payments go to providers or vendors", detail: "No cash and no stipends to the resident" },
    {
      key: "housing",
      label: `Housing type: ${HOUSING[a.housing_type] ?? a.housing_type ?? "unknown"}`,
      detail: "Operator compliance guidance on file for this program type",
    },
  ];
  // Free help to confirm before the grant pays (free child care, Clipper START, device programs).
  const firsts: any[] = Array.isArray(a.waterfall?.checks_first) ? a.waterfall.checks_first : [];
  firsts.forEach((c: any, i: number) =>
    items.push({
      key: `cf${c?.resource_id ?? i}`,
      label: String(c?.program ?? c?.resource_id ?? "Free resource"),
      detail: String(c?.note ?? ""),
      group: "Check first (free help)",
    }),
  );
  (b.items ?? []).forEach((it: any, i: number) =>
    items.push({ key: `b${i}`, label: String(it.line ?? ""), detail: String(it.treatment ?? ""), cite: it.cite, warn: !it.ok }),
  );
  return items;
}

export default function NavigatorConsole() {
  const [apps, setApps] = useState<App[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [filter, setFilter] = useState<Filter>("live");
  const [selected, setSelected] = useState<string | null>(null);
  const [checks, setChecks] = useState<Record<string, Record<string, boolean>>>({});
  const [drafts, setDrafts] = useState<Record<string, { note: string; reviewer: string }>>({});
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<{ err: unknown; ctx: string } | null>(null);
  const [flashId, setFlashId] = useState<string | null>(null);
  const [userPickedTab, setUserPickedTab] = useState(false);
  const knownLive = useRef<Set<string> | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await api<{ applications: App[] }>("/api/applications");
      const list = r?.applications ?? [];
      // Flash newly arrived live applications so the room sees them land.
      const liveIds = new Set(list.filter((a) => !a.simulated).map((a) => String(a.id)));
      if (knownLive.current) {
        const fresh = [...liveIds].find((id) => !knownLive.current!.has(id));
        if (fresh) {
          setFlashId(fresh);
          setFilter("live");
          setSelected(fresh);
        }
      }
      knownLive.current = liveIds;
      setApps(list);
      setLoadError(null);
      setLoaded(true);
    } catch (err) {
      setLoadError(err);
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(() => {
      if (!document.hidden) load();
    }, 4000);
    return () => clearInterval(t);
  }, [load]);

  // With no live applications yet, open on "All" unless the user picked a tab.
  const hasLive = apps.some((a) => !a.simulated);
  const view: Filter = !userPickedTab && !hasLive && filter === "live" ? "all" : filter;

  const filtered = useMemo(
    () => apps.filter((a) => (view === "all" ? true : view === "sim" ? a.simulated : !a.simulated)),
    [apps, view],
  );

  useEffect(() => {
    if (!flashId) return;
    const t = setTimeout(() => setFlashId(null), 1400);
    return () => clearTimeout(t);
  }, [flashId]);

  const selectedId = selected ?? (filtered[0] ? String(filtered[0].id) : null);
  const current = apps.find((a) => String(a.id) === selectedId) ?? null;

  const counts = useMemo(() => {
    const live = apps.filter((a) => !a.simulated).length;
    const waiting = apps.filter((a) => a.status === "submitted" || a.status === "in_review").length;
    const high = apps.filter((a) => a.risk === "high" && !["declined", "placed"].includes(a.status)).length;
    return [
      { label: "Live", value: live, hot: live > 0 },
      { label: "Awaiting decision", value: waiting },
      { label: "High risk", value: high },
      { label: "Total", value: apps.length },
    ];
  }, [apps]);

  const replace = (a: App) => {
    setApps((prev) => {
      const i = prev.findIndex((x) => x.id === a.id);
      if (i < 0) return [a, ...prev];
      const next = prev.slice();
      next[i] = a;
      return next;
    });
  };

  const decide = async (a: App, action: "approve" | "request_info" | "decline") => {
    const d = drafts[a.id] ?? { note: "", reviewer: "Navigator · demo" };
    setBusy(true);
    setActionError(null);
    try {
      const r = await api<{ application: App }>(`/api/applications/${encodeURIComponent(a.id)}/decision`, {
        action,
        reviewer: d.reviewer.trim() || "Navigator · demo",
        note: d.note.trim(),
      });
      replace(r.application);
      setFlashId(String(a.id));
    } catch (err) {
      setActionError({ err, ctx: "Decision not saved" });
    } finally {
      setBusy(false);
    }
  };

  const milestone = async (a: App, m: string) => {
    setBusy(true);
    setActionError(null);
    try {
      const r = await api<{ application: App }>(`/api/applications/${encodeURIComponent(a.id)}/milestone`, {
        milestone: m,
      });
      replace(r.application);
      setFlashId(String(a.id));
    } catch (err) {
      setActionError({ err, ctx: "Milestone not saved" });
    } finally {
      setBusy(false);
    }
  };

  const pickTab = (f: Filter) => {
    setUserPickedTab(true);
    setFilter(f);
    const first = apps.find((a) => (f === "all" ? true : f === "sim" ? a.simulated : !a.simulated));
    setSelected(first ? String(first.id) : null);
    setActionError(null);
  };

  return (
    <div className="nav-console">
      <section className="head">
        <div className="head-inner">
          <div>
            <span className="kicker">Career navigator console</span>
            <h1>Caseload</h1>
            <p>AI drafts. People decide. Every award passes a benefits check first.</p>
          </div>
          <div className="counts">
            {counts.map((c) => (
              <div key={c.label} className={`count${c.hot ? " hot" : ""}`}>
                <b>{c.value}</b>
                <span>{c.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <main className="layout">
        <section aria-label="Applications">
          <div className="tabs" role="tablist">
            {(
              [
                ["live", "Live"],
                ["sim", "Simulated pilot cohort"],
                ["all", "All"],
              ] as const
            ).map(([f, label]) => (
              <button
                key={f}
                type="button"
                role="tab"
                className="tab"
                aria-selected={view === f}
                onClick={() => pickTab(f)}
              >
                {label}
              </button>
            ))}
          </div>
          {view !== "live" && (
            <p className="sim-note">Simulated pilot cohort (illustrative) is labelled; it is not real residents.</p>
          )}
          <div className="list" aria-live="polite">
            {loadError ? (
              <ErrorCard error={loadError} context="Couldn't load the caseload" />
            ) : !loaded ? (
              <div className="skeleton" />
            ) : filtered.length === 0 ? (
              <div className="card-flat empty">
                {view === "live" ? "No live applications yet. Submit one from the resident app." : "Nothing here."}
              </div>
            ) : (
              filtered.map((a) => {
                const fresh = !a.simulated && (a.status === "submitted" || a.status === "in_review");
                const meta = [
                  a.property_name || a.property_code,
                  langName(a.language),
                  `${TIER_LABEL[a.tier] ?? a.tier ?? ""} ${money(a.grant_amount)}`.trim(),
                  relTime(a.created_at),
                ]
                  .filter(Boolean)
                  .join(" · ");
                return (
                  <button
                    key={a.id}
                    type="button"
                    className={`case${a.simulated ? "" : " live"}${String(a.id) === selectedId ? " sel" : ""}${
                      flashId === String(a.id) ? " flash" : ""
                    }`}
                    onClick={() => {
                      setSelected(String(a.id));
                      setActionError(null);
                    }}
                  >
                    <div className="top">
                      {fresh && <span className="new-dot" aria-label="New" />}
                      <span className="id">{a.id}</span>
                      <span className={`status st-${a.status}`}>{STATUS_LABEL[a.status] ?? a.status}</span>
                      {a.risk && <span className={`badge risk-${a.risk}`}>{a.risk} risk</span>}
                      {a.simulated && <span className="badge">Simulated</span>}
                    </div>
                    <div className="prog">{a.program_name || a.program_id || ""}</div>
                    <div className="meta">{meta}</div>
                  </button>
                );
              })
            )}
          </div>
        </section>

        <section className="detail" aria-live="polite">
          {current ? (
            <Detail
              a={current}
              flash={flashId === String(current.id)}
              checks={checks[current.id] ?? {}}
              setCheck={(k, v) =>
                setChecks((prev) => ({ ...prev, [current.id]: { ...(prev[current.id] ?? {}), [k]: v } }))
              }
              draft={drafts[current.id] ?? { note: "", reviewer: "Navigator · demo" }}
              setDraft={(d) => setDrafts((prev) => ({ ...prev, [current.id]: d }))}
              busy={busy}
              actionError={actionError}
              onDecide={(action) => decide(current, action)}
              onMilestone={(m) => milestone(current, m)}
            />
          ) : (
            <div className="card empty">Select an application to review.</div>
          )}
        </section>
      </main>
    </div>
  );
}

function Detail({
  a,
  flash,
  checks,
  setCheck,
  draft,
  setDraft,
  busy,
  actionError,
  onDecide,
  onMilestone,
}: {
  a: App;
  flash: boolean;
  checks: Record<string, boolean>;
  setCheck: (k: string, v: boolean) => void;
  draft: { note: string; reviewer: string };
  setDraft: (d: { note: string; reviewer: string }) => void;
  busy: boolean;
  actionError: { err: unknown; ctx: string } | null;
  onDecide: (action: "approve" | "request_info" | "decline") => void;
  onMilestone: (m: string) => void;
}) {
  const p = a.profile ?? {};
  const w = a.waterfall ?? {};
  // Simulated cohort records carry only top-level amounts; derive the bar from them.
  const tot = w.totals ?? {
    free_program: Number(a.free_program_value) || 0,
    public_aid: Number(a.public_aid) || 0,
    grant: Number(a.grant_amount) || 0,
    resident: 0,
  };
  const plan = a.plan ?? {};
  const b = a.benefits ?? {};
  const items = checklist(a);
  const allChecked = items.every((i) => checks[i.key]);
  const pending = PENDING.includes(a.status);
  const approvedish = APPROVEDISH.includes(a.status);
  const statusIdx = MS_STATUS_IDX[a.status] ?? -1;
  const pays: App[] = a.payments ?? [];
  const paidTotal = pays.reduce((s, x) => s + (Number(x.amount) || 0), 0);
  const d = a.decision ?? {};

  return (
    <>
      <div className={`card${flash ? " flash" : ""}`}>
        <div className="row">
          <span className="kicker">{a.id}</span>
          <span className={`status st-${a.status}`}>{STATUS_LABEL[a.status] ?? a.status}</span>
          {a.simulated ? (
            <span className="badge">Simulated pilot cohort (illustrative)</span>
          ) : (
            <span className="badge badge-green">Live</span>
          )}
          <span className="spacer" />
          <span className="small muted">{relTime(a.created_at)}</span>
        </div>
        <h2 style={{ marginTop: 10 }}>{a.program_name ?? ""}</h2>
        <p className="muted">{a.provider ?? ""}</p>
        <dl className="kv">
          <dt>Property</dt>
          <dd>
            {a.property_name || a.property_code || ""} · {HOUSING[a.housing_type] ?? a.housing_type ?? ""}
          </dd>
          <dt>Language</dt>
          <dd>{langName(a.language)}</dd>
          <dt>Goal</dt>
          <dd>{p.goal ?? ""}</dd>
          <dt>Availability</dt>
          <dd>
            {[p.availability, p.hours_per_week_available ? `${p.hours_per_week_available} h/wk` : ""]
              .filter(Boolean)
              .join(" · ")}
          </dd>
          <dt>Works now</dt>
          <dd>{p.current_work || "—"}</dd>
          <dt>Child care</dt>
          <dd>{p.needs_childcare ? `Needed${p.children ? ` · ${p.children} children` : ""}` : "Not needed"}</dd>
          <dt>Computer</dt>
          <dd>{p.has_computer ? "Has one" : "Needs one"}</dd>
          {a.distance_km != null && (
            <>
              <dt>Distance</dt>
              <dd>{(Number(a.distance_km) * 0.621).toFixed(1)} mi from home</dd>
            </>
          )}
          {p.summary && (
            <>
              <dt>Summary</dt>
              <dd>{p.summary}</dd>
            </>
          )}
        </dl>
        {a.risk && (
          <div className="row" style={{ marginTop: 12 }}>
            <span className={`badge risk-${a.risk}`}>{a.risk} risk</span>
            {(a.risk_reasons ?? []).map((r: string, i: number) => (
              <span key={i} className="badge">
                {r}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="dgrid">
        <div className="ai-draft">
          <span className="badge badge-ai">✦ AI draft · staff review required</span>
          {plan.headline && (
            <h3 style={{ marginTop: 10 }}>{plan.headline}</h3>
          )}
          {plan.navigator_note ? (
            <p style={{ marginTop: 10 }}>{plan.navigator_note}</p>
          ) : (
            <p className="muted" style={{ marginTop: 10 }}>
              No draft note.
            </p>
          )}
          {plan.steps?.length > 0 && (
            <ol>
              {plan.steps.map((s: string, i: number) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
          )}
          {plan.risks?.length > 0 && (
            <p className="small" style={{ marginTop: 10 }}>
              <strong>Watch for:</strong> {plan.risks.join("; ")}
            </p>
          )}
          <p className="tiny muted" style={{ marginTop: 10 }}>
            Mistral drafted this from the resident&apos;s own words. It does not decide eligibility or awards.
          </p>
        </div>

        <div className="card">
          <div className="row">
            <span className="kicker">Funding waterfall</span>
            <span className="spacer" />
            {w.tier && (
              <span className="badge badge-purple">
                {TIER_LABEL[w.tier] ?? w.tier} · cap {money(w.tier_cap)}
              </span>
            )}
            {w.within_cap === false && <span className="badge badge-orange">Over cap</span>}
          </div>
          <div style={{ marginTop: 10 }}>
            <PayBar totals={tot} />
            <PayLegend totals={tot} />
          </div>
          <table>
            <thead>
              <tr>
                <th>Item</th>
                <th>Payer</th>
                <th>Paid to</th>
                <th className="num">Amount</th>
              </tr>
            </thead>
            <tbody>
              {(w.lines ?? []).map((l: any, i: number) => {
                const payer = PAYER[l.payer as keyof typeof PAYER];
                return (
                  <tr key={i}>
                    <td>{l.item}</td>
                    <td>
                      <span className={`badge ${payer?.badge ?? ""}`}>{l.payer_label || payer?.label || l.payer}</span>
                    </td>
                    <td>{l.paid_to ?? ""}</td>
                    <td className="num">{money(l.amount)}</td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={3}>Bridgeline grant</td>
                <td className="num">{money(tot.grant)}</td>
              </tr>
              <tr>
                <td colSpan={3}>Resident pays</td>
                <td className="num">{money(tot.resident)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <div className="dgrid">
        <div className="card">
          <div className="row">
            <span className="kicker">Benefits check</span>
            <span className="spacer" />
            <span className={`badge ${b.status === "protected" ? "badge-green" : "badge-yellow"}`}>
              {b.status === "protected" ? "Rent-safe design" : "Needs review"}
            </span>
          </div>
          {b.summary && (
            <p className="small" style={{ margin: "8px 0 4px" }}>
              {b.summary}
            </p>
          )}
          <div className="checks">
            {items.map((i, idx) => (
              <div key={i.key}>
                {i.group && items[idx - 1]?.group !== i.group && (
                  <div className="kicker" style={{ margin: "12px 0 2px", color: "#0d6b2d" }}>
                    {i.group}
                  </div>
                )}
              <label className="check">
                <input
                  type="checkbox"
                  checked={!!checks[i.key]}
                  disabled={!pending}
                  onChange={(e) => setCheck(i.key, e.target.checked)}
                />
                <span>
                  <strong>
                    {i.label}
                    {i.warn ? " ⚠️" : ""}
                  </strong>
                  <span className="cite">{i.detail}</span>
                  {i.cite && <span className="cite">{i.cite}</span>}
                </span>
              </label>
              </div>
            ))}
          </div>
          <p className="tiny muted" style={{ marginTop: 8 }}>
            24 CFR 5.609 planning guidance, not legal advice.
          </p>
        </div>

        <div className="card decide">
          <span className="kicker">Decision</span>
          {pending ? (
            <div className="stack" style={{ marginTop: 10 }}>
              <label className="small" style={{ fontWeight: 700 }}>
                Reviewer
                <input value={draft.reviewer} onChange={(e) => setDraft({ ...draft, reviewer: e.target.value })} />
              </label>
              <label className="small" style={{ fontWeight: 700 }}>
                Note to resident
                <textarea
                  placeholder="e.g. Approved. Child care paid to the provider you chose."
                  value={draft.note}
                  onChange={(e) => setDraft({ ...draft, note: e.target.value })}
                />
              </label>
              <div className="row">
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={!allChecked || busy}
                  onClick={() => onDecide("approve")}
                >
                  Approve {money(a.grant_amount)}
                </button>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  disabled={busy}
                  onClick={() => onDecide("request_info")}
                >
                  Request info
                </button>
                <button type="button" className="btn btn-danger btn-sm" disabled={busy} onClick={() => onDecide("decline")}>
                  Decline
                </button>
              </div>
              <p className="small muted">
                {allChecked ? "Benefits check complete." : "Complete the benefits check to approve."}
              </p>
            </div>
          ) : (
            <>
              <p style={{ marginTop: 10 }}>
                <strong>{STATUS_LABEL[a.status] ?? a.status}</strong>
                {d.reviewer ? ` by ${d.reviewer}` : ""}
                {d.at ? ` · ${relTime(d.at)}` : ""}
                {a.decision_days != null ? ` · ${Number(a.decision_days).toFixed(1)} days to decision` : ""}
              </p>
              {d.note && (
                <p className="small muted" style={{ marginTop: 4 }}>
                  “{d.note}”
                </p>
              )}
              {approvedish && (
                <>
                  <div className="kicker" style={{ marginTop: 14 }}>
                    Milestones · tuition 50/30/20
                  </div>
                  <div className="ms-row">
                    {MILESTONES.map((m, i) => (
                      <button
                        key={m}
                        type="button"
                        className={`btn btn-sm ${i === statusIdx ? "btn-dark" : "btn-ghost"}`}
                        disabled={i !== statusIdx || busy}
                        onClick={() => onMilestone(m)}
                      >
                        {i < statusIdx ? "✓ " : ""}
                        {MS_LABEL[m]}
                      </button>
                    ))}
                  </div>
                </>
              )}
              {pays.length > 0 && (
                <table style={{ marginTop: 12 }}>
                  <thead>
                    <tr>
                      <th>Milestone</th>
                      <th>Paid to</th>
                      <th className="num">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pays.map((x, i) => (
                      <tr key={i}>
                        <td>
                          {x.milestone}
                          <div className="tiny muted">{relTime(x.at)}</div>
                        </td>
                        <td>{x.paid_to ?? ""}</td>
                        <td className="num">{money(x.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colSpan={2}>Paid to providers and vendors · $0 cash to resident</td>
                      <td className="num">{money(paidTotal)}</td>
                    </tr>
                  </tfoot>
                </table>
              )}
            </>
          )}
          {actionError && (
            <div style={{ marginTop: 10 }}>
              <ErrorCard error={actionError.err} context={actionError.ctx} />
            </div>
          )}
        </div>
      </div>
    </>
  );
}
