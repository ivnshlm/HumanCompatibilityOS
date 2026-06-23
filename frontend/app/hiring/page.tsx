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
    return <main className="mx-auto max-w-6xl px-6 py-16 text-sm opacity-60">Загрузка…</main>;
  }
  if (!allowed) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-16">
        <h1 className="text-2xl font-semibold">Подбор и совместимость</h1>
        <p className="mt-4 rounded-xl border border-white/10 bg-white/5 p-6 text-sm opacity-80">
          Раздел доступен ролям HR, руководитель команды, администратор, этический ревьюер.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <header className="mb-6">
        <h1 className="text-3xl font-semibold">Подбор и совместимость</h1>
        <p className="mt-2 text-sm opacity-70">
          Калибровка совместимости со средой (HR Workbook v6), не оценка ценности человека.
        </p>
      </header>

      {error && <p className="mb-4 text-sm text-orange-400">{error}</p>}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-[280px_1fr]">
        {/* Candidate list + add */}
        <aside className="space-y-4">
          <form onSubmit={onAddCandidate} className="rounded-xl border border-white/10 bg-white/5 p-4">
            <div className="text-sm font-medium">Новый кандидат</div>
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Имя"
              className="mt-2 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none placeholder:opacity-40 focus:border-white/30"
            />
            <input
              value={newRole}
              onChange={(e) => setNewRole(e.target.value)}
              placeholder="Роль (необязательно)"
              className="mt-2 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none placeholder:opacity-40 focus:border-white/30"
            />
            <button className="mt-3 w-full rounded-lg bg-white/90 px-3 py-2 text-sm font-medium text-black">
              Добавить
            </button>
          </form>

          <div className="space-y-1">
            {candidates.map((c) => (
              <button
                key={c.id}
                onClick={() => openCandidate(c.id)}
                className={`w-full rounded-lg border px-3 py-2 text-left text-sm ${
                  detail?.candidate.id === c.id
                    ? "border-white/40 bg-white/10"
                    : "border-white/10 bg-white/5 hover:border-white/25"
                }`}
              >
                <div className="font-medium">{c.full_name}</div>
                {c.role && <div className="text-xs opacity-50">{c.role}</div>}
              </button>
            ))}
            {candidates.length === 0 && <p className="text-sm opacity-60">Кандидатов пока нет.</p>}
          </div>
        </aside>

        {/* Detail */}
        <section>
          {!detail ? (
            <p className="text-sm opacity-60">Выберите или добавьте кандидата.</p>
          ) : (
            <div className="space-y-8">
              <div>
                <h2 className="text-xl font-semibold">{detail.candidate.full_name}</h2>
                {detail.candidate.role && (
                  <div className="text-sm opacity-60">{detail.candidate.role}</div>
                )}
              </div>

              {/* Past assessments */}
              <div>
                <h3 className="text-lg font-medium">Оценки</h3>
                {detail.assessments.length > 0 ? (
                  <div className="mt-2 space-y-2">
                    {detail.assessments.map((a) => (
                      <div key={a.id} className="rounded-lg border border-white/10 bg-white/5 px-4 py-3">
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-medium">
                            {a.type === "quick_screen" ? "Quick Screen" : "Full Calibration"}
                          </span>
                          <span className="flex items-center gap-3 text-xs opacity-70">
                            {a.overall_risk && (
                              <span className="flex items-center gap-1.5">
                                <span className={`h-2 w-2 rounded-full ${OVERALL_DOT[a.overall_risk]}`} />
                                {a.overall_risk}
                              </span>
                            )}
                            {a.suggested_overall_risk && (
                              <span className="opacity-60">подсказка: {a.suggested_overall_risk}</span>
                            )}
                            <span>{a.reviewer_name}</span>
                          </span>
                        </div>
                        {a.recommendation && <div className="mt-1 text-sm">{a.recommendation}</div>}
                        {a.signals && (
                          <div className="mt-2 flex flex-wrap gap-1 text-xs opacity-70">
                            {Object.entries(a.signals).map(([k, v]) => (
                              <span key={k} className="rounded border border-white/10 px-1.5 py-0.5">
                                {k}: {RISK_RU[v]}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-sm opacity-60">Оценок ещё нет.</p>
                )}
              </div>

              {/* New assessment */}
              <form onSubmit={onSaveAssessment} className="rounded-xl border border-white/10 bg-white/5 p-5">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium">Новая оценка</h3>
                  <select
                    value={assType}
                    onChange={(e) => setAssType(e.target.value as typeof assType)}
                    className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm outline-none"
                  >
                    <option value="quick_screen" className="bg-neutral-900">
                      Quick Screen
                    </option>
                    <option value="full_calibration" className="bg-neutral-900">
                      Full Calibration
                    </option>
                  </select>
                </div>

                <div className="mt-4 space-y-3">
                  {activeSignals.map((s) => (
                    <div key={s.key} className="rounded-lg border border-white/10 p-3">
                      <div className="text-sm font-medium" title={s.question}>
                        {s.label}
                        <span className="ml-1 text-xs opacity-40">{s.label_en}</span>
                      </div>
                      <div className="mt-1 text-xs opacity-50">{s.question}</div>
                      <div className="mt-2 flex gap-2">
                        {RISK_LEVELS.map((lvl) => (
                          <button
                            type="button"
                            key={lvl}
                            title={
                              lvl === "low" ? s.legend_low : lvl === "medium" ? s.legend_medium : s.legend_high
                            }
                            onClick={() => setSignals({ ...signals, [s.key]: lvl })}
                            className={`rounded-lg border px-3 py-1 text-xs ${
                              signals[s.key] === lvl
                                ? RISK_BTN[lvl]
                                : "border-white/10 bg-white/5 opacity-70 hover:opacity-100"
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
                  <label className="block">
                    <span className="text-xs opacity-60">Общий риск</span>
                    <select
                      value={overall}
                      onChange={(e) => setOverall(e.target.value as OverallRisk | "")}
                      className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none"
                    >
                      <option value="" className="bg-neutral-900">— не указан —</option>
                      <option value="green" className="bg-neutral-900">Зелёный — рекомендуется</option>
                      <option value="yellow" className="bg-neutral-900">Жёлтый — условно</option>
                      <option value="red" className="bg-neutral-900">Красный — под надзором</option>
                    </select>
                  </label>
                  <label className="block">
                    <span className="text-xs opacity-60">Источник данных</span>
                    <input
                      value={source}
                      onChange={(e) => setSource(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none"
                    />
                  </label>
                </div>
                <label className="mt-3 block">
                  <span className="text-xs opacity-60">Рекомендация</span>
                  <input
                    value={recommendation}
                    onChange={(e) => setRecommendation(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none"
                  />
                </label>
                <label className="mt-3 block">
                  <span className="text-xs opacity-60">Действия</span>
                  <textarea
                    value={actionItems}
                    onChange={(e) => setActionItems(e.target.value)}
                    rows={2}
                    className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none"
                  />
                </label>
                <button className="mt-4 rounded-lg bg-white/90 px-5 py-2 text-sm font-medium text-black">
                  Сохранить оценку
                </button>
              </form>

              {/* Development plans */}
              <div>
                <h3 className="text-lg font-medium">План развития</h3>
                {detail.development_plans.length > 0 && (
                  <div className="mt-2 space-y-2">
                    {detail.development_plans.map((p) => (
                      <div key={p.id} className="rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm">
                        <div className="font-medium">{p.risk_area || "—"}</div>
                        {p.suggested_support && (
                          <div className="mt-1 text-xs opacity-70">{p.suggested_support}</div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                <form onSubmit={onSaveDevPlan} className="mt-3 flex flex-wrap gap-2">
                  <input
                    value={dpArea}
                    onChange={(e) => setDpArea(e.target.value)}
                    placeholder="Зона риска"
                    className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none placeholder:opacity-40"
                  />
                  <input
                    value={dpSupport}
                    onChange={(e) => setDpSupport(e.target.value)}
                    placeholder="Поддержка"
                    className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none placeholder:opacity-40"
                  />
                  <button className="rounded-lg border border-white/15 px-4 py-2 text-sm font-medium hover:bg-white/5">
                    Добавить
                  </button>
                </form>
              </div>
            </div>
          )}
        </section>
      </div>

      {ref && <p className="mt-10 text-xs opacity-50">{ref.disclaimer}</p>}
    </main>
  );
}
