"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { TFn } from "./i18n";
import { Bolt, reducedMotion, type Any } from "./helpers";
import { LiveBadge } from "@/components/directory/LiveCheck";

/** Status of a free-help listing: Available (green), Confirm (yellow), Closed / not yet (grey). */
export function ResStatusPill({ status, t }: { status?: string; t?: TFn }) {
  const s = String(status || "").toLowerCase();
  const tr = (k: string, fallback: string) => (t ? t(k) : fallback);
  if (s.startsWith("avail")) return <span className="badge badge-green">{tr("st_available", "Available")}</span>;
  if (s.startsWith("confirm") || s.startsWith("check") || s.startsWith("verify")) return <span className="badge badge-yellow">{tr("st_confirm", "Confirm")}</span>;
  if (s.startsWith("closed") || s.startsWith("not yet")) return <span className="badge">{status}</span>;
  return status ? <span className="badge">{status}</span> : null;
}

/** A list of free-help resources (from the Elasticsearch resources index). */
export function ResourceItems({ items, t }: { items: Any[]; t?: TFn }) {
  return (
    <div className="res-list">
      {items.map((x, i) => (
        <div className="res" key={x.id ?? i}>
          <div className="row" style={{ gap: 6 }}>
            <ResStatusPill status={x.status} t={t} />
            {x.category && <span className="badge">{x.category}</span>}
            <LiveBadge check={x.live_check} />
          </div>
          <div className="res-name">{x.program || x.name}</div>
          {x.provides && <div className="small">{x.provides}</div>}
          {x.who && <div className="small muted">{x.who}</div>}
          {x.status_note && <div className="tiny muted">{x.status_note}</div>}
          {x._why && <div className="why" style={{ margin: "6px 0 0" }}>{x._why}</div>}
          {x.source_url && (
            <a className="small" href={x.source_url} target="_blank" rel="noopener noreferrer">{t ? t("source") : "Source"} ↗</a>
          )}
        </div>
      ))}
    </div>
  );
}

/**
 * Honest answer when the resident's goal is outside tech training: say so, show free help for the
 * path they actually described, and point to the Directory. Never rewrite their goal into tech.
 */
export function OutOfScopeCard({
  t, note, alternatives, supports, loading, hasTech, techLabel, onSeeTech,
}: {
  t: TFn; note?: string | null; alternatives: Any[] | null; supports?: Any[] | null; loading: boolean;
  hasTech: boolean; techLabel?: string; onSeeTech?: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" });
  }, []);
  return (
    <div className="card oos" ref={ref} role="status">
      <span className="kicker">{t("oos_kicker")}</span>
      <h3 style={{ marginTop: 6 }}>{t("oos_title")}</h3>
      {note && <p className="oos-note">{note}</p>}
      <p className="small muted" style={{ marginTop: 6 }}>{t("oos_body")}</p>
      {loading && <p className="small muted" style={{ marginTop: 10 }}>{t("oos_checking")}</p>}
      {!loading && alternatives && alternatives.length > 0 && (
        <>
          <div className="oos-sub">{t("oos_alts")}</div>
          <ResourceItems items={alternatives} t={t} />
        </>
      )}
      {!loading && alternatives && alternatives.length === 0 && <p className="small" style={{ marginTop: 10 }}>{t("oos_none")}</p>}
      {!loading && supports && supports.length > 0 && (
        <>
          <div className="oos-sub">{t("oos_supports")}</div>
          <ResourceItems items={supports} t={t} />
        </>
      )}
      <div className="oos-actions">
        <Link className="btn btn-ghost btn-sm" href="/directory">{t("oos_directory")}</Link>
        {hasTech && onSeeTech && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={onSeeTech}>{techLabel || t("oos_tech")}</button>
        )}
      </div>
    </div>
  );
}

/** Mistral asks one follow-up question when the story is too thin to plan from. */
export function FollowUp({
  t, question, loading, onAnswer,
}: {
  t: TFn; question: string; loading: boolean; onAnswer: (answer: string) => void;
}) {
  const [answer, setAnswer] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    inputRef.current?.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "center" });
    const id = setTimeout(() => inputRef.current?.focus({ preventScroll: true }), 300);
    return () => clearTimeout(id);
  }, [question]);
  const send = () => {
    const a = answer.trim();
    if (a && !loading) onAnswer(a);
  };
  return (
    <div className="followup">
      <div className="followup-bubble">
        <span className="bolt"><Bolt /></span>
        <div>
          <div className="kicker">{t("clarify_title")}</div>
          <p className="followup-q">{question}</p>
          <p className="tiny muted">{t("clarify_hint")}</p>
        </div>
      </div>
      <label htmlFor="followup-answer" className="sr-only">{t("answer_ph")}</label>
      <textarea
        id="followup-answer"
        ref={inputRef}
        className="input"
        rows={3}
        placeholder={t("answer_ph")}
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) send();
        }}
      />
      <div className="row" style={{ gap: 10, marginTop: 10, flexWrap: "wrap" }}>
        <button type="button" className="btn btn-primary" onClick={send} disabled={!answer.trim() || loading}>
          {loading ? "…" : t("send_answer")}
        </button>
      </div>
    </div>
  );
}
