"use client";

import { ApiError } from "@/lib/api";

export const STATUS_LABEL: Record<string, string> = {
  submitted: "Submitted",
  in_review: "In review",
  approved: "Approved",
  needs_info: "Needs info",
  declined: "Declined",
  enrolled: "Enrolled",
  completed: "Completed",
  placed: "Placed",
};

export const TIER_LABEL: Record<string, string> = {
  starter: "Starter",
  stay_in_training: "Stay-in-Training",
  career: "Career",
};

export const HOUSING: Record<string, string> = {
  LIHTC: "LIHTC",
  public_housing: "Public housing",
  project_based: "Project-based Section 8",
  voucher: "Housing Choice Voucher",
  inclusionary: "Inclusionary (BMR)",
  small_sites: "Small Sites",
  supportive: "Supportive housing",
  other: "Other / unconfirmed",
};

export const LANGS: Record<string, string> = {
  en: "English",
  es: "Spanish",
  zh: "Chinese",
  "zh-hant": "Chinese (Trad.)",
  fil: "Filipino",
  tl: "Filipino",
  vi: "Vietnamese",
};

type PayerKey = "free_program" | "public_aid" | "grant" | "resident";
export const PAYER: Record<PayerKey, { label: string; cls: string; badge: string }> = {
  free_program: { label: "Free program", cls: "free", badge: "badge-green" },
  public_aid: { label: "Public aid", cls: "public", badge: "badge-blue" },
  grant: { label: "Bridgeline grant", cls: "grant", badge: "badge-purple" },
  resident: { label: "Resident pays", cls: "resident", badge: "badge-orange" },
};
const PAYER_ORDER: PayerKey[] = ["free_program", "public_aid", "grant", "resident"];

export function money(n: unknown): string {
  const v = Number(n) || 0;
  const whole = Math.abs(v - Math.round(v)) < 0.005;
  return (
    "$" +
    v.toLocaleString("en-US", {
      minimumFractionDigits: whole ? 0 : 2,
      maximumFractionDigits: whole ? 0 : 2,
    })
  );
}

export function relTime(iso?: string | null): string {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const s = Math.round((Date.now() - t) / 1000);
  if (s < 45) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}

export function langName(code?: string | null): string {
  if (!code) return "";
  return LANGS[String(code).toLowerCase()] ?? code;
}

export function PayBar({ totals }: { totals?: Record<string, number> }) {
  const t = totals ?? {};
  const parts = PAYER_ORDER.map((k) => [k, Math.max(0, Number(t[k]) || 0)] as const);
  const sum = parts.reduce((a, p) => a + p[1], 0);
  if (!sum) {
    return (
      <div className="paybar" aria-hidden="true">
        <span className="p-free" style={{ flexGrow: 1 }} />
      </div>
    );
  }
  return (
    <div
      className="paybar"
      role="img"
      aria-label={parts.map(([k, v]) => `${PAYER[k].label} ${money(v)}`).join(", ")}
    >
      {parts
        .filter(([, v]) => v > 0)
        .map(([k, v]) => (
          <span key={k} className={`p-${PAYER[k].cls}`} style={{ flexGrow: v }} />
        ))}
    </div>
  );
}

export function PayLegend({ totals }: { totals?: Record<string, number> }) {
  const t = totals ?? {};
  return (
    <div className="paylegend">
      {PAYER_ORDER.map((k) => (
        <span key={k}>
          <i className={`dot-${PAYER[k].cls}`} />
          {PAYER[k].label} <strong>{money(t[k] ?? 0)}</strong>
        </span>
      ))}
    </div>
  );
}

const STAGE_LABEL: Record<string, string> = {
  mistral: "Mistral",
  elastic: "Elasticsearch",
  network: "Network",
  server: "Server",
  api: "Server",
};

export function ErrorCard({ error, context }: { error: unknown; context?: string }) {
  let stage = "server";
  let message = String(error);
  if (error instanceof ApiError) {
    stage = error.stage || "server";
    message = error.message;
  } else if (error instanceof TypeError) {
    stage = "network";
    message = "Can't reach the Bridgeline server. Is it running?";
  } else if (error instanceof Error) {
    message = error.message;
  }
  return (
    <div className="error-card" role="alert">
      <div>
        <span className="stage">{STAGE_LABEL[stage] ?? stage}</span>
        <strong>{context ?? "Something went wrong"}</strong>
      </div>
      <div className="small">{message}</div>
      <div className="tiny muted">Nothing on this screen was faked: the step failed, so no result is shown.</div>
    </div>
  );
}

export function BrandMark() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <rect x="2" y="2" width="28" height="28" rx="9" fill="#0f1535" />
      <path d="M9 16.5 16 10l7 6.5V23a1 1 0 0 1-1 1h-3.5v-4.5h-5V24H10a1 1 0 0 1-1-1z" fill="#fbf6ec" />
      <path
        d="M17.6 4.5 13.8 12h3l-1.4 6 4.6-8.2h-3.1z"
        fill="#ffc933"
        stroke="#0f1535"
        strokeWidth=".8"
        strokeLinejoin="round"
      />
    </svg>
  );
}
