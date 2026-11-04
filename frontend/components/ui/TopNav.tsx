"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "./Logo";

const LINKS = [
  { href: "/", label: "Resident" },
  { href: "/directory", label: "Directory" },
  { href: "/navigator", label: "Navigator" },
  { href: "/impact", label: "Impact" },
];

export function TopNav({ right }: { right?: React.ReactNode }) {
  const path = usePathname() ?? "/";
  return (
    <header className="topbar">
      <Link href="/" className="brand" aria-label="Bridgeline home">
        <Logo />
        <span className="brand-name">Bridgeline</span> <small>SF pilot</small>
      </Link>
      <span className="spacer" />
      <nav className="navlinks" aria-label="Main">
        {LINKS.map((l) => {
          const active = l.href === "/" ? path === "/" : path.startsWith(l.href);
          return (
            <Link key={l.href} href={l.href} aria-current={active ? "page" : undefined}>
              {l.label}
            </Link>
          );
        })}
      </nav>
      {right}
    </header>
  );
}
