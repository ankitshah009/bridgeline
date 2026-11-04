"use client";

import type { TFn } from "./i18n";

export const JKEYS = ["j_join", "j_plan", "j_match", "j_apply", "j_fund", "j_complete", "j_advance"];

/** Brilliant-style winding lesson path: 7 journey nodes, done / current / upcoming. */
export function PathProgress({ current, t }: { current: number; t: TFn }) {
  const W = 720, n = 7, x0 = 52, dx = (W - 2 * x0) / (n - 1);
  const pts = JKEYS.map((_, i) => [x0 + i * dx, i % 2 ? 66 : 38] as const);
  const label = `Step ${Math.min(current + 1, 7)} of 7: ${t(JKEYS[Math.min(current, 6)])}`;
  return (
    <nav className="pathbar" aria-label="Your journey">
      <svg viewBox={`0 0 ${W} 122`} role="img" aria-label={label}>
        {pts.slice(0, -1).map(([ax, ay], i) => {
          const [bx, by] = pts[i + 1];
          const mx = (ax + bx) / 2;
          const done = i < current;
          return (
            <path
              key={"s" + i}
              d={`M${ax} ${ay} C ${mx} ${ay}, ${mx} ${by}, ${bx} ${by}`}
              fill="none"
              stroke={done ? "#1fb24e" : "#d9d1bf"}
              strokeWidth={done ? 7 : 5}
              strokeLinecap="round"
              strokeDasharray={done ? undefined : "1 12"}
            />
          );
        })}
        {pts.map(([x, y], i) => {
          const done = i < current, isCur = i === current;
          return (
            <g key={"n" + i}>
              {done ? (
                <>
                  <circle cx={x} cy={y} r={19} fill="#1fb24e" stroke="#0e7a33" strokeWidth={3} />
                  <path d={`M${x - 8} ${y} l5.5 6 l10 -11`} fill="none" stroke="#fff" strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" />
                </>
              ) : isCur ? (
                <>
                  <circle className="pulse" cx={x} cy={y} r={21} fill="#ffc933" />
                  <circle cx={x} cy={y} r={21} fill="#ffc933" stroke="#15182c" strokeWidth={3} />
                  <path d={`M${x + 2} ${y - 13} L${x - 7} ${y + 2} H${x - 1} L${x - 3} ${y + 13} L${x + 8} ${y - 3} H${x + 1}Z`} fill="#15182c" />
                </>
              ) : (
                <>
                  <circle cx={x} cy={y} r={17} fill="#fff" stroke="#d9d1bf" strokeWidth={3} />
                  <text x={x} y={y + 6} textAnchor="middle" style={{ fontSize: 16 }}>{i + 1}</text>
                </>
              )}
              <text x={x} y={112} textAnchor="middle" className={isCur ? "cur" : ""}>{t(JKEYS[i])}</text>
            </g>
          );
        })}
      </svg>
    </nav>
  );
}
