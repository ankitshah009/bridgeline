"use client";

import { useEffect, useState } from "react";

// Result of the latest live source check (backend: app/freshness.py), attached to items as `live_check`.
export interface LiveCheckData {
  ok?: boolean | null;
  state?: "ok" | "flagged" | "broken" | "unverified" | string | null;
  http_status?: number | null;
  checked_at?: string | null;
  flagged?: boolean | null;
  note?: string | null;
  still_offered?: string | null;
  next_date?: string | null;
}

/** Re-renders every 30 s so "N min ago" stays current. null until mounted (keeps render pure). */
export function useNow(intervalMs = 30_000): number | null {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    const first = requestAnimationFrame(() => setNow(Date.now()));
    const t = setInterval(() => setNow(Date.now()), intervalMs);
    return () => {
      cancelAnimationFrame(first);
      clearInterval(t);
    };
  }, [intervalMs]);
  return now;
}

export function ago(iso: string | null | undefined, now: number | null): string {
  if (!iso || now == null) return "";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "";
  const s = Math.max(0, Math.round((now - t) / 1000));
  if (s < 60) return "just now";
  const m = Math.round(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 48) return `${h} h ago`;
  return `${Math.round(h / 24)} d ago`;
}

const LABEL: Record<string, string> = {
  ok: "Checked live",
  flagged: "Changed — staff review",
  broken: "Link issue",
  unverified: "Site blocks auto-check",
};

export function liveCheckDetail(c: LiveCheckData): string {
  const parts = [
    c.note,
    c.next_date ? `Next date on page: ${c.next_date}` : null,
    c.http_status ? `HTTP ${c.http_status}` : null,
  ].filter(Boolean);
  return parts.join(" · ");
}

export function LiveBadge({ check }: { check?: LiveCheckData | null }) {
  const now = useNow();
  if (!check || !check.state) return null;
  const state = String(check.state);
  const when = ago(check.checked_at, now);
  const label = LABEL[state] ?? "Checked";
  const text = state === "ok" && when ? `${label} · ${when}` : label;
  return (
    <span className={`live-badge live-${state}`} title={liveCheckDetail(check) || undefined}>
      <span className="live-dot" aria-hidden="true" />
      {text}
    </span>
  );
}

interface SourcesStatusData {
  checked_at_latest?: string | null;
  total?: number;
  ok?: number;
  flagged?: number;
  broken?: number;
  unverified?: number;
  running?: boolean;
}

/** Directory hero line: when sources were last checked live, with a "Re-check now" button. */
export function SourcesStatus({ onDone }: { onDone?: () => void }) {
  const now = useNow();
  const [s, setS] = useState<SourcesStatusData | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const res = await fetch("/api/sources/status", { cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const d: SourcesStatusData = await res.json();
        if (!alive) return;
        setS(d);
        setErr(null);
        if (d.running) {
          timer = setTimeout(poll, 3000);
        } else if (busy) {
          setBusy(false);
          onDone?.();
        }
      } catch (e) {
        if (alive) setErr(e instanceof Error ? e.message : "unavailable");
      }
    };
    poll();
    return () => {
      alive = false;
      if (timer) clearTimeout(timer);
    };
  }, [busy, onDone]);

  const recheck = async () => {
    setErr(null);
    try {
      const res = await fetch("/api/sources/verify", { method: "POST" });
      if (!res.ok && res.status !== 409) throw new Error(`HTTP ${res.status}`);
      setBusy(true);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "could not start");
    }
  };

  if (err && !s) return null;
  if (!s || !s.total) return null;
  const when = ago(s.checked_at_latest, now);
  return (
    <div className="live-status" aria-live="polite">
      <span className="live-dot" aria-hidden="true" />
      <span>
        {busy || s.running ? "Checking sources live…" : `Sources checked live${when ? ` ${when}` : ""}`} ·{" "}
        <strong>{s.ok ?? 0}</strong> OK
        {s.flagged ? <> · <strong>{s.flagged}</strong> flagged</> : null}
        {s.broken ? <> · <strong>{s.broken}</strong> link issues</> : null}
        {s.unverified ? <> · {s.unverified} block auto-checks</> : null}
      </span>
      <button type="button" className="live-recheck-link" onClick={recheck} disabled={busy || !!s.running}>
        {busy || s.running ? "Checking…" : "Re-check sources"}
      </button>
    </div>
  );
}
