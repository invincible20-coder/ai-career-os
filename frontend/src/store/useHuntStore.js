

import { create } from 'zustand'
import {
  createHunt,
  getAnalytics,
  getHealth,
  getHunt,
  getHuntApplications,
  getHuntJobs,
  recommendCareer as requestCareerRecommendation,
} from '../api/client'

export const initialForm = {
  goal: '',
  skills: '',
  interests: '',
  education: '',
  experience: '',
}

export const launchPresets = [
  {
    label: 'Backend Systems',
    sublabel: 'FastAPI, SQL, automation',
    data: {
      goal: 'Backend Engineer',
      skills: 'Python, FastAPI, SQL, REST APIs, automation',
      interests: 'distributed systems, developer tooling, workflow automation',
      education: 'B.Tech in Computer Science',
      experience:
        'Built API projects, database-backed services, and full-stack academic tools.',
    },
  },
  {
    label: 'Product Engineer',
    sublabel: 'React, Node, shipping',
    data: {
      goal: 'Full Stack Software Engineer',
      skills: 'React, JavaScript, Node.js, SQL, UI engineering',
      interests: 'product development, workflow tools, user experience',
      education: 'B.Sc. in Information Technology',
      experience:
        'Created dashboards, product features, and internal workflow tools.',
    },
  },
  {
    label: 'Data Automation',
    sublabel: 'Pipelines, analytics, ETL',
    data: {
      goal: '',
      skills: 'Python, SQL, Pandas, ETL, reporting',
      interests: 'analytics platforms, automation, operational intelligence',
      education: 'Master in Data Science',
      experience:
        'Worked with data analysis, reporting automation, and dashboard generation.',
    },
  },
]

const MAX_LOGS = 80

export function parseList(value) {
  return value
    .split(',')
    .map((entry) => entry.trim())
    .filter(Boolean)
}

function buildPayload(form, { includeGoal = true, goalOverride = null } = {}) {
  const resolvedGoal = goalOverride ?? form.goal
  const payload = {}

  if (includeGoal && resolvedGoal.trim()) {
    payload.goal = resolvedGoal.trim()
  }

  if (form.skills.trim()) {
    payload.skills = parseList(form.skills)
  }

  if (form.interests.trim()) {
    payload.interests = parseList(form.interests)
  }

  if (form.education.trim()) {
    payload.education = form.education.trim()
  }

  if (form.experience.trim()) {
    payload.experience = form.experience.trim()
  }

  return payload
}

function nowIso() {
  return new Date().toISOString()
}

function compactLogs(logs, entry) {
  return [entry, ...logs].slice(0, MAX_LOGS)
}

function getSnapshotSignature(snapshot, jobs, applications) {
  return [
    snapshot?.status ?? 'idle',
    snapshot?.progress?.map((step) => `${step.step}:${step.status}`).join('|') ?? '',
    jobs.length,
    applications.length,
    snapshot?.errors?.length ?? 0,
  ].join('::')
}

function selectedJobFor(jobs, applications, currentSelectedId) {
  if (currentSelectedId && jobs.some((job) => job.job_id === currentSelectedId)) {
    return currentSelectedId
  }

  if (currentSelectedId && applications.some((app) => app.job_id === currentSelectedId)) {
    return currentSelectedId
  }

  return jobs[0]?.job_id ?? applications[0]?.job_id ?? ''
}

