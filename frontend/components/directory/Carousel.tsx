"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/** Horizontal scroll-snap carousel: arrows, swipe, keyboard, peeking next card. */
export function Carousel({ label, children }: { label: string; children: React.ReactNode }) {
  const track = useRef<HTMLDivElement>(null);
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(false);

  const update = useCallback(() => {
    const el = track.current;
    if (!el) return;
    setAtStart(el.scrollLeft <= 4);
    setAtEnd(el.scrollLeft + el.clientWidth >= el.scrollWidth - 4);
  }, []);

  useEffect(() => {
    update();
    const el = track.current;
    if (!el) return;
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, [update, children]);

  const page = (dir: 1 | -1) => {
    const el = track.current;
    if (!el) return;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    el.scrollBy({ left: dir * Math.max(260, el.clientWidth * 0.85), behavior: reduce ? "auto" : "smooth" });
  };

  return (
    <div className="dir-carousel">
      <div
        ref={track}
        className="dir-track"
        role="region"
        aria-roledescription="carousel"
        aria-label={label}
        tabIndex={0}
        onScroll={update}
        onKeyDown={(e) => {
          if (e.target !== e.currentTarget) return;
          if (e.key === "ArrowRight") {
            e.preventDefault();
            page(1);
          } else if (e.key === "ArrowLeft") {
            e.preventDefault();
            page(-1);
          }
        }}
      >
        {children}
      </div>
      <button
        type="button"
        className="dir-arrow dir-arrow-prev"
        aria-label={`Previous ${label}`}
        onClick={() => page(-1)}
        disabled={atStart}
      >
        <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
          <path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      <button
        type="button"
        className="dir-arrow dir-arrow-next"
        aria-label={`Next ${label}`}
        onClick={() => page(1)}
        disabled={atEnd}
      >
        <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
          <path d="M9 5l7 7-7 7" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
    </div>
  );
}
