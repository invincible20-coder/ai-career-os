import { useHuntStore } from '../store/useHuntStore'
import GlassPanel from './GlassPanel'

export default function LiveActivityPanel() {
  const logs = useHuntStore((s) => s.logs)

  const levelColor = {
    info: 'text-blue-400',
    success: 'text-emerald-400',
    error: 'text-red-400',
    warn: 'text-amber-400',
  }

  return (
    <GlassPanel className="p-6">
      <h2 className="text-[22px] font-black tracking-[-0.02em] text-[var(--text-primary)]">
        Live Activity
      </h2>
      <div className="mt-5 grid gap-3 max-h-[420px] overflow-y-auto pr-1">
        {logs.slice(0, 20).map((entry) => (
          <article
            className="rounded-[20px] border border-[var(--glass-border)] bg-[var(--row-bg)] p-3"
            key={entry.id}
          >
            <div className="flex items-center gap-2">
              <span className={`text-[10px] font-black uppercase ${levelColor[entry.level] ?? 'text-[var(--text-muted)]'}`}>
                {entry.level}
              </span>
              <span className="text-[10px] font-semibold text-[var(--text-muted)]">
                {new Date(entry.at).toLocaleTimeString()}
              </span>
            </div>
            <p className="mt-1 text-sm font-semibold leading-5 text-[var(--text-muted)]">
              {entry.message}
            </p>
          </article>
        ))}
      </div>
    </GlassPanel>
  )
}
