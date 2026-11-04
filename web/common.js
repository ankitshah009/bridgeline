/* Bridgeline: shared helpers (no build step) */
(function () {
  "use strict";

  class ApiError extends Error {
    constructor(message, stage, status) { super(message); this.stage = stage || "server"; this.status = status; }
  }

  async function api(path, opts) {
    const init = { headers: { "Accept": "application/json" } };
    if (opts && opts.body !== undefined) {
      init.method = opts.method || "POST";
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(opts.body);
    } else if (opts && opts.method) {
      init.method = opts.method;
    }
    let res;
    try { res = await fetch(path, init); }
    catch (e) { throw new ApiError("Can't reach the Bridgeline server. Is it running?", "network"); }
    let data = null;
    const text = await res.text();
    try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
    if (!res.ok) {
      const msg = (data && (data.error || data.detail && (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)))) || (res.status + " " + res.statusText);
      throw new ApiError(msg, data && data.stage, res.status);
    }
    return data;
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function money(n, opts) {
    const v = Number(n) || 0;
    const whole = Math.abs(v - Math.round(v)) < 0.005;
    return "$" + v.toLocaleString("en-US", { minimumFractionDigits: whole ? 0 : 2, maximumFractionDigits: whole ? 0 : 2 });
  }

  function pct(n, digits) { return (Number(n) * 100).toFixed(digits == null ? 0 : digits) + "%"; }

  function errorHTML(err, context) {
    const stage = (err && err.stage) || "server";
    const label = { mistral: "Mistral", elastic: "Elasticsearch", network: "Network", server: "Server" }[stage] || stage;
    return '<div class="error-card" role="alert"><div><span class="stage">' + esc(label) + '</span><strong>' +
      esc(context || "Something went wrong") + '</strong></div><div class="small">' + esc(err && err.message || String(err)) +
      '</div><div class="tiny muted">Nothing on this screen was faked: the step failed, so no result is shown.</div></div>';
  }

  function relTime(iso) {
    if (!iso) return "";
    const t = new Date(iso).getTime();
    if (isNaN(t)) return "";
    const s = Math.round((Date.now() - t) / 1000);
    if (s < 45) return "just now";
    if (s < 3600) return Math.round(s / 60) + " min ago";
    if (s < 86400) return Math.round(s / 3600) + " h ago";
    return Math.round(s / 86400) + " d ago";
  }

  const STATUS_LABEL = {
    submitted: "Submitted", in_review: "In review", approved: "Approved", needs_info: "Needs info",
    declined: "Declined", enrolled: "Enrolled", completed: "Completed", placed: "Placed"
  };
  const TIER_LABEL = { starter: "Starter", stay_in_training: "Stay-in-Training", career: "Career" };
  const PAYER = {
    free_program: { label: "Free program", cls: "free", badge: "badge-green" },
    public_aid: { label: "Public aid", cls: "public", badge: "badge-blue" },
    grant: { label: "Bridgeline grant", cls: "grant", badge: "badge-purple" },
    resident: { label: "You pay", cls: "resident", badge: "badge-orange" }
  };

  function payBar(totals) {
    const t = totals || {};
    const parts = ["free_program", "public_aid", "grant", "resident"].map(k => [k, Math.max(0, Number(t[k]) || 0)]);
    const sum = parts.reduce((a, p) => a + p[1], 0);
    if (!sum) return '<div class="paybar" aria-hidden="true"><span class="p-free" style="flex-grow:1"></span></div>';
    return '<div class="paybar" role="img" aria-label="' + esc(parts.map(p => PAYER[p[0]].label + " " + money(p[1])).join(", ")) + '">' +
      parts.filter(p => p[1] > 0).map(p => '<span class="p-' + PAYER[p[0]].cls + '" style="flex-grow:' + p[1] + '"></span>').join("") + '</div>';
  }

  function payLegend(totals, labels) {
    const t = totals || {};
    const L = labels || {};
    return '<div class="paylegend">' + ["free_program", "public_aid", "grant", "resident"].map(k =>
      '<span><i class="dot-' + PAYER[k].cls + '"></i>' + esc(L[k] || PAYER[k].label) + ' <strong>' + money(t[k] || 0) + '</strong></span>').join("") + '</div>';
  }

  const BRAND_SVG = '<svg viewBox="0 0 32 32" aria-hidden="true"><rect x="2" y="2" width="28" height="28" rx="9" fill="#0f1535"/><path d="M9 16.5 16 10l7 6.5V23a1 1 0 0 1-1 1h-3.5v-4.5h-5V24H10a1 1 0 0 1-1-1z" fill="#fbf6ec"/><path d="M17.6 4.5 13.8 12h3l-1.4 6 4.6-8.2h-3.1z" fill="#ffc933" stroke="#0f1535" stroke-width=".8" stroke-linejoin="round"/></svg>';

  window.HB = { api, ApiError, esc, money, pct, errorHTML, relTime, STATUS_LABEL, TIER_LABEL, PAYER, payBar, payLegend, BRAND_SVG };
})();
