"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import type { TFn } from "./i18n";
import { call, ErrorCard, Rich, Thinking, type Any } from "./helpers";

function HeroArt() {
  return (
    <svg className="hero-art" viewBox="0 0 520 250" role="img" aria-label="A home connected by a path to a laptop">
      <line x1="20" y1="190" x2="500" y2="190" stroke="#15182c" strokeWidth="2" />
      <g stroke="#15182c" strokeWidth="1.5" opacity=".35">
        {[70, 140, 210, 310, 380, 450].map((x) => <line key={x} x1={x} y1="184" x2={x} y2="196" />)}
      </g>
      <path d="M40 190 A60 60 0 0 1 100 130 L100 190Z" fill="#ffc933" />
      <g transform="translate(120 70)">
        <path d="M0 62 L58 10 L116 62 V120 H0Z" fill="#0f1535" />
        <path d="M-8 64 L58 4 L124 64" fill="none" stroke="#15182c" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
        <rect x="44" y="76" width="28" height="44" rx="4" fill="#ffc933" />
        <rect x="14" y="72" width="20" height="18" rx="3" fill="#6d4dff" />
        <rect x="82" y="72" width="20" height="18" rx="3" fill="#6d4dff" />
      </g>
      <path className="art-path" d="M178 190 C 230 230, 300 120, 360 150" fill="none" stroke="#1fb24e" strokeWidth="5" strokeLinecap="round" strokeDasharray="2 12" />
      <g transform="translate(350 96)">
        <rect x="8" y="0" width="112" height="72" rx="8" fill="#fff" stroke="#15182c" strokeWidth="4" />
        <rect x="20" y="12" width="88" height="48" rx="4" fill="#e2ebff" />
        <path d="M34 48 L52 30 L66 40 L92 20" fill="none" stroke="#2f6bff" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M0 76 H128 L118 90 H10Z" fill="#15182c" />
      </g>
      <circle cx="300" cy="62" r="14" fill="#ff7a2f" stroke="#15182c" strokeWidth="3" />
      <circle cx="460" cy="58" r="10" fill="#fff" stroke="#15182c" strokeWidth="3" />
      <line x1="314" y1="62" x2="450" y2="58" stroke="#15182c" strokeWidth="2" strokeDasharray="4 6" />
      <g transform="translate(250 20)">
        <path d="M14 0 L2 22 H12 L8 40 L24 14 H14Z" fill="#ffc933" stroke="#15182c" strokeWidth="3" strokeLinejoin="round" />
      </g>
      <circle cx="478" cy="190" r="9" fill="#2f6bff" stroke="#fff" strokeWidth="3" />
      <g fill="#ff7a2f">
        <circle cx="420" cy="30" r="3" /><circle cx="432" cy="22" r="2.5" /><circle cx="440" cy="36" r="2" /><circle cx="410" cy="18" r="2" />
      </g>
    </svg>
  );
}

