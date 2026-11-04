export type PathStep = { key: string; label: string; hint?: string; icon?: React.ReactNode };

/**
 * Brilliant-style guided path: diamond tiles connected by a winding line.
 * `current` is the index of the active step; earlier steps render as done.
 */
export function PathProgress({
  steps,
  current,
  horizontal = false,
}: {
  steps: PathStep[];
  current: number;
  horizontal?: boolean;
}) {
  return (
    <div className={`lpath ${horizontal ? "horizontal" : ""}`}>
      {!horizontal ? (
        <svg className="lpath-line" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <path
            d={steps
              .map((_, i) => {
                const y = ((i + 0.5) / steps.length) * 100;
                const x = i % 2 === 0 ? 8 : 92;
                return `${i === 0 ? "M" : "L"}${x},${y}`;
              })
              .join(" ")}
            fill="none"
            stroke="#e0d8c6"
            strokeWidth="1.2"
            strokeDasharray="3 2"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
      ) : null}
      <ol className="lpath-nodes" style={{ listStyle: "none", margin: 0, padding: 0 }}>
        {steps.map((s, i) => {
          const state = i < current ? "done" : i === current ? "current" : "todo";
          return (
            <li key={s.key} className={`lpath-node ${state}`} aria-current={state === "current" ? "step" : undefined}>
              <div className="lpath-tile">
                <span style={{ fontWeight: 800 }}>{state === "done" ? "✓" : s.icon ?? i + 1}</span>
              </div>
              <div className="lpath-label">
                <strong>{s.label}</strong>
                {s.hint ? <span>{s.hint}</span> : null}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export const JOURNEY: PathStep[] = [
  { key: "join", label: "Join", hint: "Confirm your home" },
  { key: "plan", label: "Plan", hint: "Your goal, your words" },
  { key: "match", label: "Match", hint: "Free options first" },
  { key: "apply", label: "Apply", hint: "One application" },
  { key: "fund", label: "Fund", hint: "Navigator + committee" },
  { key: "complete", label: "Complete", hint: "Reminders & support" },
  { key: "advance", label: "Advance", hint: "Job or raise" },
];
