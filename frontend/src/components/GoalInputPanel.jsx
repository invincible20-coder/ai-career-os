import { useHuntStore } from '../store/useHuntStore'
import GlassPanel from './GlassPanel'

export default function GoalInputPanel() {
  const form = useHuntStore((s) => s.form)
  const setField = useHuntStore((s) => s.setField)
  const startHunt = useHuntStore((s) => s.startHunt)
  const recommendCareer = useHuntStore((s) => s.recommendCareer)
  const activeAction = useHuntStore((s) => s.activeAction)
  const requestPhase = useHuntStore((s) => s.requestPhase)
  const errorMessage = useHuntStore((s) => s.errorMessage)
  const presets = useHuntStore((s) => s.presets)
  const applyPreset = useHuntStore((s) => s.applyPreset)
  const resetCommandCenter = useHuntStore((s) => s.resetCommandCenter)

  const isBusy = !!activeAction

  return (
    <GlassPanel className="p-7 max-sm:p-5">
      <div className="max-w-[780px]">
        <h2 className="text-[32px] font-black leading-tight tracking-[-0.035em] text-[var(--text-primary)] max-sm:text-2xl">
          What's your career goal?
        </h2>
        <p className="mt-3 max-w-[690px] text-[15px] font-semibold leading-7 text-[var(--text-muted)]">
          Tell me anything about your skills, interests, experience, or the kind
          of role you want.
          <br />
          The more you share, the better I can plan for you.
        </p>
      </div>

      <textarea
        className="mt-6 h-[140px] w-full resize-none rounded-[28px] border border-[var(--input-border)] bg-[var(--input-bg)] p-6 text-[16px] font-semibold leading-8 text-[var(--text-primary)] shadow-[inset_0_1px_0_rgba(255,255,255,0.55),0_18px_42px_rgba(109,132,168,0.08)] outline-none placeholder:text-[var(--text-muted)]/60 focus:border-[#6ca7ff]"
        disabled={isBusy}
        onChange={(e) => setField('goal', e.target.value)}
        placeholder='e.g. "Backend Engineer at a product company" or "not sure, help me decide"'
        value={form.goal}
      />

      {/* Extra fields row */}
      <div className="mt-4 grid grid-cols-2 gap-3 max-sm:grid-cols-1">
        <input
          className="h-12 rounded-2xl border border-[var(--input-border)] bg-[var(--input-bg)] px-5 text-sm font-semibold text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)]/60 focus:border-[#6ca7ff]"
          disabled={isBusy}
          onChange={(e) => setField('skills', e.target.value)}
          placeholder="Skills (e.g. Python, FastAPI, SQL)"
          value={form.skills}
        />
        <input
          className="h-12 rounded-2xl border border-[var(--input-border)] bg-[var(--input-bg)] px-5 text-sm font-semibold text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)]/60 focus:border-[#6ca7ff]"
          disabled={isBusy}
          onChange={(e) => setField('interests', e.target.value)}
          placeholder="Interests (e.g. distributed systems, tooling)"
          value={form.interests}
        />
        <input
          className="h-12 rounded-2xl border border-[var(--input-border)] bg-[var(--input-bg)] px-5 text-sm font-semibold text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)]/60 focus:border-[#6ca7ff]"
          disabled={isBusy}
          onChange={(e) => setField('education', e.target.value)}
          placeholder="Education (e.g. B.Tech CS)"
          value={form.education}
        />
        <input
          className="h-12 rounded-2xl border border-[var(--input-border)] bg-[var(--input-bg)] px-5 text-sm font-semibold text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)]/60 focus:border-[#6ca7ff]"
          disabled={isBusy}
          onChange={(e) => setField('experience', e.target.value)}
          placeholder="Experience (e.g. Built APIs, worked on backends)"
          value={form.experience}
        />
      </div>

      {/* Presets */}
      <div className="mt-5 flex flex-wrap gap-3">
        {presets.map((preset) => (
          <button
            className="h-10 rounded-full border border-[var(--chip-border)] bg-[var(--chip-bg)] px-4 text-sm font-black text-[var(--text-primary)] shadow-[0_10px_22px_rgba(111,132,163,0.08)] transition hover:scale-[1.03] disabled:opacity-50"
            disabled={isBusy}
            key={preset.label}
            onClick={() => applyPreset(preset)}
            type="button"
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* Error display */}
      {errorMessage && (
        <div className="mt-4 rounded-2xl border border-red-300/30 bg-red-500/10 px-5 py-3 text-sm font-bold text-red-400">
          {errorMessage}
        </div>
      )}

      {/* Actions */}
      <div className="mt-7 flex items-center justify-between gap-4 max-sm:flex-col max-sm:items-stretch">
        <div className="flex items-center gap-3">
          <p className="text-sm font-semibold text-[var(--text-muted)]">
            Your data is private and never shared.
          </p>
          {requestPhase !== 'idle' && (
            <button
              className="text-sm font-bold text-[var(--text-muted)] underline"
              onClick={resetCommandCenter}
              type="button"
            >
              Reset
            </button>
          )}
        </div>
        <div className="flex gap-3">
          <button
            className="h-14 rounded-full border border-[var(--glass-border)] bg-[var(--soft-panel)] px-6 text-[14px] font-black text-[var(--text-primary)] transition hover:scale-[1.02] disabled:opacity-50"
            disabled={isBusy}
            onClick={() => recommendCareer()}
            type="button"
          >
            {activeAction === 'recommend' ? 'Recommending…' : 'Suggest Roles'}
          </button>
          <button
            className="h-14 rounded-full bg-[linear-gradient(135deg,#6ca7ff,#aee9c8)] px-8 text-[15px] font-black text-[#173453] shadow-[0_18px_35px_rgba(92,138,202,0.24)] transition hover:scale-[1.02] disabled:opacity-50"
            disabled={isBusy || !form.goal.trim()}
            onClick={() => startHunt()}
            type="button"
          >
            {activeAction === 'hunt' ? '🔄 Hunting…' : '🚀 Start Autonomous Hunt'}
          </button>
        </div>
      </div>
    </GlassPanel>
  )
}
