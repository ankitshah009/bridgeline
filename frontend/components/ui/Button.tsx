import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "ghost" | "dark" | "danger";

export function Button({
  variant = "primary",
  size,
  block,
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" | "icon"; block?: boolean }) {
  const cls = ["btn", `btn-${variant}`, size ? `btn-${size}` : "", block ? "btn-block" : "", className]
    .filter(Boolean)
    .join(" ");
  return <button type="button" className={cls} {...rest} />;
}
