export type BadgeTone = "green" | "yellow" | "purple" | "blue" | "orange" | "red" | "ink" | "ai";

export function Badge({ tone, children, title }: { tone?: BadgeTone; children: React.ReactNode; title?: string }) {
  return (
    <span className={`badge ${tone ? `badge-${tone}` : ""}`} title={title}>
      {children}
    </span>
  );
}

export function StatusPill({ status }: { status: string }) {
  return <span className={`status st-${status}`}>{status.replace(/_/g, " ")}</span>;
}
