import { usd } from "@/lib/api";

export type PayTotals = { free_program?: number; public_aid?: number; grant?: number; resident?: number };

/** Stacked "Who pays" bar: free program / public aid / Bridgeline grant / resident. */
export function PayBar({ totals, legend = true }: { totals: PayTotals; legend?: boolean }) {
  const parts = [
    { k: "free", v: totals.free_program ?? 0, label: "Free program" },
    { k: "public", v: totals.public_aid ?? 0, label: "Public aid" },
    { k: "grant", v: totals.grant ?? 0, label: "Bridgeline grant" },
    { k: "resident", v: totals.resident ?? 0, label: "You pay" },
  ];
  const sum = parts.reduce((a, p) => a + p.v, 0) || 1;
  return (
    <div>
      <div className="paybar" role="img" aria-label={parts.map((p) => `${p.label} ${usd(p.v)}`).join(", ")}>
        {parts.map((p) => (p.v > 0 ? <span key={p.k} className={`p-${p.k}`} style={{ flexGrow: p.v / sum }} /> : null))}
      </div>
      {legend ? (
        <div className="paylegend">
          {parts.map((p) => (
            <span key={p.k}>
              <i className={`dot-${p.k}`} />
              {p.label} {usd(p.v)}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
