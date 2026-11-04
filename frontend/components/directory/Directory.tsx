"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { ErrorCard, Thinking } from "@/components/ui";
import { Carousel } from "./Carousel";
import { DirectoryCard } from "./Cards";
import { DetailDialog } from "./DetailDialog";
import { DirectoryResponse, Item, Kind, SearchResponse, itemKind } from "./types";

type KindFilter = "all" | Kind;

const KIND_PILLS: { id: KindFilter; label: string }[] = [
  { id: "all", label: "Everything" },
  { id: "tier", label: "Grant tiers" },
  { id: "program", label: "Training" },
  { id: "resource", label: "Free help" },
];

const TOPICS: { id: string; label: string; words: string[] }[] = [
  { id: "childcare", label: "Child care", words: ["child", "childcare"] },
  { id: "transit", label: "Transit", words: ["transit", "muni", "clipper"] },
  { id: "device", label: "Laptops & internet", words: ["device", "laptop", "computer", "internet"] },
  { id: "digital-basics", label: "Digital basics", words: ["digital-basics", "basics", "beginner", "digital literacy"] },
  { id: "tech", label: "IT & tech careers", words: ["it support", "help desk", "network", "data", "tech"] },
  { id: "scholarship", label: "Scholarships", words: ["scholarship", "tuition", "savings"] },
];

