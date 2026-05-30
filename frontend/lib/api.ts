export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const TOKEN_KEY = "hcos_access_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window !== "undefined") window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window !== "undefined") window.localStorage.removeItem(TOKEN_KEY);
}

export interface Question {
  index: number;
  text: string;
  component: string;
  reverse: boolean;
}

export interface ComponentScore {
  component: string;
  label: string;
  weight: number;
  score: number;
  question_indices: number[];
}

export interface QuestionnaireResult {
  id: string;
  user_id: string;
  type: string;
  submitted_at: string;
  burnout_pressure_score: number;
  risk_level: "low" | "medium" | "high";
  components: ComponentScore[];
}

export type RiskLevel = "low" | "medium" | "high";

export interface Me {
  id: string;
  email: string;
  full_name: string;
  role: "employee" | "hr" | "team_lead" | "admin" | "ethics_reviewer";
  team_id: string | null;
  is_active: boolean;
  consent_given: boolean;
}

export interface BlockAggregate {
  block: string;
  label: string;
  label_en: string;
  score: number;
  risk_level: RiskLevel;
  distribution: { low: number; medium: number; high: number };
}

export interface TeamDashboard {
  team_id: string;
  generated_at: string;
  cohort_size: number;
  sufficient_data: boolean;
  interpretation: string;
  blocks: BlockAggregate[];
  notice: string | null;
}

export interface MetricAggregate {
  metric_type: string;
  count: number;
  mean: number;
  minimum: number;
  maximum: number;
}

export interface EnvironmentMetrics {
  team_id: string | null;
  metric_type: string | null;
  aggregates: MetricAggregate[];
}

export type RecalibrationCycle = "baseline" | "day_30" | "day_90" | "retrospective";

export interface RecalibrationEvent {
  id: string;
  cycle: RecalibrationCycle;
  questionnaire_id: string | null;
  submitted_at: string | null;
  burnout_pressure_score: number | null;
  risk_level: RiskLevel | null;
  delta_vs_baseline: number | null;
  notes: string | null;
  created_at: string;
}

export interface RecalibrationTimeline {
  user_id: string;
  baseline_score: number | null;
  trend: "improving" | "worsening" | "stable" | "insufficient";
  trend_label: string;
  recommendations: string[];
  events: RecalibrationEvent[];
}

export interface UserSummary {
  id: string;
  full_name: string;
  email: string;
  role: Me["role"];
  team_id: string | null;
}

export interface HistoryItem {
  id: string;
  type: string;
  submitted_at: string;
  burnout_pressure_score: number | null;
  risk_level: RiskLevel | null;
}

export interface CalibrationReview {
  id: string;
  subject_user_id: string;
  reviewer_user_id: string | null;
  reviewer_name: string | null;
  risk_level: RiskLevel | null;
  recommendation: string | null;
  action_items: string | null;
  source_of_evidence: string | null;
  notes: string | null;
  created_at: string;
}

export interface ReviewInput {
  subject_user_id: string;
  risk_level?: RiskLevel | null;
  recommendation?: string | null;
  action_items?: string | null;
  source_of_evidence?: string | null;
  notes?: string | null;
}

export interface AuditEntry {
  id: string;
  actor_user_id: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  detail: Record<string, unknown> | null;
  created_at: string;
}

export interface MetricChange {
  key: string;
  label: string;
  baseline_mean: number;
  latest_mean: number;
  pct_change: number;
  improved: boolean;
}

export interface PilotMetric {
  team_id: string;
  cohort_size: number;
  sufficient_data: boolean;
  target_pct: number;
  target_met: boolean;
  headline: MetricChange | null;
  blocks: MetricChange[];
  notice: string | null;
}

export interface OnboardingHealth {
  team_id: string;
  window_days: number;
  cohort_size: number;
  sufficient_data: boolean;
  new_hire_mean: number | null;
  tenured_mean: number | null;
  integration_friction: number | null;
  friction_flag: boolean;
  at_risk_count: number;
  notice: string | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch(`${API_BASE}${path}`, { ...init, headers: { ...headers, ...init?.headers } });
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail);
  }
  return (await resp.json()) as T;
}

export function login(email: string, password: string): Promise<{ access_token: string; refresh_token: string }> {
  return request("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}

export function giveConsent(): Promise<unknown> {
  return request("/auth/consent", { method: "POST", body: JSON.stringify({ consent_given: true }) });
}

export function fetchQuestions(): Promise<Question[]> {
  return request("/questionnaire/questions");
}

export function submitQuestionnaire(
  answers: { question_index: number; value: number }[],
): Promise<QuestionnaireResult> {
  return request("/questionnaire/submit", {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
}

export function fetchMe(): Promise<Me> {
  return request("/auth/me");
}

export function fetchTeamDashboard(teamId: string): Promise<TeamDashboard> {
  return request(`/dashboard/team/${teamId}`);
}

export function fetchEnvironmentMetrics(teamId?: string): Promise<EnvironmentMetrics> {
  const qs = teamId ? `?team_id=${encodeURIComponent(teamId)}` : "";
  return request(`/environment/metrics${qs}`);
}

export function fetchRecalibration(userId: string): Promise<RecalibrationTimeline> {
  return request(`/recalibration/${userId}`);
}

export function createRecalibration(
  userId: string,
  cycle: RecalibrationCycle,
  notes?: string,
): Promise<RecalibrationEvent> {
  return request("/recalibration/create", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, cycle, notes: notes || null }),
  });
}

export function fetchUsers(): Promise<UserSummary[]> {
  return request("/users");
}

export function fetchEmployeeHistory(userId: string): Promise<HistoryItem[]> {
  return request(`/employee/${userId}/history`);
}

export function fetchReviews(subjectId: string): Promise<CalibrationReview[]> {
  return request(`/calibration/review/${subjectId}`);
}

export function createReview(input: ReviewInput): Promise<CalibrationReview> {
  return request("/calibration/review", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function fetchAudit(limit = 100): Promise<AuditEntry[]> {
  return request(`/audit?limit=${limit}`);
}

export function fetchPilotMetric(teamId: string): Promise<PilotMetric> {
  return request(`/compliance/pilot-metric/team/${teamId}`);
}

export function fetchOnboarding(teamId: string): Promise<OnboardingHealth> {
  return request(`/onboarding/team/${teamId}`);
}

export function exportEmployee(employeeId: string): Promise<unknown> {
  return request(`/export/employee/${employeeId}`);
}
