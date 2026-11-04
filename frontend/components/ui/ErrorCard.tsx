export function ErrorCard({ stage, message, onRetry }: { stage?: string; message: string; onRetry?: () => void }) {
  return (
    <div className="error-card" role="alert">
      <div>
        {stage ? <span className="stage">{stage}</span> : null}
        <strong>Something didn&apos;t work.</strong>
      </div>
      <div className="small">{message}</div>
      {onRetry ? (
        <div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onRetry}>
            Try again
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function Thinking({ children }: { children: React.ReactNode }) {
  return (
    <div className="thinking" role="status" aria-live="polite">
      <span className="dots" aria-hidden="true">
        <i />
        <i />
        <i />
      </span>
      {children}
    </div>
  );
}
