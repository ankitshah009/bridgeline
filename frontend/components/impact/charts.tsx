"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

export const fmt = (n: number | null | undefined) => (Number(n) || 0).toLocaleString("en-US");

export const money = (n: number | null | undefined) => {
  const v = Number(n) || 0;
  return "$" + Math.round(v).toLocaleString("en-US");
};

export const compactMoney = (n: number | null | undefined) => {
  const v = Number(n) || 0;
  if (Math.abs(v) >= 1_000_000) return "$" + (v / 1_000_000).toFixed(v >= 10_000_000 ? 0 : 1) + "M";
  if (Math.abs(v) >= 10_000) return "$" + Math.round(v / 1000) + "k";
  return money(v);
};

function prefersReducedMotion() {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

/** Animates from the previous value to the new one; renders the final value with reduced motion. */
export function CountUp({ value, format = fmt, duration = 900 }: { value: number; format?: (n: number) => string; duration?: number }) {
  const [shown, setShown] = useState(value);
  const from = useRef(0);
  useEffect(() => {
    if (prefersReducedMotion()) {
      from.current = value;
      const raf0 = requestAnimationFrame(() => setShown(value));
      return () => cancelAnimationFrame(raf0);
    }
    const start = performance.now();
    const a = from.current;
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / duration);
      const e = 1 - Math.pow(1 - p, 3);
      setShown(a + (value - a) * e);
      if (p < 1) raf = requestAnimationFrame(tick);
      else from.current = value;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  return <>{format(Math.round(shown))}</>;
}

/** Circular progress toward a target. `frac` is clamped to 0..1. */
export function Ring({ frac, tone = "green", children }: { frac: number; tone?: "green" | "yellow" | "purple" | "blue"; children?: ReactNode }) {
  const f = Math.max(0, Math.min(1, Number.isFinite(frac) ? frac : 0));
  const r = 30;
  const c = 2 * Math.PI * r;
  return (
    <div className="imp-ring">
      <svg viewBox="0 0 72 72" aria-hidden="true">
        <circle cx="36" cy="36" r={r} className="imp-ring-track" />
        <circle
          cx="36"
          cy="36"
          r={r}
          className={`imp-ring-val tone-${tone}`}
          strokeDasharray={`${c * f} ${c}`}
          transform="rotate(-90 36 36)"
        />
      </svg>
      <span>{children}</span>
    </div>
  );
}

export function HBar({
  label,
  value,
  max,
  color,
  right,
  title,
}: {
  label: string;
  value: number;
  max: number;
  color: string;
  right: ReactNode;
  title?: string;
}) {
  const w = max > 0 ? Math.max(1.5, (100 * (Number(value) || 0)) / max) : 0;
  return (
    <div className="imp-hbar">
      <span className="lbl" title={title ?? label}>
        {label}
      </span>
      <span className="track">
        <span style={{ width: `${w}%`, background: color }} />
      </span>
      <span className="val">{right}</span>
    </div>
  );
}

export function SplitBar({ label, a, b, max, right }: { label: string; a: number; b: number; max: number; right: ReactNode }) {
  const total = a + b;
  const w = max > 0 ? Math.max(2, (100 * total) / max) : 0;
  return (
    <div className="imp-hbar">
      <span className="lbl" title={label}>
        {label}
      </span>
      <span className="track">
        <span className="split" style={{ width: `${w}%` }}>
          <span style={{ flexGrow: a, background: "var(--green-hi)" }} />
          <span style={{ flexGrow: b, background: "#c9d7ff" }} />
        </span>
      </span>
      <span className="val">{right}</span>
    </div>
  );
}

export type PaySlice = { key: string; label: string; amount: number; color: string; note?: string };

export function StackBar({ slices, height = 34 }: { slices: PaySlice[]; height?: number }) {
  const sum = slices.reduce((s, x) => s + Math.max(0, x.amount), 0);
  return (
    <div
      className="imp-stack"
      style={{ height }}
      role="img"
      aria-label={slices.map((s) => `${s.label} ${money(s.amount)}`).join(", ")}
    >
      {sum === 0 ? (
        <span style={{ flexGrow: 1, background: "var(--cream-2)" }} />
      ) : (
        slices
          .filter((s) => s.amount > 0)
          .map((s) => (
            <span key={s.key} style={{ flexGrow: s.amount, background: s.color }}>
              {s.amount / sum > 0.12 ? <em>{Math.round((100 * s.amount) / sum)}%</em> : null}
            </span>
          ))
      )}
    </div>
  );
}

export function Donut({ parts, size = 132, label }: { parts: { value: number; color: string }[]; size?: number; label?: ReactNode }) {
  const total = parts.reduce((s, p) => s + p.value, 0) || 1;
  const r = 52;
  const c = 2 * Math.PI * r;
  const lens = parts.map((p) => (c * p.value) / total);
  const offsets = lens.map((_, i) => lens.slice(0, i).reduce((s, l) => s + l, 0));
  return (
    <div className="imp-donut" style={{ width: size, height: size }}>
      <svg viewBox="0 0 132 132" aria-hidden="true">
        <circle cx="66" cy="66" r={r} fill="none" stroke="var(--cream-2)" strokeWidth="18" />
        {parts.map((p, i) => {
          const len = lens[i];
          const offset = offsets[i];
          return (
            <circle
              key={i}
              cx="66"
              cy="66"
              r={r}
              fill="none"
              stroke={p.color}
              strokeWidth="18"
              strokeDasharray={`${len} ${c - len}`}
              strokeDashoffset={-offset}
              transform="rotate(-90 66 66)"
            />
          );
        })}
      </svg>
      {label ? <div className="imp-donut-label">{label}</div> : null}
    </div>
  );
}