function matchesTopic(item: Item, topicId: string | null): boolean {
  if (!topicId) return true;
  const topic = TOPICS.find((t) => t.id === topicId);
  if (!topic) return true;
  const tags: string[] = Array.isArray(item.tags) ? item.tags.map((t: string) => t.toLowerCase()) : [];
  if (tags.includes(topic.id)) return true;
  if (topic.id === "digital-basics" && item.level === "basics") return true;
  const hay = [
    item.name,
    item.program,
    item.label,
    item.provides,
    item.covers,
    item.description,
    item.category,
    ...(Array.isArray(item.career_tracks) ? item.career_tracks : []),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return topic.words.some((w) => hay.includes(w));
}

function errInfo(e: unknown): { stage: string; message: string } {
  if (e instanceof ApiError) return { stage: e.stage, message: e.message };
  return { stage: "api", message: e instanceof Error ? e.message : String(e) };
}

const COUNT_LABEL: Record<string, string> = {
  programs: "training programs",
  program: "training programs",
  resources: "free-help listings",
  resource: "free-help listings",
  tiers: "grant tiers",
  tier: "grant tiers",
};

export default function Directory() {
  const [data, setData] = useState<DirectoryResponse | null>(null);
  const [loadErr, setLoadErr] = useState<{ stage: string; message: string } | null>(null);
  const [kindFilter, setKindFilter] = useState<KindFilter>("all");
  const [topic, setTopic] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchErr, setSearchErr] = useState<{ stage: string; message: string } | null>(null);
  const [detail, setDetail] = useState<{ item: Item; kind: Kind } | null>(null);
  const searchSeq = useRef(0);

  const load = useCallback(async () => {
    try {
      const d = await api<DirectoryResponse>("/api/directory");
      setData(d);
      setLoadErr(null);
    } catch (e) {
      setLoadErr(errInfo(e));
    }
  }, []);

  useEffect(() => {
    let alive = true;
    api<DirectoryResponse>("/api/directory")
      .then((d) => {
        if (!alive) return;
        setData(d);
        setLoadErr(null);
      })
      .catch((e) => {
        if (alive) setLoadErr(errInfo(e));
      });
    return () => {
      alive = false;
    };
  }, []);

  // Retry every 5 s while the directory endpoint is failing.
  useEffect(() => {
    if (!loadErr) return;
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [loadErr, load]);

  // Debounced semantic search (350 ms), driven from the input handler.
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);
  const onQuery = (value: string) => {
    setQ(value);
    if (timer.current) clearTimeout(timer.current);
    const query = value.trim();
    const seq = ++searchSeq.current;
    if (!query) {
      setResults(null);
      setSearchErr(null);
      setSearching(false);
      return;
    }
    setSearching(true);
    timer.current = setTimeout(async () => {
      try {
        const r = await api<SearchResponse>(`/api/directory/search?q=${encodeURIComponent(query)}`);
        if (seq !== searchSeq.current) return;
        setResults(r);
        setSearchErr(null);
      } catch (e) {
        if (seq !== searchSeq.current) return;
        setSearchErr(errInfo(e));
        setResults(null);
      } finally {
        if (seq === searchSeq.current) setSearching(false);
      }
    }, 350);
  };

  const sections = useMemo(() => {
    if (!data?.sections) return [];
    return data.sections
      .filter((s) => kindFilter === "all" || s.kind === kindFilter)
      .map((s) => ({ ...s, items: (s.items ?? []).filter((it) => matchesTopic(it, topic)) }))
      .filter((s) => s.items.length > 0);
  }, [data, kindFilter, topic]);

  const filteredResults = useMemo(() => {
    if (!results?.results) return [];
    return results.results.filter(
      (it) => (kindFilter === "all" || itemKind(it, "program") === kindFilter) && matchesTopic(it, topic),
    );
  }, [results, kindFilter, topic]);

  const totalItems = data?.sections?.reduce((n, s) => n + (s.items?.length ?? 0), 0) ?? 0;
  const open = (item: Item, kind: Kind) => setDetail({ item, kind });

  return (
    <div className="dir">
      <section className="dir-hero">
        <div className="dir-hero-inner">
          <div className="kicker">Bridgeline directory · San Francisco</div>
          <h1>
            Explore everything <em>free</em> in SF.
          </h1>
          <p className="dir-lede">
            Training programs, Bridgeline grant tiers and free help for residents of affordable housing, in one place.
            Free options first. Search in any language.
          </p>
          <div className="dir-counts" aria-live="polite">
            {data?.counts && Object.keys(data.counts).length
              ? Object.entries(data.counts).map(([k, v]) => (
                  <span key={k} className="pill">
                    <strong>{v}</strong> {COUNT_LABEL[k] ?? k.replace(/_/g, " ")}
                  </span>
                ))
              : data
                ? (
                    <span className="pill">
                      <strong>{totalItems}</strong> listings
                    </span>
                  )
                : null}
          </div>
        </div>
        <svg className="dir-hero-art" viewBox="0 0 260 140" aria-hidden="true">
          <path d="M10 120 C 60 120, 70 60, 120 60 S 190 100, 250 30" fill="none" stroke="#15182c" strokeWidth="2.5" strokeDasharray="3 7" strokeLinecap="round" />
          <circle cx="10" cy="120" r="9" fill="#1fb24e" stroke="#15182c" strokeWidth="2.5" />
          <rect x="108" y="48" width="24" height="24" rx="5" fill="#ffc933" stroke="#15182c" strokeWidth="2.5" transform="rotate(45 120 60)" />
          <circle cx="250" cy="30" r="12" fill="#6d4dff" stroke="#15182c" strokeWidth="2.5" />
          <path d="M246 24l3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1z" fill="#fff" />
        </svg>
      </section>

      <div className="dir-sticky">
        <div className="dir-search">
          <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" className="dir-search-icon">
            <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" strokeWidth="2.4" />
            <path d="M16.5 16.5 21 21" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
          </svg>
          <input
            type="search"
            value={q}
            onChange={(e) => onQuery(e.target.value)}
            placeholder="Busca en cualquier idioma / Search in any language"
            aria-label="Search programs, grants and free help in any language"
            enterKeyHint="search"
          />
          {q ? (
            <button type="button" className="dir-clear" onClick={() => onQuery("")} aria-label="Clear search">
              ✕
            </button>
          ) : null}
        </div>
        <div className="dir-pills" role="toolbar" aria-label="Filter">
          {KIND_PILLS.map((p) => (
            <button
              key={p.id}
              type="button"
              className={`dir-pill ${kindFilter === p.id ? "on" : ""}`}
              aria-pressed={kindFilter === p.id}
              onClick={() => setKindFilter(p.id)}
            >
              {p.label}
            </button>
          ))}
          <span className="dir-pill-sep" aria-hidden="true" />
          {TOPICS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`dir-pill dir-pill-topic ${topic === t.id ? "on" : ""}`}
              aria-pressed={topic === t.id}
              onClick={() => setTopic(topic === t.id ? null : t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="dir-body">
        {q.trim() ? (
          <section className="dir-results" aria-live="polite">
            <div className="dir-section-head">
              <div>
                <h2>Results for “{q.trim()}”</h2>
                <p className="muted">Ranked by meaning, not keywords, so Spanish, Chinese or English all work.</p>
              </div>
              <span className="dir-proof">
                <span className="dot" /> Elasticsearch · semantic
                {results?.ms != null ? ` · ${results.ms} ms` : ""}
              </span>
            </div>
            {searching && !results ? <Thinking>Searching every listing…</Thinking> : null}
            {searchErr ? <ErrorCard stage={searchErr.stage} message={searchErr.message} /> : null}
            {results && !filteredResults.length && !searching ? (
              <p className="muted">No matches with these filters. Try clearing a filter or rephrasing.</p>
            ) : null}
            <div className={`dir-grid ${searching ? "is-stale" : ""}`}>
              {filteredResults.map((it, i) => (
                <DirectoryCard key={`${it.kind ?? "x"}-${it.id ?? i}`} item={it} fallback="program" onOpen={open} />
              ))}
            </div>
          </section>
        ) : null}

        {loadErr ? (
          <div className="dir-error">
            <ErrorCard stage={loadErr.stage} message={`${loadErr.message}. Retrying every 5 seconds.`} onRetry={load} />
          </div>
        ) : null}

        {!data && !loadErr ? <Thinking>Loading the directory…</Thinking> : null}

        {!q.trim() &&
          sections.map((s) => (
            <section key={s.id} className={`dir-section dir-section-${s.kind}`}>
              <div className="dir-section-head">
                <div>
                  <h2>{s.title}</h2>
                  {s.subtitle ? <p className="muted">{s.subtitle}</p> : null}
                </div>
                <span className="dir-count">{s.items.length}</span>
              </div>
              <Carousel label={s.title}>
                {s.items.map((it, i) => (
                  <div className="dir-slide" key={`${s.id}-${it.id ?? i}`}>
                    <DirectoryCard item={it} fallback={s.kind} onOpen={open} />
                  </div>
                ))}
              </Carousel>
            </section>
          ))}

        {data && !q.trim() && !sections.length ? (
          <p className="muted">Nothing matches these filters yet. Clear a filter to see everything.</p>
        ) : null}
      </div>

      <DetailDialog item={detail?.item ?? null} kind={detail?.kind ?? "program"} onClose={() => setDetail(null)} />
    </div>
  );
}
