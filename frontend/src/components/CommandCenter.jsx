import { useEffect, useMemo } from 'react'
import { API_BASE_URL } from '../api/client'
import { parseList, useHuntStore } from '../store/useHuntStore'

const STEP_ORDER = ['plan', 'search', 'apply', 'track']

const STEP_META = {
  plan: {
    idleLabel: 'Plan Queued',
    runningLabel: 'Generating Plan',
    doneLabel: 'Plan Generated',
    agent: 'Planner Agent',
  },
  search: {
    idleLabel: 'Jobs Queued',
    runningLabel: 'Fetching Jobs',
    doneLabel: 'Jobs Fetched',
    agent: 'Job Finder Agent',
  },
  apply: {
    idleLabel: 'Applications Queued',
    runningLabel: 'Generating Resumes',
    doneLabel: 'Applications Prepared',
    agent: 'Resume Agent',
  },
  track: {
    idleLabel: 'Tracking Queued',
    runningLabel: 'Tracking Results',
    doneLabel: 'Tracking Synced',
    agent: 'Tracker Agent',
  },
}

function formatDateTime(value) {
  if (!value) {
    return 'pending'
  }

  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(value))
}

function formatPercent(value) {
  const normalized = Number.isFinite(value) ? value : 0
  return `${Math.round(normalized * 100)}%`
}

