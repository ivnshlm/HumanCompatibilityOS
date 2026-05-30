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
