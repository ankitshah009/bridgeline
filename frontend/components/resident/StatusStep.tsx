"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import type { TFn } from "./i18n";
import { JKEYS } from "./PathProgress";
import { STATUS_LABEL, TIER_LABEL, money, relTime, type Any } from "./helpers";

export function statusStep(s?: string): number {
  if (!s) return 4;
  if (s === "approved" || s === "enrolled") return 5;
  if (s === "completed") return 6;
  if (s === "placed") return 7;
  return 4;
}

const APPROVEDISH = ["approved", "enrolled", "completed", "placed"];
const ICONS = ["🏠", "✏️", "🔎", "📨", "💸", "🎓", "🚀"];

export function StatusStep({ t, app, property, onStartOver }: { t: TFn; app: Any; property: Any; onStartOver: () => void }) {
  const a = app || {};
  const s: string = a.status;
  const cur = statusStep(s);
  const approvedish = APPROVEDISH.includes(s);
  const dec = a.decision || {};
  const prof = a.profile || {};
  const pays: Any[] = a.payments || [];
  const tier = TIER_LABEL[a.tier] || a.tier || "";

  const lead = approvedish
    ? t("status_approved")
    : s === "declined"
      ? dec.note || "Not approved this round. You can reapply after talking with your navigator."
      : s === "needs_info"
        ? "Your navigator needs one more thing: " + (dec.note || "they'll text you.")
        : t("status_waiting");

  const fund: ReactNode = approvedish ? (
    <>
      Approved{dec.reviewer ? ` by ${dec.reviewer}` : ""} · {tier} grant {money(a.grant_amount)}
      {dec.note && (<><br /><span className="small">“{dec.note}”</span></>)}
    </>
  ) : s === "needs_info" ? (
    `Needs info: ${dec.note || ""}`
  ) : s === "declined" ? (
    `Not approved${dec.note ? ": " + dec.note : ""}`
  ) : (
    `Navigator reviewing · ${tier} grant ${money(a.grant_amount)} requested`
  );

  const items: ReactNode[] = [
    a.property_name || property?.name || a.property_code || "",
    prof.display?.goal || prof.goal || "",
    <>{a.program_name || ""}{a.provider ? ` · ${a.provider}` : ""}</>,
    `Application ${a.id} · ${relTime(a.created_at)}`,
    fund,
    pays.length ? (
      <>
        Paid to providers:
        <div className="pay-log">
          {pays.map((p, i) => (
            <div key={i}><span>{p.milestone} → {p.paid_to || ""}</span><strong>{money(p.amount)}</strong></div>
          ))}
        </div>
      </>
    ) : (
      "Reminders, attendance, and help if life gets in the way."
    ),
    s === "placed" ? "Hired or earning more. Check-ins at 30, 90 and 180 days." : "Job search support. Check-ins at 30, 90 and 180 days.",
  ];
  const warn = s === "needs_info" || s === "declined";

  return (
    <section className="screen" aria-labelledby="statusTitle">
      <div className="section-head">
        <span className="kicker">{a.id} · {STATUS_LABEL[s] || s}</span>
        <h2 id="statusTitle">{t("status_title")}</h2>
        <p>{lead}</p>
      </div>
      <ol className="journey" aria-live="polite">
        {items.map((it, i) => {
          const cls = i < cur ? "done" : i === cur ? (warn && i === 4 ? "warn" : "cur") : "";
          return (
            <li className={cls} key={i}>
              <div className="diamond">
                <span aria-hidden="true">
                  {i < cur ? (
                    <svg width="22" height="22" viewBox="0 0 22 22">
                      <path d="M4 11l5 5 9-10" stroke="#fff" strokeWidth="3.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  ) : (
                    ICONS[i]
                  )}
                </span>
              </div>
              <div className="jcard">
                <div className="jt">{t(JKEYS[i])}</div>
                <div className="jd">{it}</div>
              </div>
            </li>
          );
        })}
      </ol>
      <div className="row" style={{ marginTop: 18 }}>
        <Link className="small reset-link" href="/?new=1" onClick={(e) => { e.preventDefault(); onStartOver(); }}>{t("start_over")}</Link>
      </div>
    </section>
  );
}
