export default function GlassPanel({ children, className = '' }) {
  return (
    <section
      className={`rounded-[30px] border border-[var(--glass-border)] bg-[var(--glass-bg)] shadow-[var(--glass-shadow)] backdrop-blur-[10px] ${className}`}
    >
      {children}
    </section>
  )
}
