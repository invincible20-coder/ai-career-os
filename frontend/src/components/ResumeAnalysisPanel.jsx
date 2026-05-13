import { useHuntStore } from '../store/useHuntStore'
import GlassPanel from './GlassPanel'

export default function ResumeAnalysisPanel() {
  const applications = useHuntStore((s) => s.applications)
  const selectedJobId = useHuntStore((s) => s.selectedJobId)
  const contentTab = useHuntStore((s) => s.contentTab)
  const setContentTab = useHuntStore((s) => s.setContentTab)
  const careerResult = useHuntStore((s) => s.careerResult)
  const useRoleAndStart = useHuntStore((s) => s.useRoleAndStart)
  const activeAction = useHuntStore((s) => s.activeAction)

  const selectedApp = applications.find((a) => a.job_id === selectedJobId) ?? applications[0]

  // Show career recommendations if available and no applications yet
  if (careerResult && !applications.length) {
    return (
      <GlassPanel className="p-6">
        <h2 className="text-[22px] font-black tracking-[-0.02em] text-[var(--text-primary)]">
          Career Recommendations
        </h2>
        <div className="mt-4 grid gap-3">
          {(careerResult.recommended_roles ?? []).map((role) => (
            <article
              className="rounded-[22px] border border-[var(--glass-border)] bg-[var(--row-bg)] p-4"
              key={role.role}
            >
              <h3 className="text-[15px] font-black text-[var(--text-primary)]">{role.role}</h3>
              <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">{role.reason}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {(role.required_skills ?? []).map((s) => (
                  <span className="rounded-full bg-[var(--chip-bg)] px-2.5 py-1 text-[11px] font-black text-[var(--text-primary)]" key={s}>{s}</span>
                ))}
              </div>
              <button
                className="mt-3 h-9 rounded-full bg-[linear-gradient(135deg,#6ca7ff,#aee9c8)] px-5 text-xs font-black text-[#173453] transition hover:scale-[1.02] disabled:opacity-50"
                disabled={!!activeAction}
                onClick={() => useRoleAndStart(role.role)}
                type="button"
              >
                Hunt for this role →
              </button>
            </article>
          ))}
        </div>
      </GlassPanel>
    )
  }

  if (!selectedApp) {
    return (
      <GlassPanel className="p-6">
        <h2 className="text-[22px] font-black tracking-[-0.02em] text-[var(--text-primary)]">
          Resume & Cover Letter
        </h2>
        <p className="mt-4 text-sm font-semibold text-[var(--text-muted)]">
          Select a job or run a hunt to see generated content.
        </p>
      </GlassPanel>
    )
  }

  const resume = selectedApp.resume
  const coverLetter = selectedApp.cover_letter

  return (
    <GlassPanel className="p-6">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-[20px] font-black tracking-[-0.02em] text-[var(--text-primary)]">
          {selectedApp.company} — {selectedApp.job_title}
        </h2>
        <span className="rounded-full bg-[var(--soft-panel)] px-3 py-1 text-[11px] font-black text-[var(--text-muted)]">
          {selectedApp.status}
        </span>
      </div>

      {/* Tab switcher */}
      <div className="mt-4 flex rounded-full border border-[var(--glass-border)] bg-[var(--segmented-bg)] p-1">
        {['resume', 'cover_letter'].map((tab) => (
          <button
            className={`h-8 flex-1 rounded-full text-xs font-black transition ${contentTab === tab
              ? 'bg-[var(--segmented-active)] text-[var(--active-text)] shadow-sm'
              : 'text-[var(--text-muted)]'}`}
            key={tab}
            onClick={() => setContentTab(tab)}
            type="button"
          >
            {tab === 'resume' ? 'Resume' : 'Cover Letter'}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="mt-4 max-h-[380px] overflow-y-auto rounded-2xl bg-[var(--soft-panel)] p-5">
        {contentTab === 'resume' && resume && (
          <div>
            <p className="text-xs font-black uppercase text-[var(--text-muted)]">Summary</p>
            <p className="mt-1 text-sm font-semibold leading-6 text-[var(--text-primary)]">{resume.summary}</p>
            <p className="mt-4 text-xs font-black uppercase text-[var(--text-muted)]">Skills</p>
            <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">{resume.skills_section}</p>
            <p className="mt-4 text-xs font-black uppercase text-[var(--text-muted)]">Experience</p>
            <pre className="mt-1 whitespace-pre-wrap text-sm font-semibold leading-6 text-[var(--text-primary)]">{resume.experience_section}</pre>
          </div>
        )}
        {contentTab === 'cover_letter' && coverLetter && (
          <div>
            <p className="text-sm font-bold text-[var(--text-primary)]">{coverLetter.greeting}</p>
            <p className="mt-3 whitespace-pre-wrap text-sm font-semibold leading-7 text-[var(--text-primary)]">{coverLetter.body}</p>
            <p className="mt-3 text-sm font-bold text-[var(--text-primary)]">{coverLetter.closing}</p>
          </div>
        )}
      </div>
    </GlassPanel>
  )
}
