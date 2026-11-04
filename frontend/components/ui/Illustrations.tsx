// Playful geometric illustrations (inline SVG, no external assets).

export function HeroIllustration({ className = "" }: { className?: string }) {
  return (
    <svg className={`illo ${className}`} viewBox="0 0 360 240" role="img" aria-label="A home connected to a laptop and a graduation path">
      <defs>
        <linearGradient id="hb-sky" x1="0" x2="1">
          <stop offset="0" stopColor="#ece7ff" />
          <stop offset="1" stopColor="#fff4cf" />
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="360" height="240" rx="28" fill="url(#hb-sky)" />
      <path d="M40 200 C 110 120, 200 230, 320 70" fill="none" stroke="#0f1535" strokeWidth="3" strokeDasharray="6 7" strokeLinecap="round" />
      <g className="float">
        <rect x="30" y="140" width="70" height="56" rx="10" fill="#15963f" />
        <path d="M65 108 22 146h86L65 108Z" fill="#0f1535" />
        <rect x="58" y="164" width="14" height="32" rx="3" fill="#ffc933" />
      </g>
      <g transform="rotate(45 175 150)">
        <rect x="155" y="130" width="40" height="40" rx="10" fill="#ff7a2f" />
      </g>
      <text x="168" y="157" fontSize="20" fontWeight="800" fill="#fff">✓</text>
      <g className="float" style={{ animationDelay: "-2s" }}>
        <rect x="250" y="40" width="88" height="58" rx="8" fill="#0f1535" />
        <rect x="257" y="47" width="74" height="42" rx="4" fill="#2f6bff" />
        <rect x="240" y="98" width="108" height="8" rx="4" fill="#0f1535" />
        <path d="M268 72 l10 8 l18 -18" stroke="#fff" strokeWidth="5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </g>
      <circle cx="318" cy="182" r="16" fill="#6d4dff" />
      <path d="M311 182 l5 5 l9 -10" stroke="#fff" strokeWidth="3.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="120" cy="58" r="7" fill="#ff4f7e" />
      <circle cx="200" cy="40" r="5" fill="#1fb24e" />
      <rect x="96" y="96" width="14" height="14" rx="3" fill="#ffc933" transform="rotate(20 103 103)" />
    </svg>
  );
}

export function ShieldIllustration({ size = 72 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 72 72" aria-hidden="true">
      <path d="M36 4 62 14v20c0 17-11 28-26 34C21 62 10 51 10 34V14L36 4Z" fill="#15963f" />
      <path d="M36 12 54 19v15c0 12-7 20-18 25-11-5-18-13-18-25V19l18-7Z" fill="#1fb24e" />
      <path d="M26 36l7 7 14-15" stroke="#fff" strokeWidth="5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function SparkIllustration({ size = 56 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 56 56" aria-hidden="true">
      <circle cx="28" cy="28" r="26" fill="#ffc933" />
      <path d="M31 10 17 31h10l-3 15 15-22H29l2-14Z" fill="#0f1535" />
    </svg>
  );
}

export function MistralMark({ size = 18 }: { size?: number }) {
  // Generic pixel-block mark for "AI draft" moments (not a brand logo).
  return (
    <svg width={size} height={size} viewBox="0 0 18 18" aria-hidden="true">
      <rect x="0" y="0" width="6" height="6" fill="#ffc933" />
      <rect x="12" y="0" width="6" height="6" fill="#ffc933" />
      <rect x="0" y="6" width="18" height="6" fill="#ff7a2f" />
      <rect x="0" y="12" width="6" height="6" fill="#ff4f7e" />
      <rect x="12" y="12" width="6" height="6" fill="#ff4f7e" />
    </svg>
  );
}

export function SearchMark({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 18 18" aria-hidden="true">
      <circle cx="7.5" cy="7.5" r="5.5" fill="none" stroke="#2f6bff" strokeWidth="2.4" />
      <path d="M12 12l4.5 4.5" stroke="#2f6bff" strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  );
}
