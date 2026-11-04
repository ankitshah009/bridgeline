"use client";

import Link from "next/link";
import { usd } from "@/lib/api";
import { LiveBadge } from "./LiveCheck";
import { Item, Kind, LANG_LABEL, LEVEL_LABEL, SCHEDULE_LABEL, itemKind, itemTitle, programCost } from "./types";

type OpenFn = (item: Item, kind: Kind) => void;

export function statusTone(status?: string): string {
  const s = (status ?? "").toLowerCase();
  if (s.startsWith("available")) return "green";
  if (s.startsWith("confirm")) return "yellow";
  if (s.startsWith("closed")) return "grey";
  if (s.startsWith("not yet")) return "blue";
  return "grey";
}

const TIER_STYLE: Record<string, { tone: string; art: "spark" | "shield" | "rocket" }> = {
  starter: { tone: "yellow", art: "spark" },
  stay_in_training: { tone: "purple", art: "shield" },
  career: { tone: "green", art: "rocket" },
};

function tierKey(item: Item): string {
  const id = String(item.id ?? item.key ?? item.label ?? "").toLowerCase().replace(/[^a-z]+/g, "_");
  if (id.includes("starter")) return "starter";
  if (id.includes("stay")) return "stay_in_training";
  if (id.includes("career")) return "career";
  return "starter";
}

