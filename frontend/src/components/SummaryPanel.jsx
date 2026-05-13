import { useHuntStore } from '../store/useHuntStore'
import GlassPanel from './GlassPanel'

export default function SummaryPanel() {
  const huntResult = useHuntStore((s) => s.huntResult)
  const jobs = useHuntStore((s) => s.jobs)
  const applications = useHuntStore((s) => s.applications)

  const summary = huntResult?.summary ?? {}
  const totalSteps = 4
  const completedSteps = summary.completed_steps ?? 0
  const progressPct = totalSteps ? Math.round((completedSteps / totalSteps) * 100) : 0

  const metrics = [
    ['Jobs Found', String(jobs.length)],
    ['Applications', String(applications.length)],
    ['Tracked', String(summary.tracked_applications ?? 0)],
    ['Errors', String(summary.error_count ?? 0)],
  ]

  return (
    <GlassPanel className="p-6">
      <h2 className="text-[22px] font-black tracking-[-0.02em] text-[var(--text-primary)]">
        Summary
      </h2>

      <div className="mt-5 grid grid-cols-2 gap-3 max-sm:grid-cols-1">
        {metrics.map(([label, value]) => (
          <article className="rounded-[22px] bg-[var(--soft-panel)] p-4" key={label}>
            <p className="text-xs font-black uppercase text-[var(--text-muted)]">
              {label}
            </p>
            <p className="mt-2 text-3xl font-black text-[var(--text-primary)]">
              {value}
            </p>
          </article>
        ))}
      </div>

      <div className="mt-6">
        <div className="flex items-center justify-between">
          <p className="text-sm font-black text-[var(--text-primary)]">Pipeline Progress</p>
          <p className="text-sm font-black text-[var(--text-primary)]">{progressPct}%</p>
        </div>
        <div className="mt-3 h-4 overflow-hidden rounded-full bg-[var(--progress-track)]">
          <div
            className="h-full rounded-full bg-[linear-gradient(90deg,#6ca7ff,#aee9c8)] transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {huntResult?.goal && (
        <div className="mt-5 rounded-2xl bg-[var(--soft-panel)] p-4">
          <p className="text-xs font-black uppercase text-[var(--text-muted)]">Hunt Goal</p>
          <p className="mt-1 text-sm font-bold text-[var(--text-primary)]">{huntResult.goal}</p>
        </div>
      )}
    </GlassPanel>
  )
}
