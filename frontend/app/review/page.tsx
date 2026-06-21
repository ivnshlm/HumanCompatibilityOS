"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  createReview,
  exportEmployee,
  fetchEmployeeHistory,
  fetchMe,
  fetchQuestionnaireDetail,
  fetchReviews,
  fetchUsers,
  getToken,
  type CalibrationReview,
  type HistoryItem,
  type QuestionnaireResult,
  type RiskLevel,
  type UserSummary,
} from "@/lib/api";
import { RESULT_DISCLAIMER, RISK_DOT, RISK_LABEL, RISK_TEXT } from "@/lib/risk";

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

// The careful explainable reading of one past result — same doctrine the
// employee sees, so the reviewer reads a signal, not a verdict.
function InterpretationView({ result }: { result: QuestionnaireResult }) {
  const it = result.interpretation;
  return (
    <div className="space-y-3 border-t border-white/10 px-4 py-3 text-sm">
      <p className="leading-relaxed opacity-90">{it.summary}</p>

      <div>
        <div className="text-xs uppercase tracking-wide opacity-50">Что создаёт давление</div>
        <div className="mt-1 space-y-1">
          {it.dominant_factors.map((f) => (
            <div key={f.key} className="flex justify-between gap-3">
              <span className="opacity-90">
                {f.title}
                {f.subdimension && <span className="ml-2 text-xs opacity-50">· {f.subdimension}</span>}
              </span>
              <span className="font-semibold tabular-nums">{f.score.toFixed(2)}</span>
            </div>
          ))}
        </div>
      </div>

      <p className="leading-relaxed opacity-80">{it.possible_meaning}</p>

      <div>
        <div className="text-xs uppercase tracking-wide opacity-50">Что проверить дальше</div>
        <ul className="mt-1 list-disc space-y-0.5 pl-5 opacity-90">
          {it.check_next.map((x, i) => (
            <li key={i}>{x}</li>
          ))}
        </ul>
      </div>

      {it.follow_ups && it.follow_ups.length > 0 && (
        <div>
          <div className="text-xs uppercase tracking-wide opacity-50">Вопросы для углублённого разбора</div>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 opacity-80">
            {it.follow_ups.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </div>
      )}

      {result.report_layer && (
        <div className="rounded-lg border border-white/10 bg-white/5 p-3">
          <div className="text-xs font-medium uppercase tracking-wide opacity-60">
            {result.report_layer.label}
          </div>
          {result.report_layer.description && (
            <p className="mt-1 text-xs leading-relaxed opacity-70">{result.report_layer.description}</p>
          )}
          <div className="mt-2 space-y-1.5">
            {result.report_layer.notes.map((n) => (
              <div key={n.component} className="text-xs leading-relaxed">
                <span className="font-medium opacity-80">{n.label}.</span>{" "}
                <span className="opacity-70">{n.note}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs leading-relaxed opacity-50">{it.disclaimer}</p>
    </div>
  );
}

export default function ReviewPage() {
  const router = useRouter();
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [subjectId, setSubjectId] = useState<string>("");
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [reviews, setReviews] = useState<CalibrationReview[]>([]);
  const [openId, setOpenId] = useState<string | null>(null);
  const [details, setDetails] = useState<Record<string, QuestionnaireResult>>({});
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

  async function onExport() {
    if (!subjectId) return;
    setError(null);
    try {
      const bundle = await exportEmployee(subjectId);
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `export-${subjectId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка экспорта");
    }
  }

  async function onSelectSubject(id: string) {
    setSubjectId(id);
    setHistory([]);
    setReviews([]);
    setOpenId(null);
    setDetails({});
    if (id) await loadSubject(id);
  }

  async function toggleDetail(id: string) {
    if (openId === id) {
      setOpenId(null);
      return;
    }
    setOpenId(id);
    if (!details[id]) {
      try {
        const d = await fetchQuestionnaireDetail(id);
        setDetails((m) => ({ ...m, [id]: d }));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Не удалось загрузить результат");
      }
    }
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
          <div className="mt-4 flex justify-end">
            <button
              type="button"
              onClick={onExport}
              className="rounded-lg border border-white/15 px-4 py-2 text-sm font-medium hover:bg-white/5"
            >
              Экспорт для проверки (JSON)
            </button>
          </div>

          <section className="mt-6">
            <h2 className="text-lg font-medium">История опросников</h2>
            <p className="mt-1 text-xs opacity-50">Нажмите на запись, чтобы увидеть объяснимую интерпретацию.</p>
            {history.length > 0 ? (
              <div className="mt-3 space-y-2">
                {history.map((h) => (
                  <div key={h.id} className="overflow-hidden rounded-lg border border-white/10 bg-white/5">
                    <button
                      type="button"
                      onClick={() => toggleDetail(h.id)}
                      aria-expanded={openId === h.id}
                      className="flex w-full items-center justify-between px-4 py-2.5 text-left hover:bg-white/5"
                    >
                      <div className="text-xs opacity-60">
                        {new Date(h.submitted_at).toLocaleString("ru-RU")}
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-sm font-semibold">
                          {h.burnout_pressure_score?.toFixed(2) ?? "—"}
                        </span>
                        <RiskBadge level={h.risk_level} />
                        <span className={`text-xs opacity-40 transition-transform ${openId === h.id ? "rotate-180" : ""}`}>
                          ▾
                        </span>
                      </div>
                    </button>
                    {openId === h.id &&
                      (details[h.id] ? (
                        <InterpretationView result={details[h.id]} />
                      ) : (
                        <div className="px-4 pb-3 text-xs opacity-50">Загрузка…</div>
                      ))}
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

      <p className="mt-10 rounded-lg border border-amber-400/20 bg-amber-400/5 px-4 py-3 text-xs leading-relaxed opacity-70">
        {RESULT_DISCLAIMER}
      </p>
    </main>
  );
}
