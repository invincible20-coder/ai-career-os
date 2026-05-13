import { useHuntStore } from '../store/useHuntStore'
import GlassPanel from './GlassPanel'

const statusStyles = {
  completed: 'bg-[var(--completed-bg)] text-[var(--completed-text)] border-[var(--completed-border)]',
  running: 'bg-[var(--progress-bg)] text-[var(--progress-text)] border-[var(--progress-border)]',
  pending: 'bg-[var(--pending-bg)] text-[var(--pending-text)] border-[var(--pending-border)]',
  failed: 'bg-red-500/10 text-red-400 border-red-400/30',
}

const stepLabels = {
  plan: { title: 'Goal Understanding & Planning', agent: 'Planner Agent' },
  search: { title: 'Job Discovery', agent: 'Job Finder Agent' },
  apply: { title: 'Resume & Applications', agent: 'Resume + Apply Agents' },
  track: { title: 'Tracking & Monitoring', agent: 'Tracking Agent' },
}

export default function WorkflowPanel() {
  const huntResult = useHuntStore((s) => s.huntResult)
  const requestPhase = useHuntStore((s) => s.requestPhase)

  const progress = huntResult?.progress ?? []

  if (requestPhase === 'idle' && !huntResult) {
    return (
      <GlassPanel className="p-6 max-sm:p-5">
        <h2 className="text-[22px] font-black tracking-[-0.02em] text-[var(--text-primary)]">
          AI Hunt Workflow
        </h2>
        <p className="mt-4 text-sm font-semibold text-[var(--text-muted)]">
          Start a hunt to see the live workflow progress here.
        </p>
      </GlassPanel>
    )
  }

  return (
    <GlassPanel className="p-6 max-sm:p-5">
      <div className="mb-5 flex items-center justify-between gap-4">
        <h2 className="text-[22px] font-black tracking-[-0.02em] text-[var(--text-primary)]">
          AI Hunt Workflow
        </h2>
        {huntResult?.status === 'running' && (
          <span className="inline-flex items-center gap-2 rounded-full bg-[var(--live-bg)] px-3 py-1.5 text-xs font-black text-[var(--live-text)]">
            <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--live-dot)] shadow-[0_0_0_5px_var(--live-ring)]" />
            Live
          </span>
        )}
        {huntResult?.status === 'completed' && (
          <span className="inline-flex items-center gap-2 rounded-full bg-emerald-500/10 px-3 py-1.5 text-xs font-black text-emerald-400">
            ✓ Completed
          </span>
        )}
        {huntResult?.status === 'failed' && (
          <span className="inline-flex items-center gap-2 rounded-full bg-red-500/10 px-3 py-1.5 text-xs font-black text-red-400">
            ✕ Failed
          </span>
        )}
      </div>

      <div className="grid gap-3">
        {progress.map((item, idx) => {
          const label = stepLabels[item.step] ?? { title: item.step, agent: 'Agent' }
          const style = statusStyles[item.status] ?? statusStyles.pending
          return (
            <article
              className="grid grid-cols-[44px_minmax(0,1fr)_auto] items-center gap-4 rounded-[24px] border border-[var(--glass-border)] bg-[var(--row-bg)] p-4 max-sm:grid-cols-[44px_minmax(0,1fr)]"
              key={item.step}
            >
              <div className={`grid h-11 w-11 place-items-center rounded-2xl border text-sm font-black ${style}`}>
                {idx + 1}
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-[15px] font-black text-[var(--text-primary)]">
                    {label.title}
                  </h3>
                  <span className={`rounded-full border px-2.5 py-1 text-[11px] font-black ${style}`}>
                    {item.status}
                  </span>
                </div>
                <p className="mt-1 text-xs font-bold text-[var(--text-muted)]">
                  {label.agent} — Attempt {item.attempt_count}
                  {item.latency_ms != null ? ` · ${item.latency_ms}ms` : ''}
                </p>
              </div>
              <p className="max-w-[240px] text-right text-xs font-bold text-[var(--text-muted)] max-sm:col-span-2 max-sm:max-w-none max-sm:text-left">
                {item.status === 'completed' && '✓ Done'}
                {item.status === 'running' && '⏳ In progress…'}
                {item.status === 'pending' && 'Waiting'}
                {item.status === 'failed' && item.last_errors?.[0]?.message}
              </p>
            </article>
          )
        })}
      </div>
    </GlassPanel>
  )
}