export const useHuntStore = create((set, get) => ({
  form: initialForm,
  presets: launchPresets,
  serverState: { label: 'Checking backend', tone: 'checking' },
  activeAction: '',
  requestPhase: 'idle',
  careerResult: null,
  huntResult: null,
  huntId: '',
  jobs: [],
  applications: [],
  analytics: null,
  selectedJobId: '',
  contentTab: 'resume',
  jobFilter: '',
  errorMessage: '',
  pollError: '',
  isPolling: false,
  lastSnapshotSignature: '',
  logs: [
    {
      id: 'boot',
      level: 'info',
      at: nowIso(),
      message: 'Command center initialized.',
    },
  ],

  addLog(level, message) {
    set((state) => ({
      logs: compactLogs(state.logs, {
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        level,
        at: nowIso(),
        message,
      }),
    }))
  },

  setField(name, value) {
    set((state) => ({
      form: { ...state.form, [name]: value },
      errorMessage: '',
    }))
  },

  applyPreset(preset) {
    set({
      form: preset.data,
      errorMessage: '',
      pollError: '',
    })
    get().addLog('info', `Loaded launch profile: ${preset.label}.`)
  },

  resetCommandCenter() {
    set({
      form: initialForm,
      activeAction: '',
      requestPhase: 'idle',
      careerResult: null,
      huntResult: null,
      huntId: '',
      jobs: [],
      applications: [],
      selectedJobId: '',
      contentTab: 'resume',
      jobFilter: '',
      errorMessage: '',
      pollError: '',
      isPolling: false,
      lastSnapshotSignature: '',
    })
    get().addLog('info', 'Workspace reset.')
  },

  setJobFilter(value) {
    set({ jobFilter: value })
  },

  selectJob(jobId) {
    set({ selectedJobId: jobId })
  },

  setContentTab(tab) {
    set({ contentTab: tab })
  },

  clearError() {
    set({ errorMessage: '', pollError: '' })
  },

  async checkHealth() {
    try {
      const health = await getHealth()
      set({
        serverState: {
          label: `Backend live v${health?.version ?? 'unknown'}`,
          tone: 'online',
        },
      })
      get().addLog('success', 'GET /health returned ok.')
    } catch (error) {
      set({
        serverState: { label: 'Backend offline', tone: 'offline' },
      })
      get().addLog(
        'error',
        error instanceof Error ? error.message : 'Health check failed.',
      )
    }
  },

  async fetchAnalytics() {
    try {
      const analytics = await getAnalytics()
      set({ analytics })
    } catch (error) {
      get().addLog(
        'warn',
        error instanceof Error ? error.message : 'Analytics request failed.',
      )
    }
  },

  async recommendCareer() {
    if (get().activeAction) {
      return
    }

    set({
      activeAction: 'recommend',
      requestPhase: 'recommending',
      errorMessage: '',
      pollError: '',
    })
    get().addLog('info', 'POST /recommend-career submitted.')

    try {
      const recommendation = await requestCareerRecommendation(
        buildPayload(get().form, { includeGoal: false }),
      )
      set({
        careerResult: recommendation,
        activeAction: '',
        requestPhase: 'idle',
      })
      get().addLog(
        'success',
        `Career agent returned ${recommendation?.recommended_roles?.length ?? 0
        } role recommendations.`,
      )
    } catch (error) {
      set({
        activeAction: '',
        requestPhase: 'failed',
        errorMessage:
          error instanceof Error
            ? error.message
            : 'Unable to recommend careers.',
      })
      get().addLog(
        'error',
        error instanceof Error ? error.message : 'Career recommendation failed.',
      )
    }
  },

  async startHunt(goalOverride = null) {
    if (get().activeAction) {
      return
    }

    if (goalOverride) {
      set((state) => ({
        form: { ...state.form, goal: goalOverride },
      }))
    }

    set({
      activeAction: 'hunt',
      requestPhase: 'submitting',
      errorMessage: '',
      pollError: '',
      isPolling: false,
    })
    get().addLog('info', 'POST /hunts submitted. Waiting for first hunt snapshot.')

    try {
      const snapshot = await createHunt(
        buildPayload(get().form, { goalOverride }),
      )
      get().hydrateSnapshot(snapshot, 'launch response')
      set({
        activeAction: '',
        requestPhase: snapshot?.status ?? 'completed',
        isPolling: snapshot?.status === 'running',
      })
      await get().fetchAnalytics()
      get().addLog(
        'success',
        `Hunt snapshot received: ${snapshot?.status ?? 'unknown'} with ${snapshot?.jobs_found?.length ?? 0
        } jobs and ${snapshot?.applications?.length ?? 0} applications.`,
      )
    } catch (error) {
      set({
        activeAction: '',
        requestPhase: 'failed',
        errorMessage:
          error instanceof Error ? error.message : 'Unable to launch job hunt.',
        isPolling: false,
      })
      get().addLog(
        'error',
        error instanceof Error ? error.message : 'Hunt launch failed.',
      )
    }
  },

  useRoleAndStart(role) {
    get().addLog('info', `Role selected from recommendations: ${role}.`)
    return get().startHunt(role)
  },

  hydrateSnapshot(snapshot, source = 'snapshot') {
    if (!snapshot) {
      return
    }

    const jobs = snapshot.jobs_found ?? get().jobs
    const applications = snapshot.applications ?? get().applications
    const signature = getSnapshotSignature(snapshot, jobs, applications)
    const previousSignature = get().lastSnapshotSignature

    set((state) => ({
      huntResult: snapshot,
      huntId: snapshot.hunt_id ?? state.huntId,
      careerResult: snapshot.career_recommendation ?? state.careerResult,
      jobs,
      applications,
      selectedJobId: selectedJobFor(jobs, applications, state.selectedJobId),
      isPolling: snapshot.status === 'running',
      lastSnapshotSignature: signature,
    }))

    if (signature !== previousSignature) {
      get().addLog(
        'info',
        `State update from ${source}: ${snapshot.status}, ${jobs.length} jobs, ${applications.length} applications.`,
      )
    }
  },

  async refreshHunt() {
    const huntId = get().huntId
    if (!huntId) {
      return
    }

    try {
      const [snapshot, jobs, applications, analytics] = await Promise.all([
        getHunt(huntId),
        getHuntJobs(huntId),
        getHuntApplications(huntId),
        getAnalytics(),
      ])

      const mergedSnapshot = {
        ...snapshot,
        jobs_found: jobs ?? snapshot?.jobs_found ?? [],
        applications: applications ?? snapshot?.applications ?? [],
      }

      set({
        analytics,
        pollError: '',
      })
      get().hydrateSnapshot(mergedSnapshot, 'polling')
    } catch (error) {
      set({
        pollError:
          error instanceof Error ? error.message : 'Polling request failed.',
      })
      get().addLog(
        'error',
        error instanceof Error ? error.message : 'Polling request failed.',
      )
    }
  },
}))