export function TierArt({ kind }: { kind: "spark" | "shield" | "rocket" }) {
  if (kind === "spark")
    return (
      <svg viewBox="0 0 120 80" className="dir-art" aria-hidden="true">
        <circle cx="30" cy="48" r="20" fill="#fff4cf" stroke="#15182c" strokeWidth="2.5" />
        <path d="M33 30 22 50h10l-3 16 13-22H32z" fill="#ffc933" stroke="#15182c" strokeWidth="2.5" strokeLinejoin="round" />
        <rect x="62" y="34" width="44" height="28" rx="4" fill="#fff" stroke="#15182c" strokeWidth="2.5" />
        <path d="M56 66h56" stroke="#15182c" strokeWidth="2.5" strokeLinecap="round" />
        <path d="M70 52l8-8 6 5 12-11" fill="none" stroke="#2f6bff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  if (kind === "shield")
    return (
      <svg viewBox="0 0 120 80" className="dir-art" aria-hidden="true">
        <path d="M60 8 86 18v20c0 18-12 30-26 36C46 68 34 56 34 38V18z" fill="#ece7ff" stroke="#15182c" strokeWidth="2.5" strokeLinejoin="round" />
        <path d="M48 40l8 8 16-17" fill="none" stroke="#6d4dff" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="16" cy="58" r="8" fill="#1fb24e" stroke="#15182c" strokeWidth="2.5" />
        <circle cx="104" cy="22" r="6" fill="#ff7a2f" stroke="#15182c" strokeWidth="2.5" />
        <path d="M10 70h22M92 66h20" stroke="#15182c" strokeWidth="2.5" strokeLinecap="round" strokeDasharray="2 6" />
      </svg>
    );
  return (
    <svg viewBox="0 0 120 80" className="dir-art" aria-hidden="true">
      <path d="M14 68 L46 40 L66 54 L106 14" fill="none" stroke="#1fb24e" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="46" cy="40" r="6" fill="#fff" stroke="#15182c" strokeWidth="2.5" />
      <circle cx="66" cy="54" r="6" fill="#fff" stroke="#15182c" strokeWidth="2.5" />
      <circle cx="106" cy="14" r="9" fill="#ffc933" stroke="#15182c" strokeWidth="2.5" />
      <path d="M14 74h96" stroke="#15182c" strokeWidth="2.5" strokeLinecap="round" />
      <rect x="18" y="22" width="16" height="16" rx="3" fill="#2f6bff" stroke="#15182c" strokeWidth="2.5" transform="rotate(-12 26 30)" />
    </svg>
  );
}

function OpenButton({ item, kind, onOpen }: { item: Item; kind: Kind; onOpen: OpenFn }) {
  return (
    <button type="button" className="dir-open" onClick={() => onOpen(item, kind)}>
      <span className="dir-title">{itemTitle(item)}</span>
    </button>
  );
}

export function TierCard({ item, onOpen }: { item: Item; onOpen: OpenFn }) {
  const key = tierKey(item);
  const style = TIER_STYLE[key] ?? TIER_STYLE.starter;
  const covers: string[] = Array.isArray(item.covers)
    ? item.covers
    : String(item.covers ?? "")
        .replace(/\.$/, "")
        .split(/,\s*(?:and\s+)?|\s+and\s+/)
        .filter(Boolean);
  return (
    <article className={`dir-card dir-tier tone-${style.tone}`}>
      <TierArt kind={style.art} />
      <div className="kicker">Grant tier</div>
      <OpenButton item={item} kind="tier" onOpen={onOpen} />
      <div className="dir-cap">
        <span className="dir-cap-label">up to</span> {usd(Number(item.cap) || 0)}
      </div>
      {covers.length ? (
        <ul className="dir-covers">
          {covers.slice(0, 4).map((c) => (
            <li key={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</li>
          ))}
        </ul>
      ) : null}
      {item.requires ? (
        <p className="dir-requires small">
          <strong>Needs:</strong> {item.requires}
        </p>
      ) : null}
      <p className="dir-note small muted">Paid straight to providers and vendors. Never cash.</p>
      <div className="dir-cta">
        <Link href="/?new=1" className="btn btn-primary btn-sm">
          Start a plan
        </Link>
      </div>
    </article>
  );
}

export function ProgramCard({ item, onOpen }: { item: Item; onOpen: OpenFn }) {
  const cost = programCost(item);
  const langs: string[] = Array.isArray(item.languages) ? item.languages : [];
  const level = String(item.level ?? "");
  const schedule = SCHEDULE_LABEL[String(item.schedule ?? "")] ?? item.schedule;
  const span = [
    item.hours_per_week ? `${item.hours_per_week} h/week` : null,
    item.weeks ? `${item.weeks} weeks` : null,
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <article className={`dir-card dir-program lvl-${level || "entry"}`}>
      <div className="dir-row">
        {level ? <span className={`badge dir-lvl lvl-badge-${level}`}>{LEVEL_LABEL[level] ?? level}</span> : null}
        {item.offered_now === false ? <span className="badge badge-off">Not running this term</span> : null}
        {item.illustrative ? <span className="badge badge-ink">Illustrative</span> : null}
        {item._score != null && item.kind ? <span className="badge badge-blue">match</span> : null}
      </div>
      <LiveBadge check={item.live_check} />
      <OpenButton item={item} kind="program" onOpen={onOpen} />
      {item.provider ? <div className="dir-provider">{item.provider}</div> : null}
      <div className="dir-chips">
        {schedule ? <span className="dir-chip">{schedule}</span> : null}
        {span ? <span className="dir-chip">{span}</span> : null}
        {item.format ? <span className="dir-chip">{item.format}</span> : null}
      </div>
      <div className="dir-row">
        {item.free_to_resident ? (
          <span className="badge badge-green">Free tuition</span>
        ) : cost > 0 ? (
          <span className="badge badge-orange">~{usd(cost)} before aid</span>
        ) : (
          <span className="badge badge-green">No cost listed</span>
        )}
        {item.wioa_etpl ? <span className="badge badge-blue">State-listed (WIOA)</span> : null}
        {item.stipend ? <span className="badge badge-yellow">Stipend: benefits check</span> : null}
      </div>
      {langs.length ? (
        <div className="dir-langs small muted">{langs.map((l) => LANG_LABEL[l] ?? l.toUpperCase()).join(" · ")}</div>
      ) : null}
      {item._why ? <p className="dir-why small">{item._why}</p> : null}
      {item.offered_now === false && item.availability_note ? (
        <p className="not-running-note">{item.availability_note}</p>
      ) : item.verify_note ? (
        <p className="dir-verify">{item.verify_note}</p>
      ) : null}
      <div className="dir-cta">
        <Link href="/?new=1" className="btn btn-primary btn-sm">
          Plan with this
        </Link>
      </div>
    </article>
  );
}

export function ResourceCard({ item, onOpen }: { item: Item; onOpen: OpenFn }) {
  const tone = statusTone(item.status);
  return (
    <article className={`dir-card dir-resource st-tone-${tone}`}>
      <div className="dir-row">
        <span className={`badge dir-status dir-status-${tone}`}>{item.status ?? "Confirm"}</span>
        {item.housing_only ? <span className="badge badge-purple">For affordable-housing residents</span> : null}
      </div>
      <LiveBadge check={item.live_check} />
      {item.category ? <div className="kicker dir-cat">{item.category}</div> : null}
      <OpenButton item={item} kind="resource" onOpen={onOpen} />
      {item.provides ? <p className="dir-provides">{item.provides}</p> : null}
      {item.who ? (
        <p className="small dir-who">
          <strong>Who:</strong> {item.who}
        </p>
      ) : null}
      {item.status_note ? <p className="dir-verify">{item.status_note}</p> : null}
      {item._why ? <p className="dir-why small">{item._why}</p> : null}
      <div className="dir-cta">
        {item.source_url ? (
          <a className="btn btn-ghost btn-sm" href={item.source_url} target="_blank" rel="noopener noreferrer">
            Source ↗
          </a>
        ) : (
          <span className="small muted">Source: confirm directly</span>
        )}
      </div>
    </article>
  );
}

export function DirectoryCard({ item, fallback, onOpen }: { item: Item; fallback: Kind; onOpen: OpenFn }) {
  const kind = itemKind(item, fallback);
  if (kind === "tier") return <TierCard item={item} onOpen={onOpen} />;
  if (kind === "resource") return <ResourceCard item={item} onOpen={onOpen} />;
  return <ProgramCard item={item} onOpen={onOpen} />;
}
