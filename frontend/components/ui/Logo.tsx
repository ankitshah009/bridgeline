export function Logo({ size = 30 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect x="2" y="12" width="28" height="18" rx="5" fill="#15963f" />
      <path d="M16 2 2 14h28L16 2Z" fill="#0f1535" />
      <rect x="12" y="18" width="8" height="12" rx="2" fill="#ffc933" />
      <circle cx="25" cy="7" r="3" fill="#ff7a2f" />
    </svg>
  );
}
