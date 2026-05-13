import { useHuntStore } from '../store/useHuntStore'
import GlassPanel from './GlassPanel'

export default function JobMatchSection() {
  const jobs = useHuntStore((s) => s.jobs)
  const selectedJobId = useHuntStore((s) => s.selectedJobId)
  const selectJob = useHuntStore((s) => s.selectJob)
  const jobFilter = useHuntStore((s) => s.jobFilter)
  const setJobFilter = useHuntStore((s) => s.setJobFilter)

  const filtered = jobFilter
    ? jobs.filter(
        (j) =>
          j.title.toLowerCase().includes(jobFilter.toLowerCase()) ||
          j.company.toLowerCase().includes(jobFilter.toLowerCase()),
      )
    : jobs

  if (!jobs.length) {
    return (
      <GlassPanel className="p-6">
        <h2 className="text-[22px] font-black tracking-[-0.02em] text-[var(--text-primary)]">
          Top Matching Jobs
        </h2>
        <p className="mt-4 text-sm font-semibold text-[var(--text-muted)]">
          Jobs will appear here after a hunt completes.
        </p>
      </GlassPanel>
    )
  }

  return (
    <GlassPanel className="p-6">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-[22px] font-black tracking-[-0.02em] text-[var(--text-primary)]">
          Top Matching Jobs
        </h2>
        <span className="rounded-full bg-[var(--soft-panel)] px-3 py-1 text-xs font-black text-[var(--text-muted)]">
          {jobs.length} found
        </span>
      </div>

      <input
        className="mt-4 h-10 w-full rounded-2xl border border-[var(--input-border)] bg-[var(--input-bg)] px-4 text-sm font-semibold text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)]/60 focus:border-[#6ca7ff]"
        onChange={(e) => setJobFilter(e.target.value)}
        placeholder="Filter jobs…"
        value={jobFilter}
      />

      <div className="mt-4 grid gap-3 max-h-[400px] overflow-y-auto pr-1">
        {filtered.map((job) => (
          <article
            className={`cursor-pointer rounded-[22px] border p-4 shadow-[0_12px_28px_rgba(111,132,163,0.07)] transition hover:scale-[1.01] ${
              selectedJobId === job.job_id
                ? 'border-[#6ca7ff] bg-[#6ca7ff]/8'
                : 'border-[var(--glass-border)] bg-[var(--job-card-bg)]'
            }`}
            key={job.job_id}
            onClick={() => selectJob(job.job_id)}
          >
            <h3 className="text-[15px] font-black text-[var(--text-primary)]">
              {job.company} — {job.title}
            </h3>
            <p className="mt-1 text-xs font-bold text-[var(--text-muted)]">
              {job.location} · {job.source}
            </p>
            {job.salary_range && (
              <p className="mt-1 text-xs font-semibold text-emerald-400">
                {job.salary_range}
              </p>
            )}
            <div className="mt-3 flex flex-wrap gap-1.5">
              {(job.requirements ?? []).slice(0, 5).map((skill) => (
                <span
                  className="rounded-full bg-[var(--chip-bg)] px-2.5 py-1 text-[11px] font-black text-[var(--text-primary)]"
                  key={skill}
                >
                  {skill}
                </span>
              ))}
            </div>
          </article>
        ))}
      </div>
    </GlassPanel>
  )
}
