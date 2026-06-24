"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  createAssessment,
  createCandidate,
  createDevelopmentPlan,
  fetchCandidate,
  fetchCandidates,
  fetchHiringReference,
  fetchMe,
  getToken,
  type Candidate,
  type CandidateDetail,
  type HiringReference,
  type OverallRisk,
  type RiskLevel,
} from "@/lib/api";
import {
  Button,
  Card,
  Disclaimer,
  EmptyState,
  Field,
  Input,
  PageSkeleton,
  SectionHeader,
  Select,
  Textarea,
} from "@/components/ui";

const REVIEWER_ROLES = new Set(["hr", "team_lead", "admin", "ethics_reviewer"]);
const RISK_LEVELS: RiskLevel[] = ["low", "medium", "high"];

const RISK_BTN: Record<RiskLevel, string> = {
  low: "border-emerald-400/60 bg-emerald-400/15 text-emerald-300",
  medium: "border-amber-400/60 bg-amber-400/15 text-amber-300",
  high: "border-orange-400/60 bg-orange-400/15 text-orange-300",
};
const RISK_RU: Record<RiskLevel, string> = { low: "Низкий", medium: "Средний", high: "Высокий" };
const OVERALL_DOT: Record<OverallRisk, string> = {
  green: "bg-emerald-400",
  yellow: "bg-amber-400",
  red: "bg-orange-400",
};

