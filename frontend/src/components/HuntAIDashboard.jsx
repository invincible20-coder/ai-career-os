import { useEffect, useState } from 'react'
import { useHuntStore } from '../store/useHuntStore'

import Sidebar from './Sidebar'
import TopHeader from './TopHeader'
import GoalInputPanel from './GoalInputPanel'
import WorkflowPanel from './WorkflowPanel'
import JobMatchSection from './JobMatchSection'
import SummaryPanel from './SummaryPanel'
import LiveActivityPanel from './LiveActivityPanel'
import ResumeAnalysisPanel from './ResumeAnalysisPanel'

function resolveSystemTheme() {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function HuntAIDashboard() {
  const [themeMode, setThemeMode] = useState('Light')
  const [systemTheme, setSystemTheme] = useState(resolveSystemTheme)

  const checkHealth = useHuntStore((s) => s.checkHealth)
  const fetchAnalytics = useHuntStore((s) => s.fetchAnalytics)

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const updateTheme = () => setSystemTheme(mediaQuery.matches ? 'dark' : 'light')
    updateTheme()
    mediaQuery.addEventListener('change', updateTheme)
    return () => mediaQuery.removeEventListener('change', updateTheme)
  }, [])

  // Check backend health on mount
  useEffect(() => {
    checkHealth()
    fetchAnalytics()
  }, [checkHealth, fetchAnalytics])

  const resolvedTheme =
    themeMode === 'System' ? systemTheme : themeMode.toLowerCase()

  return (
    <div
      className="min-h-screen bg-[var(--page-bg)] text-[var(--text-primary)] transition-colors duration-300"
      data-theme={resolvedTheme}
    >
      <div className="min-h-screen bg-[linear-gradient(135deg,var(--wash-a),var(--wash-b)_44%,var(--wash-c))]">
        <div className="mx-auto grid min-h-screen max-w-[1600px] grid-cols-[280px_minmax(0,1fr)] gap-6 px-6 py-6 max-xl:grid-cols-[244px_minmax(0,1fr)] max-lg:grid-cols-1 max-sm:px-4 max-sm:py-4">
          <Sidebar />

          <div className="grid min-w-0 grid-rows-[auto_minmax(0,1fr)] gap-6">
            <TopHeader themeMode={themeMode} onThemeChange={setThemeMode} />

            <main className="grid min-w-0 grid-cols-[minmax(0,1fr)_360px] gap-6 max-xl:grid-cols-[minmax(0,1fr)_326px] max-lg:grid-cols-1">
              <section className="grid min-w-0 content-start gap-6">
                <GoalInputPanel />
                <WorkflowPanel />

                <div className="grid grid-cols-[minmax(0,1.2fr)_minmax(300px,0.8fr)] gap-6 max-xl:grid-cols-1">
                  <JobMatchSection />
                  <SummaryPanel />
                </div>
              </section>

              <aside className="grid content-start gap-6">
                <LiveActivityPanel />
                <ResumeAnalysisPanel />
              </aside>
            </main>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HuntAIDashboard
