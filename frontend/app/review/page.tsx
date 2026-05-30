"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  createReview,
  fetchEmployeeHistory,
  fetchMe,
  fetchReviews,
  fetchUsers,
  getToken,
  type CalibrationReview,
  type HistoryItem,
  type RiskLevel,
  type UserSummary,
} from "@/lib/api";
import { NO_DECISION_DISCLAIMER, RISK_DOT, RISK_LABEL, RISK_TEXT } from "@/lib/risk";

const REVIEWER_ROLES = new Set(["hr", "team_lead", "admin", "ethics_reviewer"]);
const RISK_OPTIONS: RiskLevel[] = ["low", "medium", "high"];

function RiskBadge({ level }: { level: RiskLevel | null }) {
  if (!level) return <span className="text-xs opacity-50">—</span>;
  return (
    <span className={`inline-flex items-center gap-1.5 text-sm font-medium ${RISK_TEXT[level]}`}>
      <span className={`h-2 w-2 rounded-full ${RISK_DOT[level]}`} />
      {RISK_LABEL[level]}
    </span>
  );
}

export default function ReviewPage() {
  const router = useRouter();
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [subjectId, setSubjectId] = useState<string>("");
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [reviews, setReviews] = useState<CalibrationReview[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Review form
  const [risk, setRisk] = useState<RiskLevel | "">("");
  const [recommendation, setRecommendation] = useState("");
  const [actionItems, setActionItems] = useState("");
  const [evidence, setEvidence] = useState("");
  const [notes, setNotes] = useState("");

  const loadSubject = useCallback(async (id: string) => {
    setError(null);
    const [h, r] = await Promise.all([
      fetchEmployeeHistory(id).catch(() => []),
      fetchReviews(id),
    ]);
    setHistory(h);
    setReviews(r);
  }, []);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    (async () => {
      try {
        const me = await fetchMe();
        if (!REVIEWER_ROLES.has(me.role)) {
          setAllowed(false);
          return;
        }
        setAllowed(true);
        setUsers(await fetchUsers());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка загрузки");
        setAllowed(false);
      }
    })();
  }, [router]);

  async function onSelectSubject(id: string) {
    setSubjectId(id);
    setHistory([]);
    setReviews([]);
    if (id) await loadSubject(id);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!subjectId) return;
    setBusy(true);
    setError(null);
    try {
      await createReview({
        subject_user_id: subjectId,
        risk_level: risk || null,
        recommendation: recommendation || null,
        action_items: actionItems || null,
        source_of_evidence: evidence || null,
        notes: notes || null,
      });
      setRisk("");
      setRecommendation("");
      setActionItems("");
      setEvidence("");
      setNotes("");
      await loadSubject(subjectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка сохранения");
    } finally {
      setBusy(false);
    }
  }

  if (allowed === null) {
    return <main className="mx-auto max-w-3xl px-6 py-16 text-sm opacity-60">Загрузка…</main>;
  }

  if (!allowed) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-16">
        <h1 className="text-2xl font-semibold">Calibration Review</h1>
        <p className="mt-4 rounded-xl border border-white/10 bg-white/5 p-6 text-sm opacity-80">
          Экран доступен только ролям HR, руководитель команды, администратор и этический ревьюер.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold">Calibration Review</h1>
        <p className="mt-2 text-sm opacity-70">
          Человеческая проверка операционного риска с указанием источника. Система не принимает
          решений.
        </p>
      </header>

      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}

      <label className="block">
        <span className="text-sm opacity-70">Сотрудник</span>
        <select
          value={subjectId}
          onChange={(e) => onSelectSubject(e.target.value)}
          className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-white/30"
        >
          <option value="" className="bg-neutral-900">
            — выберите —
          </option>
          {users.map((u) => (
            <option key={u.id} value={u.id} className="bg-neutral-900">
              {u.full_name} ({u.email})
            </option>
          ))}
        </select>
      </label>

      {subjectId && (
        <>
          <section className="mt-8">
            <h2 className="text-lg font-medium">История опросников</h2>
            {history.length > 0 ? (
              <div className="mt-3 space-y-2">
                {history.map((h) => (
                  <div
                    key={h.id}
                    className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-4 py-2.5"
                  >
                    <div className="text-xs opacity-60">
                      {new Date(h.submitted_at).toLocaleString("ru-RU")}
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-sm font-semibold">
                        {h.burnout_pressure_score?.toFixed(2) ?? "—"}
                      </span>
                      <RiskBadge level={h.risk_level} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm opacity-60">Нет заполненных опросников.</p>
            )}
          </section>

          <section className="mt-8">
            <h2 className="text-lg font-medium">Прошлые review</h2>
            {reviews.length > 0 ? (
              <div className="mt-3 space-y-2">
                {reviews.map((rv) => (
                  <div key={rv.id} className="rounded-lg border border-white/10 bg-white/5 px-4 py-3">
                    <div className="flex items-center justify-between">
                      <RiskBadge level={rv.risk_level} />
                      <span className="text-xs opacity-50">
                        {rv.reviewer_name ?? "—"} · {new Date(rv.created_at).toLocaleDateString("ru-RU")}
                      </span>
                    </div>
                    {rv.recommendation && <div className="mt-2 text-sm">{rv.recommendation}</div>}
                    {rv.action_items && (
                      <div className="mt-1 text-xs opacity-70">Действия: {rv.action_items}</div>
                    )}
                    {rv.source_of_evidence && (
                      <div className="mt-1 text-xs opacity-50">Источник: {rv.source_of_evidence}</div>
                    )}
                    {rv.notes && <div className="mt-1 text-xs opacity-50">{rv.notes}</div>}
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm opacity-60">Review ещё не проводились.</p>
            )}
          </section>

          <section className="mt-8 rounded-xl border border-white/10 bg-white/5 p-5">
            <h2 className="text-lg font-medium">Новое review</h2>
            <form onSubmit={onSubmit} className="mt-4 space-y-4">
              <label className="block">
                <span className="text-sm opacity-70">Уровень риска (по мнению ревьюера)</span>
                <select
                  value={risk}
                  onChange={(e) => setRisk(e.target.value as RiskLevel | "")}
                  className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-white/30"
                >
                  <option value="" className="bg-neutral-900">
                    — не указан —
                  </option>
                  {RISK_OPTIONS.map((r) => (
                    <option key={r} value={r} className="bg-neutral-900">
                      {RISK_LABEL[r]}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-sm opacity-70">Рекомендация</span>
                <input
                  value={recommendation}
                  onChange={(e) => setRecommendation(e.target.value)}
                  maxLength={500}
                  className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-white/30"
                />
              </label>

              <label className="block">
                <span className="text-sm opacity-70">Действия</span>
                <textarea
                  value={actionItems}
                  onChange={(e) => setActionItems(e.target.value)}
                  rows={2}
                  className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-white/30"
                />
              </label>

              <label className="block">
                <span className="text-sm opacity-70">Источник данных (обязателен для прозрачности)</span>
                <input
                  value={evidence}
                  onChange={(e) => setEvidence(e.target.value)}
                  maxLength={200}
                  placeholder="например: опросник 30 дней, 1:1 от 12.05"
                  className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none placeholder:opacity-30 focus:border-white/30"
                />
              </label>

              <label className="block">
                <span className="text-sm opacity-70">Заметки</span>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-white/30"
                />
              </label>

              <button
                type="submit"
                disabled={busy}
                className="rounded-lg bg-white/90 px-5 py-2 text-sm font-medium text-black disabled:opacity-40"
              >
                {busy ? "Сохранение…" : "Сохранить review"}
              </button>
            </form>
          </section>
        </>
      )}

      <p className="mt-10 text-xs opacity-50">{NO_DECISION_DISCLAIMER}</p>
    </main>
  );
}
