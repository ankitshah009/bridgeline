export function Stat({
  label,
  value,
  sub,
  progress,
  tone = "default",
  accent,
}: {
  label: React.ReactNode;
  value: React.ReactNode;
  sub?: React.ReactNode;
  /** 0..1, renders a progress bar toward a target */
  progress?: number | null;
  tone?: "default" | "navy";
  accent?: "green" | "purple" | "orange" | "blue" | "yellow";
}) {
  const pct = progress == null ? null : Math.max(0, Math.min(1, progress)) * 100;
  return (
    <div className={`stat ${tone === "navy" ? "stat-navy" : ""} ${accent ? `stat-accent-${accent}` : ""}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub ? <div className="stat-sub">{sub}</div> : null}
      {pct != null ? (
        <div className="stat-bar" aria-hidden="true">
          <span style={{ width: `${pct}%` }} />
        </div>
      ) : null}
    </div>
  );
}
