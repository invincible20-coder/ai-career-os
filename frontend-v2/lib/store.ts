import { create } from "zustand";
import {
  createHunt,
  getAnalytics,
  getHealth,
  getHunt,
  getHuntApplications,
  getHuntJobs,
  recommendCareer as requestCareerRecommendation,
} from "./api";
import type {
  ActiveAction,
  Analytics,
  Application,
  ContentTab,
  HuntForm,
  HuntResult,
  HuntStore,
  Job,
  LaunchPreset,
  LogEntry,
  LogLevel,
  RequestPhase,
} from "./types";

// ─── Constants ───────────────────────────────────────────────────────────────

export const initialForm: HuntForm = {
  goal: "",
  skills: "",
  interests: "",
  education: "",
  experience: "",
};

export const launchPresets: LaunchPreset[] = [
  {
    label: "Backend Systems",
    sublabel: "FastAPI · SQL · Automation",
    data: {
      goal: "Backend Engineer",
      skills: "Python, FastAPI, SQL, REST APIs, automation",
      interests: "distributed systems, developer tooling, workflow automation",
      education: "B.Tech in Computer Science",
      experience:
        "Built API projects, database-backed services, and full-stack academic tools.",
    },
  },
  {
    label: "Product Engineer",
    sublabel: "React · Node · Shipping",
    data: {
      goal: "Full Stack Software Engineer",
      skills: "React, JavaScript, Node.js, SQL, UI engineering",
      interests: "product development, workflow tools, user experience",
      education: "B.Sc. in Information Technology",
      experience:
        "Created dashboards, product features, and internal workflow tools.",
    },
  },
  {
    label: "Data & Automation",
    sublabel: "Pipelines · Analytics · ETL",
    data: {
      goal: "",
      skills: "Python, SQL, Pandas, ETL, reporting",
      interests: "analytics platforms, automation, operational intelligence",
      education: "Master in Data Science",
      experience:
        "Worked with data analysis, reporting automation, and dashboard generation.",
    },
  },
];

const MAX_LOGS = 80;

