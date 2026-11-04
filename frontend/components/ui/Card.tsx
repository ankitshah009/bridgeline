import type { HTMLAttributes } from "react";

export function Card({
  tone = "default",
  kicker,
  className = "",
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement> & { tone?: "default" | "flat" | "navy"; kicker?: React.ReactNode }) {
  const base = tone === "navy" ? "card-navy" : tone === "flat" ? "card-flat" : "card";
  return (
    <div className={`${base} ${className}`} {...rest}>
      {kicker ? <div className="kicker" style={{ marginBottom: 8 }}>{kicker}</div> : null}
      {children}
    </div>
  );
}
