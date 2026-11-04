"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { usd } from "@/lib/api";
import { statusTone, TierArt } from "./Cards";
import { LiveBadge, liveCheckDetail } from "./LiveCheck";
import { Item, Kind, LANG_LABEL, LEVEL_LABEL, SCHEDULE_LABEL, itemTitle, programCost } from "./types";

type Row = [string, React.ReactNode];

function yesNo(v: unknown) {
  return v ? "Yes" : "No";
}

function liveRows(item: Item): Row[] {
  const c = item.live_check;
  if (!c) return [];
  return [
    ["Live check", <LiveBadge key="lc" check={c} />],
    ["Live check notes", liveCheckDetail(c) || null],
  ];
}

function rowsFor(item: Item, kind: Kind): Row[] {
  if (kind === "tier") {
    return [
      ["Grant cap", usd(Number(item.cap) || 0)],
      ["Covers", item.covers],
      ["Requires", item.requires],
      ["Paid to", "Training providers and approved vendors, never cash to residents"],
      ["Tuition payments", "50% at enrollment · 30% at completion · 20% at verified job or raise"],
      ["Decision time", "Within 10 business days of a complete application"],
    ];
  }
  if (kind === "resource") {
    return [
      ["Status", <span key="s" className={`badge dir-status dir-status-${statusTone(item.status)}`}>{item.status}</span>],
      ["Category", item.category],
      ["What it provides", item.provides],
      ["Who qualifies", item.who],
      ["Status notes", item.status_note],
      ["Only for affordable housing", yesNo(item.housing_only)],
      ["Topics", Array.isArray(item.tags) ? item.tags.join(", ") : null],
      ["As of", item.as_of],
      ...liveRows(item),
    ];
  }
  const cost = programCost(item);
  return [
    ["Provider", item.provider],
    ["Level", LEVEL_LABEL[String(item.level)] ?? item.level],
    ["Career tracks", Array.isArray(item.career_tracks) ? item.career_tracks.join(", ") : null],
    ["Schedule", SCHEDULE_LABEL[String(item.schedule)] ?? item.schedule],
    ["Time", [item.hours_per_week && `${item.hours_per_week} h/week`, item.weeks && `${item.weeks} weeks`].filter(Boolean).join(" · ")],
    ["Format", [item.format, item.neighborhood].filter(Boolean).join(" · ")],
    ["Cost to resident", item.free_to_resident ? "Free tuition" : cost > 0 ? `~${usd(cost)} before aid` : "No cost listed"],
    ["Tuition / materials / exams", `${usd(Number(item.tuition_usd) || 0)} / ${usd(Number(item.materials_usd) || 0)} / ${usd(Number(item.exam_fees_usd) || 0)}`],
    ["Languages", Array.isArray(item.languages) ? item.languages.map((l: string) => LANG_LABEL[l] ?? l).join(", ") : null],
    ["Requirements", Array.isArray(item.requirements) ? item.requirements.join(" · ") : item.requirements],
    ["State-listed provider (WIOA)", yesNo(item.wioa_etpl)],
    ["Stipend", item.stipend ? "Yes (benefits check needed)" : "No"],
    ["Income-share or required loan", item.isa_or_required_loan ? "Yes (not grant-eligible)" : "No"],
    ["Published outcomes", item.published_outcomes == null ? "Not published; ask the provider" : JSON.stringify(item.published_outcomes)],
    ["Running this term", item.offered_now === false ? "No" : item.offered_now === "unknown" ? "Unknown; confirm with provider" : "Yes"],
    ["Availability", item.offered_now === false ? item.availability_note : null],
    ["Verify", item.verify_note],
    ...liveRows(item),
  ];
}

export function DetailDialog({ item, kind, onClose }: { item: Item | null; kind: Kind; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (item && !d.open) d.showModal();
    if (!item && d.open) d.close();
  }, [item]);

  const link = item ? (kind === "resource" ? item.source_url : kind === "program" ? item.url : null) : null;

  return (
    <dialog
      ref={ref}
      className="dir-dialog"
      aria-labelledby="dir-dialog-title"
      onClose={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      {item ? (
        <div className="dir-dialog-body">
          <div className="dir-dialog-head">
            <div>
              <div className="kicker">{kind === "tier" ? "Grant tier" : kind === "resource" ? "Free help" : "Training program"}</div>
              <h2 id="dir-dialog-title">{itemTitle(item)}</h2>
            </div>
            <button type="button" className="btn btn-ghost btn-icon dir-close" aria-label="Close" onClick={onClose}>
              ✕
            </button>
          </div>
          {kind === "tier" ? <TierArt kind={String(item.id ?? "").includes("career") ? "rocket" : String(item.id ?? "").includes("stay") ? "shield" : "spark"} /> : null}
          {item.description ? <p className="dir-desc">{item.description}</p> : null}
          <dl className="dir-dl">
            {rowsFor(item, kind)
              .filter(([, v]) => v !== null && v !== undefined && v !== "")
              .map(([k, v]) => (
                <div key={k} className="dir-dl-row">
                  <dt>{k}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
          </dl>
          <div className="dir-dialog-actions">
            {kind !== "resource" ? (
              <Link href="/?new=1" className="btn btn-primary">
                {kind === "tier" ? "Start a plan" : "Plan with this"}
              </Link>
            ) : null}
            {link ? (
              <a className="btn btn-ghost" href={link} target="_blank" rel="noopener noreferrer">
                {kind === "resource" ? "Source ↗" : "Provider site ↗"}
              </a>
            ) : null}
          </div>
          <p className="small muted dir-disclaimer">
            Listings come from public sources and change often. Confirm dates, cost and eligibility with each program; ask
            your housing provider how any grant may affect rent.
          </p>
        </div>
      ) : null}
    </dialog>
  );
}