function BuildingTypeahead({ t, building, setBuilding }: { t: TFn; building: Any; setBuilding: (b: Any) => void }) {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<Any[]>([]);
  const [open, setOpen] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  const [active, setActive] = useState(-1);
  const seq = useRef(0);

  useEffect(() => {
    const query = q.trim();
    if (query.length < 2) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- close the dropdown when the query is cleared
      setOpen(false);
      return;
    }
    const my = ++seq.current;
    const timer = setTimeout(async () => {
      try {
        const r = await call(`/api/buildings?q=${encodeURIComponent(query)}`);
        if (my !== seq.current) return;
        setErr(null);
        setItems((r && r.buildings) || []);
        setActive(-1);
        setOpen(true);
      } catch (e) {
        if (my !== seq.current) return;
        setErr(e);
        setItems([]);
        setOpen(true);
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [q]);

  const pick = (i: number) => {
    setBuilding(items[i]);
    setQ("");
    setOpen(false);
  };
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") e.preventDefault();
    if (!open || !items.length) return;
    const n = Math.min(items.length, 8);
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => (a + (e.key === "ArrowDown" ? 1 : -1) + n) % n);
    } else if (e.key === "Enter" && active >= 0) pick(active);
    else if (e.key === "Escape") setOpen(false);
  };

  return (
    <div className="field ta-wrap">
      <label htmlFor="bq">
        <span>{t("find_building")}</span> <span className="small muted">{t("optional")}</span>
      </label>
      <input
        id="bq"
        className="input input-plain"
        type="search"
        autoComplete="off"
        spellCheck={false}
        placeholder="Street or building name"
        role="combobox"
        aria-autocomplete="list"
        aria-controls="bList"
        aria-expanded={open}
        aria-activedescendant={active >= 0 ? "bo" + active : undefined}
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={onKey}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
      />
      {open && (
        <ul id="bList" className="typeahead" role="listbox" aria-label="Buildings">
          {err ? (
            <li style={{ padding: 6 }}><ErrorCard error={err} context="Building search failed" /></li>
          ) : !items.length ? (
            <li className="small muted" style={{ padding: "10px 12px" }}>No match in the DataSF portfolio.</li>
          ) : (
            items.slice(0, 8).map((b, i) => (
              <li role="option" id={"bo" + i} key={b.id ?? i} aria-selected={i === active}>
                <button type="button" tabIndex={-1} className={i === active ? "on" : ""} onMouseDown={(e) => { e.preventDefault(); pick(i); }}>
                  <span className="bn">{b.name}</span>
                  <span className="ba">
                    {[b.address, b.neighborhood, b.affordable_units ? `${b.affordable_units} affordable homes` : ""].filter(Boolean).join(" · ")}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
      )}
      <p className="tiny muted" style={{ marginTop: 6 }}>From DataSF&apos;s affordable housing portfolio. We use it only to estimate travel to class.</p>
      {building && (
        <div className="picked">
          <span aria-hidden="true">📍</span>
          <div>
            <div style={{ fontWeight: 700 }}>{building.name}</div>
            <div className="small muted">
              {[building.address, building.neighborhood].filter(Boolean).join(" · ")}
              {building.affordable_units ? ` · ${building.affordable_units} affordable homes` : ""}
            </div>
          </div>
          <button type="button" className="x" aria-label="Clear building" onClick={() => setBuilding(null)}>×</button>
        </div>
      )}
    </div>
  );
}

export function JoinStep({
  t, building, setBuilding, onJoined,
}: { t: TFn; building: Any; setBuilding: (b: Any) => void; onJoined: (property: Any) => void }) {
  const [code, setCode] = useState("");
  const [props, setProps] = useState<Any[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ kind: "notfound" | "missing" | "error"; error?: unknown } | null>(null);

  useEffect(() => {
    call("/api/properties").then((l) => setProps(Array.isArray(l) ? l : [])).catch(() => {});
  }, []);

  const join = async (raw?: string) => {
    const c = (raw ?? code).trim().toUpperCase();
    if (raw) setCode(c);
    if (!c) return setMsg({ kind: "missing" });
    setBusy(true);
    setMsg(null);
    try {
      const r = await call("/api/join", { property_code: c });
      onJoined(r.property);
    } catch (e: Any) {
      setMsg(e?.status === 404 ? { kind: "notfound" } : { kind: "error", error: e });
    } finally {
      setBusy(false);
    }
  };
  const submit = (e: FormEvent) => {
    e.preventDefault();
    join();
  };

  return (
    <section className="screen" aria-labelledby="joinTitle">
      <div className="hero graph-paper">
        <HeroArt />
        <h1 id="joinTitle"><Rich text={t("tagline")} /></h1>
        <p className="lead">{t("join_sub")}</p>
      </div>

      <form className="stack" style={{ marginTop: 22 }} noValidate onSubmit={submit}>
        <div className="field">
          <label htmlFor="code">{t("code_label")}</label>
          <input
            id="code"
            className="input"
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            placeholder="e.g. MISSION-24"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          <p className="small muted" style={{ marginTop: 6 }}>{t("code_hint")}</p>
        </div>
        {props.length > 0 && (
          <div className="row" aria-label="Demo building codes">
            {props.slice(0, 3).map((p) => (
              <button key={p.code} type="button" className="chip" title={p.name} onClick={() => join(p.code)}>
                <span className="badge badge-ink">DEMO</span> {p.code}
              </button>
            ))}
          </div>
        )}
        <BuildingTypeahead t={t} building={building} setBuilding={setBuilding} />
        <div>
          {busy && <Thinking msg="…" />}
          {msg?.kind === "missing" && <p className="small" style={{ color: "var(--red)" }}>Enter the code from your building&apos;s text message.</p>}
          {msg?.kind === "notfound" && (
            <div className="error-card" role="alert">
              <strong>We don&apos;t recognize that code.</strong>
              <span className="small">Check the text from your building, or ask your service coordinator.</span>
            </div>
          )}
          {msg?.kind === "error" && <ErrorCard error={msg.error} context="Couldn't confirm your building" />}
        </div>
        <button className="btn btn-primary btn-block" type="submit" disabled={busy}>{t("get_started")}</button>
      </form>

      <div className="band">
        <h3>{t("band_title")}</h3>
        <div className="flow">
          <div><span className="n" style={{ background: "#7ef0a0" }}>1</span><b>{t("pay_free")}</b><span>{t("band_1")}</span></div>
          <div><span className="n" style={{ background: "#9db8ff" }}>2</span><b>{t("pay_public")}</b><span>{t("band_2")}</span></div>
          <div><span className="n" style={{ background: "#c3b4ff" }}>3</span><b>{t("pay_grant")}</b><span>{t("band_3")}</span></div>
        </div>
      </div>
    </section>
  );
}