export default function HiringPage() {
  const router = useRouter();
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [ref, setRef] = useState<HiringReference | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [detail, setDetail] = useState<CandidateDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  // forms
  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("");
  const [assType, setAssType] = useState<"quick_screen" | "full_calibration">("quick_screen");
  const [signals, setSignals] = useState<Record<string, RiskLevel>>({});
  const [overall, setOverall] = useState<OverallRisk | "">("");
  const [recommendation, setRecommendation] = useState("");
  const [source, setSource] = useState("");
  const [actionItems, setActionItems] = useState("");
  const [dpArea, setDpArea] = useState("");
  const [dpSupport, setDpSupport] = useState("");

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
        const [r, cs] = await Promise.all([fetchHiringReference(), fetchCandidates()]);
        setRef(r);
        setCandidates(cs);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка загрузки");
        setAllowed(false);
      }
    })();
  }, [router]);

  const openCandidate = useCallback(async (id: string) => {
    setError(null);
    setSignals({});
    setOverall("");
    setRecommendation("");
    setSource("");
    setActionItems("");
    setDetail(await fetchCandidate(id));
  }, []);

  async function onAddCandidate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      const c = await createCandidate(newName.trim(), newRole.trim() || undefined);
      setNewName("");
      setNewRole("");
      setCandidates([c, ...candidates]);
      await openCandidate(c.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  const activeSignals =
    ref?.signals.filter((s) => assType === "full_calibration" || s.quick_screen) ?? [];

  async function onSaveAssessment(e: React.FormEvent) {
    e.preventDefault();
    if (!detail) return;
    try {
      await createAssessment(detail.candidate.id, {
        type: assType,
        signals,
        overall_risk: overall || null,
        recommendation: recommendation || null,
        source_of_evidence: source || null,
        action_items: actionItems || null,
      });
      await openCandidate(detail.candidate.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка сохранения оценки");
    }
  }

  async function onSaveDevPlan(e: React.FormEvent) {
    e.preventDefault();
    if (!detail) return;
    try {
      await createDevelopmentPlan(detail.candidate.id, {
        risk_area: dpArea || null,
        suggested_support: dpSupport || null,
      });
      setDpArea("");
      setDpSupport("");
      await openCandidate(detail.candidate.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  if (allowed === null) {
    return <PageSkeleton width="6xl" />;
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <header className="mb-6">
        <div className="text-[11px] font-semibold uppercase tracking-[0.09em] text-ink-faint">
          Совместимость со средой
        </div>
        <h1 className="mt-1 text-3xl font-semibold text-ink">Подбор и совместимость</h1>
        <p className="mt-2 text-sm text-ink-muted">
          Калибровка совместимости со средой (HR Workbook v6), не оценка ценности человека.
        </p>
      </header>

      {!allowed ? (
        <EmptyState
          title="Доступ только для проверяющих ролей"
          text="Раздел доступен ролям HR, руководитель команды, администратор, этический ревьюер."
        />
      ) : (
        <>
          {error && <p className="mb-4 text-sm text-orange-400">{error}</p>}

          <div className="grid grid-cols-1 gap-6 md:grid-cols-[280px_1fr]">
            {/* Candidate list + add */}
            <aside className="space-y-4">
              <Card>
                <div className="text-sm font-medium text-ink">Новый кандидат</div>
                <form onSubmit={onAddCandidate} className="mt-2 space-y-2">
                  <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Имя" />
                  <Input
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    placeholder="Роль (необязательно)"
                  />
                  <Button type="submit" className="w-full">
                    Добавить
                  </Button>
                </form>
              </Card>

              <div className="space-y-1">
                {candidates.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => openCandidate(c.id)}
                    className={`w-full rounded-control border px-3 py-2 text-left text-sm transition-colors ${
                      detail?.candidate.id === c.id
                        ? "border-accent bg-surface"
                        : "border-edge bg-surface-2 hover:border-white/25"
                    }`}
                  >
                    <div className="font-medium text-ink">{c.full_name}</div>
                    {c.role && <div className="text-xs text-ink-muted">{c.role}</div>}
                  </button>
                ))}
                {candidates.length === 0 && (
                  <p className="text-sm text-ink-muted">Кандидатов пока нет.</p>
                )}
              </div>
            </aside>

            {/* Detail */}
            <section>
              {!detail ? (
                <EmptyState title="Кандидат не выбран" text="Выберите или добавьте кандидата слева." />
              ) : (
                <div className="space-y-8">
                  <div>
                    <h2 className="text-xl font-semibold text-ink">{detail.candidate.full_name}</h2>
                    {detail.candidate.role && (
                      <div className="text-sm text-ink-muted">{detail.candidate.role}</div>
                    )}
                  </div>

                  {/* Past assessments */}
                  <div>
                    <SectionHeader title="Оценки" />
                    {detail.assessments.length > 0 ? (
                      <div className="space-y-2">
                        {detail.assessments.map((a) => (
                          <Card key={a.id} variant="inset" className="px-4 py-3">
                            <div className="flex items-center justify-between text-sm">
                              <span className="font-medium text-ink">
                                {a.type === "quick_screen" ? "Quick Screen" : "Full Calibration"}
                              </span>
                              <span className="flex items-center gap-3 text-xs text-ink-muted">
                                {a.overall_risk && (
                                  <span className="flex items-center gap-1.5">
                                    <span className={`h-2 w-2 rounded-full ${OVERALL_DOT[a.overall_risk]}`} />
                                    {a.overall_risk}
                                  </span>
                                )}
                                {a.suggested_overall_risk && (
                                  <span className="text-ink-faint">подсказка: {a.suggested_overall_risk}</span>
                                )}
                                <span>{a.reviewer_name}</span>
                              </span>
                            </div>
                            {a.recommendation && <div className="mt-1 text-sm text-ink">{a.recommendation}</div>}
                            {a.signals && (
                              <div className="mt-2 flex flex-wrap gap-1 text-xs text-ink-muted">
                                {Object.entries(a.signals).map(([k, v]) => (
                                  <span key={k} className="rounded border border-edge px-1.5 py-0.5">
                                    {k}: {RISK_RU[v]}
                                  </span>
                                ))}
                              </div>
                            )}
                          </Card>
                        ))}
                      </div>
                    ) : (
                      <EmptyState title="Оценок ещё нет" />
                    )}
                  </div>

                  {/* New assessment */}
                  <Card>
                    <form onSubmit={onSaveAssessment}>
                      <div className="flex items-center justify-between">
                        <h3 className="text-lg font-medium text-ink">Новая оценка</h3>
                        <Select
                          value={assType}
                          onChange={(e) => setAssType(e.target.value as typeof assType)}
                          className="w-auto px-3 py-1.5"
                        >
                          <option value="quick_screen" className="bg-neutral-900">
                            Quick Screen
                          </option>
                          <option value="full_calibration" className="bg-neutral-900">
                            Full Calibration
                          </option>
                        </Select>
                      </div>

                      <div className="mt-4 space-y-3">
                        {activeSignals.map((s) => (
                          <div key={s.key} className="rounded-control border border-edge-2 p-3">
                            <div className="text-sm font-medium text-ink" title={s.question}>
                              {s.label}
                              <span className="ml-1 text-xs text-ink-faint">{s.label_en}</span>
                            </div>
                            <div className="mt-1 text-xs text-ink-muted">{s.question}</div>
                            <div className="mt-2 flex gap-2">
                              {RISK_LEVELS.map((lvl) => (
                                <button
                                  type="button"
                                  key={lvl}
                                  title={
                                    lvl === "low"
                                      ? s.legend_low
                                      : lvl === "medium"
                                        ? s.legend_medium
                                        : s.legend_high
                                  }
                                  onClick={() => setSignals({ ...signals, [s.key]: lvl })}
                                  className={`rounded-control border px-3 py-1 text-xs transition-colors ${
                                    signals[s.key] === lvl
                                      ? RISK_BTN[lvl]
                                      : "border-edge bg-surface-2 text-ink-muted hover:border-white/30"
                                  }`}
                                >
                                  {RISK_RU[lvl]}
                                </button>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>

                      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <Field label="Общий риск">
                          <Select value={overall} onChange={(e) => setOverall(e.target.value as OverallRisk | "")}>
                            <option value="" className="bg-neutral-900">
                              — не указан —
                            </option>
                            <option value="green" className="bg-neutral-900">
                              Зелёный — рекомендуется
                            </option>
                            <option value="yellow" className="bg-neutral-900">
                              Жёлтый — условно
                            </option>
                            <option value="red" className="bg-neutral-900">
                              Красный — под надзором
                            </option>
                          </Select>
                        </Field>
                        <Field label="Источник данных">
                          <Input value={source} onChange={(e) => setSource(e.target.value)} />
                        </Field>
                      </div>
                      <div className="mt-3">
                        <Field label="Рекомендация">
                          <Input value={recommendation} onChange={(e) => setRecommendation(e.target.value)} />
                        </Field>
                      </div>
                      <div className="mt-3">
                        <Field label="Действия">
                          <Textarea value={actionItems} onChange={(e) => setActionItems(e.target.value)} rows={2} />
                        </Field>
                      </div>
                      <Button type="submit" className="mt-4">
                        Сохранить оценку
                      </Button>
                    </form>
                  </Card>

                  {/* Development plans */}
                  <div>
                    <SectionHeader title="План развития" />
                    {detail.development_plans.length > 0 && (
                      <div className="mb-3 space-y-2">
                        {detail.development_plans.map((p) => (
                          <Card key={p.id} variant="inset" className="px-4 py-3 text-sm">
                            <div className="font-medium text-ink">{p.risk_area || "—"}</div>
                            {p.suggested_support && (
                              <div className="mt-1 text-xs text-ink-muted">{p.suggested_support}</div>
                            )}
                          </Card>
                        ))}
                      </div>
                    )}
                    <form onSubmit={onSaveDevPlan} className="flex flex-wrap gap-2">
                      <Input
                        value={dpArea}
                        onChange={(e) => setDpArea(e.target.value)}
                        placeholder="Зона риска"
                        className="flex-1"
                      />
                      <Input
                        value={dpSupport}
                        onChange={(e) => setDpSupport(e.target.value)}
                        placeholder="Поддержка"
                        className="flex-1"
                      />
                      <Button type="submit" variant="ghost">
                        Добавить
                      </Button>
                    </form>
                  </div>
                </div>
              )}
            </section>
          </div>
        </>
      )}

      {ref && <Disclaimer className="mt-10">{ref.disclaimer}</Disclaimer>}
    </main>
  );
}
