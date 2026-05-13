export default function TopHeader({ themeMode, onThemeChange }) {
  return (
    <header className="flex min-h-24 items-center justify-between gap-6 rounded-[32px] border border-[var(--glass-border)] bg-[var(--glass-bg)] px-7 py-5 shadow-[var(--glass-shadow)] backdrop-blur-[10px] max-md:flex-col max-md:items-start">
      <div>
        <h1 className="text-[28px] font-black leading-tight tracking-[-0.03em] text-[var(--text-primary)] max-sm:text-2xl">
          Good morning, Swaransh! 👋
        </h1>
        <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
          Let's build your dream career.
        </p>
      </div>

      <div className="flex items-center gap-3 max-sm:w-full max-sm:justify-between">
        <div className="flex rounded-full border border-[var(--glass-border)] bg-[var(--segmented-bg)] p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.4)]">
          {['Light', 'Dark', 'System'].map((mode) => (
            <button
              className={`h-9 rounded-full px-4 text-xs font-black transition ${themeMode === mode
                ? 'bg-[var(--segmented-active)] text-[var(--active-text)] shadow-[0_10px_22px_rgba(88,118,164,0.16)]'
                : 'text-[var(--text-muted)]'
                }`}
              key={mode}
              onClick={() => onThemeChange(mode)}
              type="button"
            >
              {mode}
            </button>
          ))}
        </div>

        <button
          aria-label="Notifications"
          className="grid h-11 w-11 place-items-center rounded-full border border-[var(--glass-border)] bg-[var(--soft-panel)] text-[var(--text-primary)] shadow-[0_14px_28px_rgba(100,121,150,0.13)]"
          type="button"
        >
          <svg aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
        </button>
      </div>
    </header>
  )
}
