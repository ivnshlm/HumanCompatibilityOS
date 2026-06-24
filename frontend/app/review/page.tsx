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
import { RESULT_DISCLAIMER, RISK_LABEL } from "@/lib/risk";
import {
  Button,
  Card,
  Disclaimer,
  EmptyState,
  Field,
  Input,
  PageSkeleton,
  RiskBadge,
  Skeleton,
  SectionHeader,
  Select,
  Textarea,
} from "@/components/ui";

const REVIEWER_ROLES = new Set(["hr", "team_lead", "admin", "ethics_reviewer"]);
const RISK_OPTIONS: RiskLevel[] = ["low", "medium", "high"];

// The careful explainable reading of one past result — same doctrine the
// employee sees, so the reviewer reads a signal, not a verdict.
function InterpretationView({ result }: { result: QuestionnaireResult }) {
  const it = result.interpretation;
  return (
    <div className="space-y-3 border-t border-edge px-4 py-3 text-sm">
      <p className="leading-relaxed text-ink">{it.summary}</p>

      <div>
        <div className="text-[11px] uppercase tracking-[0.09em] text-ink-faint">Что создаёт давление</div>
        <div className="mt-1 space-y-1">
          {it.dominant_factors.map((f) => (
            <div key={f.key} className="flex justify-between gap-3">
              <span className="text-ink">
                {f.title}
                {f.subdimension && <span className="ml-2 text-xs text-ink-faint">· {f.subdimension}</span>}
              </span>
              <span className="font-semibold tabular-nums text-ink">{f.score.toFixed(2)}</span>
            </div>
          ))}
        </div>
      </div>

      <p className="leading-relaxed text-ink-muted">{it.possible_meaning}</p>

      <div>
        <div className="text-[11px] uppercase tracking-[0.09em] text-ink-faint">Что проверить дальше</div>
        <ul className="mt-1 list-disc space-y-0.5 pl-5 text-ink">
          {it.check_next.map((x, i) => (
            <li key={i}>{x}</li>
          ))}
        </ul>
      </div>

      {it.follow_ups && it.follow_ups.length > 0 && (
        <div>
          <div className="text-[11px] uppercase tracking-[0.09em] text-ink-faint">
            Вопросы для углублённого разбора
          </div>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-ink-muted">
            {it.follow_ups.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </div>
      )}

      {result.report_layer && (
        <div className="rounded-control border border-edge-2 bg-surface-2 p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.09em] text-ink-faint">
            {result.report_layer.label}
          </div>
          {result.report_layer.description && (
            <p className="mt-1 text-xs leading-relaxed text-ink-muted">{result.report_layer.description}</p>
          )}
          <div className="mt-2 space-y-1.5">
            {result.report_layer.notes.map((n) => (
              <div key={n.component} className="text-xs leading-relaxed">
                <span className="font-medium text-ink">{n.label}.</span>{" "}
                <span className="text-ink-muted">{n.note}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs leading-relaxed text-ink-faint">{it.disclaimer}</p>
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
    const [h, r] = await Promise.all([fetchEmployeeHistory(id).catch(() => []), fetchReviews(id)]);
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
    return <PageSkeleton width="3xl" />;
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <header className="mb-8">
        <div className="text-[11px] font-semibold uppercase tracking-[0.09em] text-ink-faint">
          Проверка человеком
        </div>
        <h1 className="mt-1 text-3xl font-semibold text-ink">Calibration Review</h1>
        <p className="mt-2 text-sm text-ink-muted">
          Человеческая проверка операционного риска с указанием источника. Система не принимает
          решений.
        </p>
      </header>

      {!allowed ? (
        <EmptyState
          title="Доступ только для проверяющих ролей"
          text="Экран доступен ролям HR, руководитель команды, администратор и этический ревьюер."
        />
      ) : (
        <>
          {error && <p className="mb-4 text-sm text-orange-400">{error}</p>}

          <Field label="Сотрудник">
            <Select value={subjectId} onChange={(e) => onSelectSubject(e.target.value)}>
              <option value="" className="bg-neutral-900">
                — выберите —
              </option>
              {users.map((u) => (
                <option key={u.id} value={u.id} className="bg-neutral-900">
                  {u.full_name} ({u.email})
                </option>
              ))}
            </Select>
          </Field>

          {subjectId && (
            <>
              <div className="mt-4 flex justify-end">
                <Button variant="ghost" size="sm" onClick={onExport}>
                  Экспорт для проверки (JSON)
                </Button>
              </div>

              <section className="mt-6">
                <SectionHeader
                  title="История опросников"
                  right={<span className="text-xs text-ink-muted">нажмите для интерпретации</span>}
                />
                {history.length > 0 ? (
                  <div className="space-y-2">
                    {history.map((h) => (
                      <Card key={h.id} variant="inset" className="overflow-hidden p-0">
                        <button
                          type="button"
                          onClick={() => toggleDetail(h.id)}
                          aria-expanded={openId === h.id}
                          className="flex w-full items-center justify-between px-4 py-2.5 text-left hover:bg-white/5"
                        >
                          <div className="text-xs text-ink-muted">
                            {new Date(h.submitted_at).toLocaleString("ru-RU")}
                          </div>
                          <div className="flex items-center gap-4">
                            <span className="text-sm font-semibold tabular-nums text-ink">
                              {h.burnout_pressure_score?.toFixed(2) ?? "—"}
                            </span>
                            <RiskBadge level={h.risk_level} />
                            <span
                              className={`text-xs text-ink-faint transition-transform ${
                                openId === h.id ? "rotate-180" : ""
                              }`}
                            >
                              ▾
                            </span>
                          </div>
                        </button>
                        {openId === h.id &&
                          (details[h.id] ? (
                            <InterpretationView result={details[h.id]} />
                          ) : (
                            <div className="px-4 pb-3">
                              <Skeleton className="h-3 w-40" />
                            </div>
                          ))}
                      </Card>
                    ))}
                  </div>
                ) : (
                  <EmptyState title="Нет заполненных опросников" />
                )}
              </section>

              <section className="mt-8">
                <SectionHeader title="Прошлые review" />
                {reviews.length > 0 ? (
                  <div className="space-y-2">
                    {reviews.map((rv) => (
                      <Card key={rv.id} variant="inset" className="px-4 py-3">
                        <div className="flex items-center justify-between">
                          <RiskBadge level={rv.risk_level} />
                          <span className="text-xs text-ink-faint">
                            {rv.reviewer_name ?? "—"} · {new Date(rv.created_at).toLocaleDateString("ru-RU")}
                          </span>
                        </div>
                        {rv.recommendation && <div className="mt-2 text-sm text-ink">{rv.recommendation}</div>}
                        {rv.action_items && (
                          <div className="mt-1 text-xs text-ink-muted">Действия: {rv.action_items}</div>
                        )}
                        {rv.source_of_evidence && (
                          <div className="mt-1 text-xs text-ink-faint">Источник: {rv.source_of_evidence}</div>
                        )}
                        {rv.notes && <div className="mt-1 text-xs text-ink-faint">{rv.notes}</div>}
                      </Card>
                    ))}
                  </div>
                ) : (
                  <EmptyState title="Review ещё не проводились" />
                )}
              </section>

              <section className="mt-8">
                <SectionHeader title="Новое review" />
                <Card>
                  <form onSubmit={onSubmit} className="space-y-4">
                    <Field label="Уровень риска (по мнению ревьюера)">
                      <Select value={risk} onChange={(e) => setRisk(e.target.value as RiskLevel | "")}>
                        <option value="" className="bg-neutral-900">
                          — не указан —
                        </option>
                        {RISK_OPTIONS.map((r) => (
                          <option key={r} value={r} className="bg-neutral-900">
                            {RISK_LABEL[r]}
                          </option>
                        ))}
                      </Select>
                    </Field>

                    <Field label="Рекомендация">
                      <Input
                        value={recommendation}
                        onChange={(e) => setRecommendation(e.target.value)}
                        maxLength={500}
                      />
                    </Field>

                    <Field label="Действия">
                      <Textarea value={actionItems} onChange={(e) => setActionItems(e.target.value)} rows={2} />
                    </Field>

                    <Field label="Источник данных (обязателен для прозрачности)">
                      <Input
                        value={evidence}
                        onChange={(e) => setEvidence(e.target.value)}
                        maxLength={200}
                        placeholder="например: опросник 30 дней, 1:1 от 12.05"
                      />
                    </Field>

                    <Field label="Заметки">
                      <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
                    </Field>

                    <Button type="submit" disabled={busy}>
                      {busy ? "Сохранение…" : "Сохранить review"}
                    </Button>
                  </form>
                </Card>
              </section>
            </>
          )}
        </>
      )}

      <Disclaimer className="mt-10">{RESULT_DISCLAIMER}</Disclaimer>
    </main>
  );
}
