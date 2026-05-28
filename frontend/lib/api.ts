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