export function parseList(value: string): string[] {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function buildPayload(
  form: HuntForm,
  opts: { includeGoal?: boolean; goalOverride?: string | null } = {}
) {
  const { includeGoal = true, goalOverride = null } = opts;
  const resolvedGoal = goalOverride ?? form.goal;
  const payload: Record<string, unknown> = {};

  if (includeGoal && resolvedGoal.trim()) payload.goal = resolvedGoal.trim();
  if (form.skills.trim()) payload.skills = parseList(form.skills);
  if (form.interests.trim()) payload.interests = parseList(form.interests);
  if (form.education.trim()) payload.education = form.education.trim();
  if (form.experience.trim()) payload.experience = form.experience.trim();

  return payload;
}

function nowIso() {
  return new Date().toISOString();
}

function compactLogs(logs: LogEntry[], entry: LogEntry): LogEntry[] {
  return [entry, ...logs].slice(0, MAX_LOGS);
}

function getSnapshotSignature(
  snapshot: HuntResult | null,
  jobs: Job[],
  applications: Application[]
) {
  return [
    snapshot?.status ?? "idle",
    snapshot?.progress
      ?.map((s) => `${s.step}:${s.status}`)
      .join("|") ?? "",
    jobs.length,
    applications.length,
    snapshot?.errors?.length ?? 0,
  ].join("::");
}

function selectedJobFor(
  jobs: Job[],
  applications: Application[],
  currentId: string
): string {
  if (currentId && jobs.some((j) => j.job_id === currentId)) return currentId;
  if (currentId && applications.some((a) => a.job_id === currentId))
    return currentId;
  return jobs[0]?.job_id ?? applications[0]?.job_id ?? "";
}

// ─── Store ───────────────────────────────────────────────────────────────────

export const useHuntStore = create<HuntStore>((set, get) => ({
  form: initialForm,
  presets: launchPresets,
  serverState: { label: "Checking backend", tone: "checking" },
  activeAction: "" as ActiveAction,
  requestPhase: "idle" as RequestPhase,
  careerResult: null,
  huntResult: null,
  huntId: "",
  jobs: [],
  applications: [],
  analytics: null,
  selectedJobId: "",
  contentTab: "resume" as ContentTab,
  jobFilter: "",
  errorMessage: "",
  pollError: "",
  isPolling: false,
  lastSnapshotSignature: "",
  sidebarCollapsed: false,
  logs: [
    { id: "boot", level: "info", at: nowIso(), message: "System initialized. Ready for autonomous operations." },
  ],

  addLog(level: LogLevel, message: string) {
    set((state) => ({
      logs: compactLogs(state.logs, {
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        level,
        at: nowIso(),
        message,
      }),
    }));
  },

  setField(name, value) {
    set((state) => ({
      form: { ...state.form, [name]: value },
      errorMessage: "",
    }));
  },

  applyPreset(preset) {
    set({ form: preset.data, errorMessage: "", pollError: "" });
    get().addLog("info", `Loaded profile: ${preset.label}`);
  },

  resetCommandCenter() {
    set({
      form: initialForm,
      activeAction: "",
      requestPhase: "idle",
      careerResult: null,
      huntResult: null,
      huntId: "",
      jobs: [],
      applications: [],
      selectedJobId: "",
      contentTab: "resume",
      jobFilter: "",
      errorMessage: "",
      pollError: "",
      isPolling: false,
      lastSnapshotSignature: "",
    });
    get().addLog("info", "Workspace reset.");
  },

  setJobFilter(value) {
    set({ jobFilter: value });
  },

  selectJob(jobId) {
    set({ selectedJobId: jobId });
  },

  setContentTab(tab) {
    set({ contentTab: tab });
  },

  clearError() {
    set({ errorMessage: "", pollError: "" });
  },

  setSidebarCollapsed(value) {
    set({ sidebarCollapsed: value });
  },

  async checkHealth() {
    try {
      const health = await getHealth();
      set({
        serverState: {
          label: `v${health?.version ?? "unknown"}`,
          tone: "online",
        },
      });
      get().addLog("success", "Backend connection verified.");
    } catch (error) {
      set({ serverState: { label: "Offline", tone: "offline" } });
      get().addLog(
        "error",
        error instanceof Error ? error.message : "Health check failed."
      );
    }
  },

  async fetchAnalytics() {
    try {
      const analytics = (await getAnalytics()) as Analytics | null;
      set({ analytics });
    } catch (error) {
      get().addLog(
        "warn",
        error instanceof Error ? error.message : "Analytics unavailable."
      );
    }
  },

  async recommendCareer() {
    if (get().activeAction) return;
    set({
      activeAction: "recommend",
      requestPhase: "recommending",
      errorMessage: "",
      pollError: "",
    });
    get().addLog("info", "Career analysis initiated...");

    try {
      const rec = await requestCareerRecommendation(
        buildPayload(get().form, { includeGoal: false })
      );
      set({
        careerResult: rec as HuntStore["careerResult"],
        activeAction: "",
        requestPhase: "idle",
      });
      const roles = (rec as Record<string, unknown>)?.recommended_roles;
      get().addLog(
        "success",
        `Career agent returned ${Array.isArray(roles) ? roles.length : 0} recommendations.`
      );
    } catch (error) {
      set({
        activeAction: "",
        requestPhase: "failed",
        errorMessage:
          error instanceof Error ? error.message : "Career analysis failed.",
      });
      get().addLog(
        "error",
        error instanceof Error ? error.message : "Career recommendation failed."
      );
    }
  },

  async startHunt(goalOverride = null) {
    if (get().activeAction) return;
    if (goalOverride) {
      set((state) => ({ form: { ...state.form, goal: goalOverride } }));
    }
    set({
      activeAction: "hunt",
      requestPhase: "submitting",
      errorMessage: "",
      pollError: "",
      isPolling: false,
    });
    get().addLog("info", "Autonomous hunt launched. Agents deploying...");

    try {
      const snapshot = (await createHunt(
        buildPayload(get().form, { goalOverride })
      )) as HuntResult | null;

      if (snapshot) {
        get().hydrateSnapshot(snapshot, "launch");
        set({
          activeAction: "",
          requestPhase: (snapshot.status as RequestPhase) ?? "completed",
          isPolling: snapshot.status === "running",
        });
      } else {
        set({ activeAction: "", requestPhase: "completed" });
      }
      await get().fetchAnalytics();
      get().addLog(
        "success",
        `Hunt complete — ${snapshot?.jobs_found?.length ?? 0} jobs, ${snapshot?.applications?.length ?? 0} applications.`
      );
    } catch (error) {
      set({
        activeAction: "",
        requestPhase: "failed",
        errorMessage:
          error instanceof Error ? error.message : "Hunt launch failed.",
        isPolling: false,
      });
      get().addLog(
        "error",
        error instanceof Error ? error.message : "Hunt launch failed."
      );
    }
  },

  async applyRoleAndStart(role) {
    get().addLog("info", `Selected role: ${role}`);
    return get().startHunt(role);
  },

  hydrateSnapshot(snapshot, source = "snapshot") {
    if (!snapshot) return;
    const jobs = (snapshot.jobs_found ?? get().jobs) as Job[];
    const applications = (snapshot.applications ??
      get().applications) as Application[];
    const signature = getSnapshotSignature(snapshot, jobs, applications);
    const prev = get().lastSnapshotSignature;

    set((state) => ({
      huntResult: snapshot,
      huntId: snapshot.hunt_id ?? state.huntId,
      careerResult: snapshot.career_recommendation ?? state.careerResult,
      jobs,
      applications,
      selectedJobId: selectedJobFor(jobs, applications, state.selectedJobId),
      isPolling: snapshot.status === "running",
      lastSnapshotSignature: signature,
    }));

    if (signature !== prev) {
      get().addLog(
        "info",
        `State update (${source}): ${snapshot.status}, ${jobs.length} jobs, ${applications.length} applications.`
      );
    }
  },

  async refreshHunt() {
    const huntId = get().huntId;
    if (!huntId) return;

    try {
      const [snapshot, jobs, applications, analytics] = await Promise.all([
        getHunt(huntId),
        getHuntJobs(huntId),
        getHuntApplications(huntId),
        getAnalytics(),
      ]);

      const merged = {
        ...(snapshot as HuntResult),
        jobs_found: (jobs as Job[]) ?? (snapshot as HuntResult)?.jobs_found ?? [],
        applications:
          (applications as Application[]) ??
          (snapshot as HuntResult)?.applications ??
          [],
      };

      set({ analytics: analytics as Analytics | null, pollError: "" });
      get().hydrateSnapshot(merged, "polling");
    } catch (error) {
      set({
        pollError:
          error instanceof Error ? error.message : "Polling failed.",
      });
      get().addLog(
        "error",
        error instanceof Error ? error.message : "Polling failed."
      );
    }
  },
}));
