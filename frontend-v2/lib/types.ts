// ─── Hunt / Orchestrator types ───────────────────────────────────────────────

export interface HuntForm {
  goal: string;
  skills: string;
  interests: string;
  education: string;
  experience: string;
}

export interface LaunchPreset {
  label: string;
  sublabel: string;
  data: HuntForm;
}

export interface PlanStep {
  step_number: number;
  step_type: StepType;
  description: string;
  parameters: Record<string, unknown>;
}

export interface ExecutionPlan {
  goal: string;
  summary: string;
  steps: PlanStep[];
}

export interface ProgressEntry {
  step: StepType;
  status: StepStatus;
  attempt_count: number;
  latency_ms: number | null;
  updated_at: string | null;
  last_errors: ErrorDetail[];
}

export interface Job {
  job_id: string;
  title: string;
  company: string;
  location: string;
  description?: string;
  requirements?: string[];
  source: string;
  url?: string;
  scraped_at?: string;
}

export interface Resume {
  full_text?: string;
  summary?: string;
  skills_section?: string;
  experience_section?: string;
}

export interface CoverLetter {
  full_text?: string;
  greeting?: string;
  body?: string;
  closing?: string;
}

export interface Application {
  application_id: string;
  job_id: string;
  job_title: string;
  company: string;
  status: string;
  resume?: Resume;
  cover_letter?: CoverLetter;
  submitted_at?: string;
  created_at?: string;
}

export interface TrackerEntry {
  application_id: string;
  job_title: string;
  company: string;
  status: string;
  submitted_at?: string;
  created_at?: string;
}

export interface HuntSummary {
  total_jobs: number;
  total_applications: number;
  tracked_applications: number;
  error_count: number;
}

export interface ErrorDetail {
  code: string;
  message: string;
  hunt_id?: string;
  step?: string;
  retryable?: boolean;
  details?: Record<string, unknown>;
}

export interface CareerRole {
  role: string;
  reason: string;
  required_skills?: string[];
}

export interface CareerResult {
  recommended_roles: CareerRole[];
}

export interface HuntResult {
  hunt_id: string;
  goal: string;
  original_goal?: string;
  career_recommendation?: CareerResult;
  goal_was_recommended?: boolean;
  status: HuntStatus;
  plan?: ExecutionPlan;
  progress?: ProgressEntry[];
  jobs_found?: Job[];
  applications?: Application[];
  tracker?: TrackerEntry[];
  errors?: ErrorDetail[];
  created_at?: string;
  completed_at?: string;
  summary?: HuntSummary;
}

export interface AnalyticsMetrics {
  total_applications: number;
  success_rate: number;
  apps_per_day?: number;
  platform_distribution?: Record<string, number>;
  role_diversity?: number;
  resume_success_rate?: number;
  referral_ratio?: number;
}

export interface Analytics {
  classification: string;
  metrics: AnalyticsMetrics;
}

// ─── Status types ────────────────────────────────────────────────────────────

export type StepType = "plan" | "search" | "apply" | "track";
export type StepStatus = "pending" | "running" | "completed" | "failed";
export type HuntStatus = "running" | "completed" | "failed";
export type RequestPhase = "idle" | "submitting" | "recommending" | "completed" | "running" | "failed";
export type ActiveAction = "" | "hunt" | "recommend";
export type ContentTab = "resume" | "cover";

// ─── Server state ────────────────────────────────────────────────────────────

export interface ServerState {
  label: string;
  tone: "checking" | "online" | "offline";
}

// ─── Log entry ───────────────────────────────────────────────────────────────

export type LogLevel = "info" | "success" | "warn" | "error";

export interface LogEntry {
  id: string;
  level: LogLevel;
  at: string;
  message: string;
}

// ─── Timeline ────────────────────────────────────────────────────────────────

export interface TimelineItem {
  step: StepType;
  agent: string;
  label: string;
  status: StepStatus;
  description: string;
  attempts: number;
  latency: number | null;
  updatedAt: string | null;
  errors: ErrorDetail[];
}

export interface Timeline {
  items: TimelineItem[];
  progress: number;
  completed: number;
}

// ─── Tracker row ─────────────────────────────────────────────────────────────

export interface TrackerRow {
  id: string;
  job: string;
  company: string;
  status: string;
  time: string | null;
}

// ─── Store ───────────────────────────────────────────────────────────────────

export interface HuntStoreState {
  form: HuntForm;
  presets: LaunchPreset[];
  serverState: ServerState;
  activeAction: ActiveAction;
  requestPhase: RequestPhase;
  careerResult: CareerResult | null;
  huntResult: HuntResult | null;
  huntId: string;
  jobs: Job[];
  applications: Application[];
  analytics: Analytics | null;
  selectedJobId: string;
  contentTab: ContentTab;
  jobFilter: string;
  errorMessage: string;
  pollError: string;
  isPolling: boolean;
  lastSnapshotSignature: string;
  logs: LogEntry[];
  sidebarCollapsed: boolean;
}

export interface HuntStoreActions {
  addLog: (level: LogLevel, message: string) => void;
  setField: (name: keyof HuntForm, value: string) => void;
  applyPreset: (preset: LaunchPreset) => void;
  resetCommandCenter: () => void;
  setJobFilter: (value: string) => void;
  selectJob: (jobId: string) => void;
  setContentTab: (tab: ContentTab) => void;
  clearError: () => void;
  setSidebarCollapsed: (value: boolean) => void;
  checkHealth: () => Promise<void>;
  fetchAnalytics: () => Promise<void>;
  recommendCareer: () => Promise<void>;
  startHunt: (goalOverride?: string | null) => Promise<void>;
  applyRoleAndStart: (role: string) => Promise<void>;
  hydrateSnapshot: (snapshot: HuntResult, source?: string) => void;
  refreshHunt: () => Promise<void>;
}

export type HuntStore = HuntStoreState & HuntStoreActions;
