export function Pill({
  tone,
  children,
  className = "",
}: {
  tone?: "green" | "navy" | "yellow" | "purple";
  children: React.ReactNode;
  className?: string;
}) {
  return <span className={`pill ${tone ? `pill-${tone}` : ""} ${className}`}>{children}</span>;
}