function humanize(value) {
  return String(value ?? '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function getStepCount(step, jobs, applications, tracker) {
  if (step === 'search') {
    return jobs.length
  }

  if (step === 'apply') {
    return applications.length
  }

  if (step === 'track') {
    return tracker.length || applications.length
  }

  return 0
}

function buildTimeline({
  huntResult,
  jobs,
  applications,
  activeAction,
}) {
  const progressByStep = new Map(
    huntResult?.progress?.map((entry) => [entry.step, entry]) ?? [],
  )
  const planByStep = new Map(
    huntResult?.plan?.steps?.map((entry) => [entry.step_type, entry]) ?? [],
  )
  const tracker = huntResult?.tracker ?? []

  const items = STEP_ORDER.map((step, index) => {
    const meta = STEP_META[step]
    const progress = progressByStep.get(step)
    const count = getStepCount(step, jobs, applications, tracker)
    const planStep = planByStep.get(step)
    const failed = progress?.status === 'failed'
    const completedByData =
      (step === 'plan' && Boolean(huntResult?.plan)) ||
      (step === 'search' && jobs.length > 0) ||
      (step === 'apply' && applications.length > 0) ||
      (step === 'track' && huntResult?.status === 'completed')

    let status = progress?.status ?? (completedByData ? 'completed' : 'pending')

    if (!huntResult && activeAction === 'hunt' && index === 0) {
      status = 'running'
    }

    if (huntResult?.status === 'running' && status === 'pending') {
      const firstPending = STEP_ORDER.find(
        (candidate) => !progressByStep.has(candidate),
      )
      if (firstPending === step) {
        status = 'running'
      }
    }

    const label =
      status === 'completed'
        ? meta.doneLabel
        : status === 'running'
          ? meta.runningLabel
          : meta.idleLabel
    const countLabel = count ? ` (${count})` : ''

    return {
      step,
      agent: meta.agent,
      label: `${label}${countLabel}`,
      status: failed ? 'failed' : status,
      description:
        planStep?.description ??
        (activeAction === 'hunt' && index === 0
          ? 'POST /hunts is executing. Waiting for the first persisted snapshot.'
          : 'Waiting for backend progress.'),
      attempts: progress?.attempt_count ?? 0,
      latency: progress?.latency_ms ?? null,
      updatedAt: progress?.updated_at,
      errors: progress?.last_errors ?? [],
    }
  })

  const completed = items.filter((item) => item.status === 'completed').length
  const running = items.some((item) => item.status === 'running') ? 0.5 : 0
  const progress = Math.min(100, Math.round(((completed + running) / items.length) * 100))

  return { items, progress, completed }
}

function getActiveStep(timeline, activeAction, requestPhase) {
  const failed = timeline.items.find((item) => item.status === 'failed')
  if (failed) {
    return failed
  }

  const running = timeline.items.find((item) => item.status === 'running')
  if (running) {
    return running
  }

  if (activeAction === 'recommend') {
    return {
      label: 'Recommendation Running',
      agent: 'Career Advisor Agent',
      status: 'running',
      description: 'POST /recommend-career is analyzing the profile.',
    }
  }

  const lastDone = [...timeline.items]
    .reverse()
    .find((item) => item.status === 'completed')

  if (lastDone) {
    return lastDone
  }

  return {
    label: requestPhase === 'failed' ? 'Attention Needed' : 'Standing By',
    agent: 'Orchestrator',
    status: requestPhase === 'failed' ? 'failed' : 'pending',
    description: 'Awaiting a goal, recommendation, or hunt launch.',
  }
}

function statusForJob(job, applications) {
  const app = applications.find((application) => application.job_id === job.job_id)
  if (!app) {
    return 'pending'
  }
  if (app.status === 'submitted') {
    return 'applied'
  }
  if (app.status === 'failed') {
    return 'failed'
  }
  return 'prepared'
}

function textFromApplication(application, tab) {
  if (!application) {
    return ''
  }

  if (tab === 'cover') {
    const letter = application.cover_letter
    return (
      letter?.full_text ||
      [letter?.greeting, letter?.body, letter?.closing].filter(Boolean).join('\n\n')
    )
  }

  const resume = application.resume
  return (
    resume?.full_text ||
    [resume?.summary, resume?.skills_section, resume?.experience_section]
      .filter(Boolean)
      .join('\n\n')
  )
}

function CommandCenter() {
  const {
    form,
    presets,
    serverState,
    activeAction,
    requestPhase,
    careerResult,
    huntResult,
    huntId,
    jobs,
    applications,
    analytics,
    selectedJobId,
    contentTab,
    jobFilter,
    errorMessage,
    pollError,
    isPolling,
    logs,
    setField,
    applyPreset,
    resetCommandCenter,
    setJobFilter,
    selectJob,
    setContentTab,
    checkHealth,
    fetchAnalytics,
    recommendCareer,
    startHunt,
    useRoleAndStart,
    refreshHunt,
    clearError,
  } = useHuntStore()

  useEffect(() => {
    checkHealth()
    fetchAnalytics()
  }, [checkHealth, fetchAnalytics])

  useEffect(() => {
    if (!huntId || !isPolling) {
      return undefined
    }

    const intervalId = window.setInterval(() => {
      refreshHunt()
    }, 1800)

    return () => window.clearInterval(intervalId)
  }, [huntId, isPolling, refreshHunt])

  const timeline = useMemo(
    () =>
      buildTimeline({
        huntResult,
        jobs,
        applications,
        activeAction,
      }),
    [activeAction, applications, huntResult, jobs],
  )
  const activeStep = getActiveStep(timeline, activeAction, requestPhase)
  const recommendedRoles = careerResult?.recommended_roles ?? []
  const trackerRows = useMemo(
    () => buildTrackerRows(jobs, applications, huntResult?.tracker ?? []),
    [applications, huntResult?.tracker, jobs],
  )
  const filteredJobs = useMemo(
    () => filterJobs(jobs, applications, jobFilter),
    [applications, jobFilter, jobs],
  )
  const selectedJob = jobs.find((job) => job.job_id === selectedJobId) ?? jobs[0]
  const selectedApplication =
    applications.find((application) => application.job_id === selectedJob?.job_id) ??
    applications[0]
  const successRate = analytics?.metrics?.success_rate ?? 0
  const summary = {
    totalJobs: huntResult?.summary?.total_jobs ?? jobs.length,
    applicationsCreated:
      huntResult?.summary?.total_applications ?? applications.length,
    successRate,
    status: huntResult?.status ?? requestPhase,
  }
  const busy = Boolean(activeAction)

  return (
    <main className="command-shell">
      <SystemHeader serverState={serverState} huntId={huntId} />

      <section className="command-grid">
        <div className="left-column">
          <GoalInputPanel
            form={form}
            presets={presets}
            busy={busy}
            activeAction={activeAction}
            onFieldChange={setField}
            onApplyPreset={applyPreset}
            onReset={resetCommandCenter}
            onRecommend={recommendCareer}
            onStartHunt={() => startHunt()}
          />

          <CareerRecommendationPanel
            roles={recommendedRoles}
            busy={busy}
            onUseRole={useRoleAndStart}
          />
        </div>

        <div className="center-column">
          <ExecutionTimeline timeline={timeline} />
          <LiveStatusPanel
            activeStep={activeStep}
            logs={logs}
            huntId={huntId}
            isPolling={isPolling}
            requestPhase={requestPhase}
            onRefresh={refreshHunt}
          />
          <JobResultsPanel
            jobs={filteredJobs}
            allJobsCount={jobs.length}
            applications={applications}
            filter={jobFilter}
            selectedJobId={selectedJobId}
            onFilterChange={setJobFilter}
            onSelectJob={selectJob}
          />
        </div>

        <div className="right-column">
          <SummaryPanel
            summary={summary}
            analytics={analytics}
            timeline={timeline}
          />

          <GeneratedContentViewer
            jobs={jobs}
            selectedJob={selectedJob}
            application={selectedApplication}
            selectedJobId={selectedJobId}
            tab={contentTab}
            onSelectJob={selectJob}
            onTabChange={setContentTab}
          />

          <ApplicationTracker rows={trackerRows} />
        </div>
      </section>

      <ErrorPanel
        apiError={errorMessage}
        pollError={pollError}
        backendErrors={huntResult?.errors ?? []}
        onRetry={huntId ? refreshHunt : null}
        onClear={clearError}
      />
    </main>
  )
}

function SystemHeader({ serverState, huntId }) {
  return (
    <header className="system-header">
      <div className="identity">
        <span className="identity-mark">AJ</span>
        <div>
          <p className="eyebrow">Autonomous Job Hunt AI Agent</p>
          <h1>Command Center</h1>
        </div>
      </div>

      <div className="header-status">
        <span className={`server-pill server-pill--${serverState.tone}`}>
          {serverState.label}
        </span>
        <span className="api-pill">{API_BASE_URL}</span>
        {huntId ? <span className="hunt-pill">{huntId}</span> : null}
      </div>
    </header>
  )
}

function GoalInputPanel({
  form,
  presets,
  busy,
  activeAction,
  onFieldChange,
  onApplyPreset,
  onReset,
  onRecommend,
  onStartHunt,
}) {
  const skills = parseList(form.skills)
  const interests = parseList(form.interests)
  const profileSignal = Math.min(
    100,
    20 +
      [form.goal, form.education, form.experience].filter((value) => value.trim())
        .length *
        12 +
      skills.length * 5 +
      interests.length * 4,
  )

  return (
    <section className="panel input-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Goal Input Panel</p>
          <h2>Mission Parameters</h2>
        </div>
        <div className="signal-meter" aria-label={`Profile signal ${profileSignal}%`}>
          <span style={{ width: `${profileSignal}%` }} />
        </div>
      </div>

      <div className="preset-row">
        {presets.map((preset) => (
          <button
            className="preset-button"
            key={preset.label}
            type="button"
            onClick={() => onApplyPreset(preset)}
            disabled={busy}
          >
            <strong>{preset.label}</strong>
            <span>{preset.sublabel}</span>
          </button>
        ))}
      </div>

      <form
        className="goal-form"
        onSubmit={(event) => {
          event.preventDefault()
          onStartHunt()
        }}
      >
        <label className="field">
          <span>Target role</span>
          <input
            name="goal"
            value={form.goal}
            onChange={(event) => onFieldChange('goal', event.target.value)}
            placeholder="Backend Engineer, Product Engineer, or not sure"
            disabled={busy}
          />
        </label>

        <div className="field-pair">
          <label className="field">
            <span>Skills</span>
            <textarea
              name="skills"
              value={form.skills}
              onChange={(event) => onFieldChange('skills', event.target.value)}
              rows={4}
              placeholder="Python, FastAPI, React, SQL"
              disabled={busy}
            />
          </label>

          <label className="field">
            <span>Interests</span>
            <textarea
              name="interests"
              value={form.interests}
              onChange={(event) => onFieldChange('interests', event.target.value)}
              rows={4}
              placeholder="automation, systems, product UX"
              disabled={busy}
            />
          </label>
        </div>

        <label className="field">
          <span>Education</span>
          <input
            name="education"
            value={form.education}
            onChange={(event) => onFieldChange('education', event.target.value)}
            placeholder="Degree, bootcamp, or certification"
            disabled={busy}
          />
        </label>

        <label className="field">
          <span>Experience</span>
          <textarea
            name="experience"
            value={form.experience}
            onChange={(event) => onFieldChange('experience', event.target.value)}
            rows={4}
            placeholder="Projects, internships, shipped tools, responsibilities"
            disabled={busy}
          />
        </label>

        <div className="button-row">
          <button
            className="primary-button"
            type="submit"
            disabled={busy}
          >
            {activeAction === 'hunt' ? <span className="spinner" /> : null}
            {activeAction === 'hunt' ? 'Running Hunt' : 'Start Hunt'}
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={onRecommend}
            disabled={busy}
          >
            {activeAction === 'recommend' ? <span className="spinner" /> : null}
            {activeAction === 'recommend' ? 'Analyzing' : 'Recommend Career'}
          </button>
          <button
            className="ghost-button"
            type="button"
            onClick={onReset}
            disabled={busy}
          >
            Reset
          </button>
        </div>
      </form>
    </section>
  )
}

function CareerRecommendationPanel({ roles, busy, onUseRole }) {
  return (
    <section className="panel recommendations-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Career Recommendation Panel</p>
          <h2>Role Vectors</h2>
        </div>
        <span className="count-pill">{roles.length}</span>
      </div>

      <div className="recommendation-list">
        {roles.length ? (
          roles.map((role) => (
            <article className="recommendation-card" key={role.role}>
              <div>
                <h3>{role.role}</h3>
                <p>{role.reason}</p>
              </div>
              <div className="skill-stack">
                {role.required_skills?.slice(0, 5).map((skill) => (
                  <span className="skill-chip" key={skill}>
                    {skill}
                  </span>
                ))}
              </div>
              <button
                className="small-button"
                type="button"
                onClick={() => onUseRole(role.role)}
                disabled={busy}
              >
                Use this role
              </button>
            </article>
          ))
        ) : (
          <div className="empty-box">
            <strong>No recommendations yet</strong>
            <span>Run the career advisor to populate this panel.</span>
          </div>
        )}
      </div>
    </section>
  )
}

function ExecutionTimeline({ timeline }) {
  return (
    <section className="panel timeline-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Agent Execution Timeline</p>
          <h2>Backend Workflow</h2>
        </div>
        <span className="progress-number">{timeline.progress}%</span>
      </div>

      <div className="progress-track">
        <span style={{ width: `${timeline.progress}%` }} />
      </div>

      <div className="timeline-list">
        {timeline.items.map((item) => (
          <article
            className={`timeline-item timeline-item--${item.status}`}
            key={item.step}
          >
            <span className="step-marker">{markerForStatus(item.status)}</span>
            <div className="timeline-copy">
              <div className="timeline-title">
                <h3>{item.label}</h3>
                <span>{item.agent}</span>
              </div>
              <p>{item.description}</p>
              <div className="step-meta">
                <span>Attempts {item.attempts}</span>
                <span>{item.latency ? `${item.latency}ms` : 'latency pending'}</span>
                <span>{formatDateTime(item.updatedAt)}</span>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

function markerForStatus(status) {
  if (status === 'completed') {
    return 'OK'
  }
  if (status === 'running') {
    return 'RUN'
  }
  if (status === 'failed') {
    return 'ERR'
  }
  return 'WAIT'
}

function LiveStatusPanel({
  activeStep,
  logs,
  huntId,
  isPolling,
  requestPhase,
  onRefresh,
}) {
  return (
    <section className="panel live-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Live Status Stream</p>
          <h2>{activeStep.label}</h2>
        </div>
        <span className={`status-dot status-dot--${activeStep.status}`} />
      </div>

      <div className="active-agent">
        <span>Active agent</span>
        <strong>{activeStep.agent}</strong>
        <p>{activeStep.description}</p>
      </div>

      <div className="stream-controls">
        <span className="stream-state">
          {isPolling ? 'Polling live endpoints' : humanize(requestPhase)}
        </span>
        <button
          className="small-button small-button--quiet"
          type="button"
          onClick={onRefresh}
          disabled={!huntId}
        >
          Refresh
        </button>
      </div>

      <div className="log-stream" role="log" aria-live="polite">
        {logs.map((log) => (
          <div className={`log-line log-line--${log.level}`} key={log.id}>
            <time>{formatDateTime(log.at)}</time>
            <span>{log.message}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

function JobResultsPanel({
  jobs,
  allJobsCount,
  applications,
  filter,
  selectedJobId,
  onFilterChange,
  onSelectJob,
}) {
  return (
    <section className="panel jobs-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Job Results Panel</p>
          <h2>Opportunities</h2>
        </div>
        <span className="count-pill">{jobs.length}/{allJobsCount}</span>
      </div>

      <label className="filter-field">
        <span>Filter jobs</span>
        <input
          value={filter}
          onChange={(event) => onFilterChange(event.target.value)}
          placeholder="Company, role, location, skill"
        />
      </label>

      <div className="job-card-list">
        {jobs.length ? (
          jobs.map((job) => {
            const status = statusForJob(job, applications)
            const selected = job.job_id === selectedJobId

            return (
              <article
                className={`job-card ${selected ? 'job-card--selected' : ''}`}
                key={job.job_id}
              >
                <button
                  className="job-select"
                  type="button"
                  onClick={() => onSelectJob(job.job_id)}
                >
                  <span className={`job-status job-status--${status}`}>
                    {status}
                  </span>
                  <strong>{job.title}</strong>
                  <span>{job.company}</span>
                  <small>{job.location}</small>
                </button>
                <div className="skill-stack">
                  {job.requirements?.slice(0, 4).map((skill) => (
                    <span className="skill-chip" key={skill}>
                      {skill}
                    </span>
                  ))}
                </div>
                <div className="job-footer">
                  <span>{job.source}</span>
                  {job.url ? (
                    <a href={job.url} target="_blank" rel="noreferrer">
                      Apply Link
                    </a>
                  ) : (
                    <span>No link</span>
                  )}
                </div>
              </article>
            )
          })
        ) : (
          <div className="empty-box">
            <strong>No jobs in view</strong>
            <span>Run a hunt or adjust the filter.</span>
          </div>
        )}
      </div>
    </section>
  )
}

function SummaryPanel({ summary, analytics, timeline }) {
  return (
    <section className="panel summary-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Summary Panel</p>
          <h2>Run Metrics</h2>
        </div>
        <span className="status-chip">{humanize(summary.status)}</span>
      </div>

      <div className="summary-grid">
        <MetricCard label="Total jobs" value={summary.totalJobs} />
        <MetricCard label="Applications" value={summary.applicationsCreated} />
        <MetricCard label="Success rate" value={formatPercent(summary.successRate)} />
        <MetricCard
          label="Completed steps"
          value={`${timeline.completed}/${timeline.items.length}`}
        />
      </div>

      <div className="analytics-strip">
        <span>Behavior class</span>
        <strong>{humanize(analytics?.classification ?? 'insufficient_data')}</strong>
        <small>
          {analytics?.metrics?.total_applications ?? 0} applications in the window
        </small>
      </div>
    </section>
  )
}

function MetricCard({ label, value }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  )
}

function GeneratedContentViewer({
  jobs,
  selectedJob,
  application,
  selectedJobId,
  tab,
  onSelectJob,
  onTabChange,
}) {
  const documentText = textFromApplication(application, tab)

  return (
    <section className="panel content-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Generated Content Viewer</p>
          <h2>Application Drafts</h2>
        </div>
      </div>

      <div className="viewer-toolbar">
        <select
          value={selectedJobId}
          onChange={(event) => onSelectJob(event.target.value)}
          disabled={!jobs.length}
        >
          {jobs.length ? (
            jobs.map((job) => (
              <option key={job.job_id} value={job.job_id}>
                {job.title} - {job.company}
              </option>
            ))
          ) : (
            <option value="">No jobs yet</option>
          )}
        </select>
        <div className="tab-row" role="tablist" aria-label="Generated content">
          <button
            className={tab === 'resume' ? 'tab-button tab-button--active' : 'tab-button'}
            type="button"
            onClick={() => onTabChange('resume')}
          >
            Resume
          </button>
          <button
            className={tab === 'cover' ? 'tab-button tab-button--active' : 'tab-button'}
            type="button"
            onClick={() => onTabChange('cover')}
          >
            Cover Letter
          </button>
        </div>
      </div>

      <div className="document-shell">
        {documentText ? (
          <>
            <div className="document-heading">
              <strong>{selectedJob?.title ?? application?.job_title}</strong>
              <span>{selectedJob?.company ?? application?.company}</span>
            </div>
            <div className="document-body">{documentText}</div>
          </>
        ) : (
          <div className="empty-box">
            <strong>No generated draft selected</strong>
            <span>Prepared resumes and cover letters appear here by job.</span>
          </div>
        )}
      </div>
    </section>
  )
}

function ApplicationTracker({ rows }) {
  return (
    <section className="panel tracker-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Application Tracker</p>
          <h2>Status Table</h2>
        </div>
        <span className="count-pill">{rows.length}</span>
      </div>

      <div className="tracker-table" role="table" aria-label="Application tracker">
        <div className="tracker-row tracker-row--head" role="row">
          <span role="columnheader">Job</span>
          <span role="columnheader">Company</span>
          <span role="columnheader">Status</span>
          <span role="columnheader">Time</span>
        </div>
        {rows.length ? (
          rows.map((row) => (
            <div className="tracker-row" role="row" key={row.id}>
              <span role="cell">{row.job}</span>
              <span role="cell">{row.company}</span>
              <span role="cell">
                <span className={`job-status job-status--${row.status}`}>
                  {row.status}
                </span>
              </span>
              <time role="cell">{formatDateTime(row.time)}</time>
            </div>
          ))
        ) : (
          <div className="empty-box empty-box--table">
            <strong>No tracker rows</strong>
            <span>Application status will update from the backend.</span>
          </div>
        )}
      </div>
    </section>
  )
}

function ErrorPanel({ apiError, pollError, backendErrors, onRetry, onClear }) {
  const hasError = apiError || pollError || backendErrors.length > 0

  if (!hasError) {
    return null
  }

  return (
    <aside className="error-panel" role="alert">
      <div>
        <p className="eyebrow">Error Handling UI</p>
        <h2>Backend Attention Required</h2>
      </div>
      <div className="error-list">
        {apiError ? <p>{apiError}</p> : null}
        {pollError ? <p>{pollError}</p> : null}
        {backendErrors.map((error) => (
          <p key={`${error.code}-${error.step}-${error.message}`}>
            <strong>{error.code}</strong> {error.step ? `at ${error.step}: ` : ''}
            {error.message}
          </p>
        ))}
      </div>
      <div className="button-row button-row--compact">
        {onRetry ? (
          <button className="secondary-button" type="button" onClick={onRetry}>
            Retry Poll
          </button>
        ) : null}
        <button className="ghost-button" type="button" onClick={onClear}>
          Dismiss
        </button>
      </div>
    </aside>
  )
}

function filterJobs(jobs, applications, filter) {
  const query = filter.trim().toLowerCase()
  if (!query) {
    return jobs
  }

  return jobs.filter((job) => {
    const status = statusForJob(job, applications)
    const haystack = [
      job.title,
      job.company,
      job.location,
      job.source,
      status,
      ...(job.requirements ?? []),
    ]
      .join(' ')
      .toLowerCase()

    return haystack.includes(query)
  })
}

function buildTrackerRows(jobs, applications, tracker) {
  if (tracker.length) {
    return tracker.map((entry) => ({
      id: entry.application_id,
      job: entry.job_title,
      company: entry.company,
      status: normalizeTrackerStatus(entry.status),
      time: entry.submitted_at ?? entry.created_at,
    }))
  }

  const rows = jobs.map((job) => {
    const application = applications.find((app) => app.job_id === job.job_id)

    return {
      id: application?.application_id ?? job.job_id,
      job: job.title,
      company: job.company,
      status: application ? normalizeTrackerStatus(application.status) : 'pending',
      time: application?.submitted_at ?? application?.created_at ?? job.scraped_at,
    }
  })

  applications.forEach((application) => {
    if (!rows.some((row) => row.id === application.application_id)) {
      rows.push({
        id: application.application_id,
        job: application.job_title,
        company: application.company,
        status: normalizeTrackerStatus(application.status),
        time: application.submitted_at ?? application.created_at,
      })
    }
  })

  return rows
}

function normalizeTrackerStatus(status) {
  if (status === 'submitted') {
    return 'applied'
  }
  if (status === 'prepared') {
    return 'prepared'
  }
  if (status === 'failed') {
    return 'failed'
  }
  return 'pending'
}

export default CommandCenter
