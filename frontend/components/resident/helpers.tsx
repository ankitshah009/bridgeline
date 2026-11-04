"use client";

import { Fragment, type ReactNode } from "react";
import { ApiError, api } from "@/lib/api";

/* eslint-disable @typescript-eslint/no-explicit-any */
export type Any = any;

export const STATUS_LABEL: Record<string, string> = {
  submitted: "Submitted", in_review: "In review", approved: "Approved", needs_info: "Needs info",
  declined: "Declined", enrolled: "Enrolled", completed: "Completed", placed: "Placed",
};
export const TIER_LABEL: Record<string, string> = { starter: "Starter", stay_in_training: "Stay-in-Training", career: "Career" };
export const PAYER: Record<string, { label: string; cls: string; badge: string }> = {
  free_program: { label: "Free program", cls: "free", badge: "badge-green" },
  public_aid: { label: "Public aid", cls: "public", badge: "badge-blue" },
  grant: { label: "Bridgeline grant", cls: "grant", badge: "badge-purple" },
  resident: { label: "You pay", cls: "resident", badge: "badge-orange" },
};
export const PAY_KEYS = ["free_program", "public_aid", "grant", "resident"] as const;

export function money(n: unknown): string {
  const v = Number(n) || 0;
  const whole = Math.abs(v - Math.round(v)) < 0.005;
  return "$" + v.toLocaleString("en-US", { minimumFractionDigits: whole ? 0 : 2, maximumFractionDigits: whole ? 0 : 2 });
}

export function relTime(iso?: string): string {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  if (isNaN(t)) return "";
  const s = Math.round((Date.now() - t) / 1000);
  if (s < 45) return "just now";
  if (s < 3600) return Math.round(s / 60) + " min ago";
  if (s < 86400) return Math.round(s / 3600) + " h ago";
  return Math.round(s / 86400) + " d ago";
}

export const reducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Calls the API and normalises network failures into ApiError with stage "network". */
export async function call<T = Any>(path: string, body?: unknown): Promise<T> {
  try {
    return await api<T>(path, body);
  } catch (e) {
    if (e instanceof ApiError) throw e;
    throw new ApiError("Can't reach the Bridgeline server. Is it running?", "network", 0);
  }
}

/** Renders strings that contain a single <em>…</em> highlight. */
export function Rich({ text }: { text: string }) {
  const parts = text.split(/<em>(.*?)<\/em>/);
  return (
    <>
      {parts.map((p, i) => (i % 2 ? <em key={i}>{p}</em> : <Fragment key={i}>{p}</Fragment>))}
    </>
  );
}

const STAGE_LABEL: Record<string, string> = { mistral: "Mistral", elastic: "Elasticsearch", network: "Network", server: "Server", api: "Server" };

export function ErrorCard({ error, context }: { error: unknown; context?: string }) {
  const e = error as Any;
  const stage = (e && e.stage) || "server";
  return (
    <div className="error-card" role="alert">
      <div>
        <span className="stage">{STAGE_LABEL[stage] ?? stage}</span>
        <strong>{context || "Something went wrong"}</strong>
      </div>
      <div className="small">{(e && e.message) || String(error)}</div>
      <div className="tiny muted">Nothing on this screen was faked: the step failed, so no result is shown.</div>
    </div>
  );
}

export function Thinking({ msg }: { msg: string }) {
  return (
    <div className="thinking">
      <span className="dots"><i /><i /><i /></span>
      <span>{msg}</span>
    </div>
  );
}

export function PayBar({ totals, className = "" }: { totals?: Any; className?: string }) {
  const t = totals || {};
  const parts = PAY_KEYS.map((k) => [k, Math.max(0, Number(t[k]) || 0)] as const);
  const sum = parts.reduce((a, p) => a + p[1], 0);
  if (!sum)
    return (
      <div className={"paybar " + className} aria-hidden="true">
        <span className="p-free" style={{ flexGrow: 1 }} />
      </div>
    );
  return (
    <div className={"paybar " + className} role="img" aria-label={parts.map((p) => `${PAYER[p[0]].label} ${money(p[1])}`).join(", ")}>
      {parts.filter((p) => p[1] > 0).map((p) => (
        <span key={p[0]} className={"p-" + PAYER[p[0]].cls} style={{ flexGrow: p[1] }} />
      ))}
    </div>
  );
}

export function PayLegend({ totals, labels }: { totals?: Any; labels: Record<string, string> }) {
  const t = totals || {};
  return (
    <div className="paylegend">
      {PAY_KEYS.map((k) => (
        <span key={k}>
          <i className={"dot-" + PAYER[k].cls} />
          {labels[k] || PAYER[k].label} <strong>{money(t[k] || 0)}</strong>
        </span>
      ))}
    </div>
  );
}

export function BrandIcon() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <rect x="2" y="2" width="28" height="28" rx="9" fill="#0f1535" />
      <path d="M9 16.5 16 10l7 6.5V23a1 1 0 0 1-1 1h-3.5v-4.5h-5V24H10a1 1 0 0 1-1-1z" fill="#fbf6ec" />
      <path d="M17.6 4.5 13.8 12h3l-1.4 6 4.6-8.2h-3.1z" fill="#ffc933" stroke="#0f1535" strokeWidth=".8" strokeLinejoin="round" />
    </svg>
  );
}

export function Bolt({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size * 1.22} viewBox="0 0 18 22" aria-hidden="true">
      <path d="M11 0 1 13h6l-2 9 11-14h-6z" fill="#15182c" />
    </svg>
  );
}

export function DistBadge({ km, label }: { km: unknown; label: string }): ReactNode {
  if (km == null || isNaN(Number(km))) return null;
  const mi = Number(km) * 0.621371;
  return <span className="badge badge-blue">📍 {mi < 10 ? mi.toFixed(1) : Math.round(mi)} {label}</span>;
}
