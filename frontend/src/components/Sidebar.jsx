import { useHuntStore } from '../store/useHuntStore'

const navigationItems = [
  'Command Center',
  'Recommendations',
  'Hunt Missions',
  'Applications',
  'Resumes & Letters',
  'Analytics',
  'Profile & Behavior',
  'Strategy Advisor',
  'Settings',
]

export default function Sidebar() {
  const serverState = useHuntStore((s) => s.serverState)

  return (
    <aside className="sticky top-6 grid h-[calc(100vh-48px)] content-between overflow-hidden rounded-[34px] border border-[var(--glass-border)] bg-[var(--sidebar-bg)] p-5 shadow-[var(--glass-shadow)] backdrop-blur-[10px] max-lg:static max-lg:h-auto">
      <div>
        <div className="mb-7 flex items-center gap-3">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-[linear-gradient(135deg,#8cc8ff,#c9f4dc_55%,#ffd8c6)] text-base font-black text-[#24445e] shadow-[0_16px_32px_rgba(110,145,190,0.2)]">
            HA
          </div>
          <div>
            <p className="text-[15px] font-black tracking-[-0.01em] text-[var(--text-primary)]">
              HuntAI
            </p>
            <p className="text-xs font-semibold text-[var(--text-muted)]">
              Autonomous Job Hunt Agent
            </p>
          </div>
        </div>

        <nav className="grid gap-2">
          {navigationItems.map((item) => (
            <button
              className={`flex min-h-11 items-center rounded-2xl px-4 text-left text-[14px] font-bold transition ${item === 'Command Center'
                ? 'bg-[var(--active-nav)] text-[var(--active-text)] shadow-[0_14px_30px_rgba(84,118,168,0.18)]'
                : 'text-[var(--text-muted)] hover:bg-[var(--nav-hover)] hover:text-[var(--text-primary)]'
                }`}
              key={item}
              type="button"
            >
              {item}
            </button>
          ))}
        </nav>
      </div>

      <div className="grid gap-4 pt-6">
        <div className="rounded-[26px] border border-[var(--glass-border)] bg-[linear-gradient(135deg,var(--plan-a),var(--plan-b))] p-4 shadow-[0_18px_40px_rgba(115,144,190,0.14)]">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-black text-[var(--text-primary)]">Pro Plan</p>
            <span className="rounded-full bg-white/55 px-3 py-1 text-[11px] font-black text-[#4f75a0]">
              Active
            </span>
          </div>
          <p className="mt-2 text-xs font-semibold text-[var(--text-muted)]">
            6 agents working for you
          </p>
        </div>

        <div className="rounded-[24px] bg-[var(--soft-panel)] p-4">
          <p className="text-sm font-black text-[var(--text-primary)]">Swaransh</p>
          <p className="mt-1 text-xs font-semibold text-[var(--text-muted)]">
            swaransh@example.com
          </p>
        </div>

        <div className="rounded-[24px] border border-[var(--glass-border)] bg-[var(--soft-panel)] p-4">
          <p className="text-xs font-bold uppercase text-[var(--text-muted)]">
            Backend Status
          </p>
          <p className={`mt-1 text-sm font-black ${serverState.tone === 'online' ? 'text-emerald-500' : serverState.tone === 'offline' ? 'text-red-400' : 'text-[var(--text-primary)]'}`}>
            {serverState.label}
          </p>
        </div>
      </div>
    </aside>
  )
}
