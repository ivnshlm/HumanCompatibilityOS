"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchQuestions,
  getToken,
  giveConsent,
  submitQuestionnaire,
  type Question,
  type QuestionnaireResult,
  type ScaleOption,
} from "@/lib/api";
import { RESULT_DISCLAIMER, RISK_TEXT } from "@/lib/risk";
import { Button, Card, Disclaimer, PageSkeleton, ProgressBar, SectionHeader } from "@/components/ui";

const SCALE = [1, 2, 3, 4, 5];

// Safe-language labels (§6): name the overload regime, not the person.
const RISK_LABEL: Record<QuestionnaireResult["risk_level"], string> = {
  low: "Низкий риск перегруза",
  medium: "Средний риск перегруза",
  high: "Высокий риск перегруза",
};

const LEVELS = [
  { id: "short", label: "Короткий", hint: "15 вопросов · ~5 мин" },
  { id: "base", label: "Базовый", hint: "25 вопросов · ~10 мин" },
  { id: "deep", label: "Углублённый", hint: "40 вопросов · ~15–20 мин" },
] as const;

const storageKey = (level: string) => `hcos_qn_${level}`;

export default function QuestionnairePage() {
  const router = useRouter();
  const [level, setLevel] = useState<string>("short");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [scale, setScale] = useState<ScaleOption[]>([]);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [consent, setConsent] = useState(false);
  const [result, setResult] = useState<QuestionnaireResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const [started, setStarted] = useState(false);
  const [step, setStep] = useState(0); // 0..N-1 questions, N = consent step
  const advanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load the question set for the chosen level + restore any autosaved answers.
  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setLoading(true);
    setStarted(false);
    setStep(0);
    fetchQuestions(level)
      .then((set) => {
        setQuestions(set.questions);
        setScale(set.scale);
        try {
          const saved = localStorage.getItem(storageKey(level));
          setAnswers(saved ? (JSON.parse(saved) as Record<string, number>) : {});
        } catch {
          setAnswers({});
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Ошибка загрузки"))
      .finally(() => setLoading(false));
  }, [router, level]);

  // Autosave answers per level.
  useEffect(() => {
    if (questions.length === 0) return;
    try {
      localStorage.setItem(storageKey(level), JSON.stringify(answers));
    } catch {
      /* ignore quota errors */
    }
  }, [answers, level, questions.length]);

  useEffect(() => () => {
    if (advanceTimer.current) clearTimeout(advanceTimer.current);
  }, []);

  const total = questions.length;
  const answeredCount = questions.filter((q) => answers[q.question_id]).length;
  const allAnswered = total > 0 && answeredCount === total;

  const selectAnswer = useCallback(
    (qid: string, value: number, lastIndex: number) => {
      setAnswers((a) => ({ ...a, [qid]: value }));
      if (advanceTimer.current) clearTimeout(advanceTimer.current);
      advanceTimer.current = setTimeout(() => setStep((s) => Math.min(s + 1, lastIndex + 1)), 240);
    },
    [],
  );

  async function onSubmit() {
    setError(null);
    setBusy(true);
    try {
      if (consent) await giveConsent();
      const payload = questions.map((q) => ({ question_id: q.question_id, value: answers[q.question_id] }));
      const res = await submitQuestionnaire(payload, level);
      try {
        localStorage.removeItem(storageKey(level));
      } catch {
        /* ignore */
      }
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка отправки");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <PageSkeleton width="3xl" />;
  }

  // ---- Result ----
  if (result) {
    const interp = result.interpretation;
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <div className="text-[11px] font-semibold uppercase tracking-[0.09em] text-ink-faint">
          Результат
        </div>
        <h1 className="mt-1 text-3xl font-semibold text-ink">Сигнал среды</h1>

        <Card className="mt-6">
          <div className="text-sm text-ink-muted">Давление среды на человека</div>
          <div className="mt-1 text-5xl font-semibold tabular-nums text-ink">
            {result.burnout_pressure_score.toFixed(2)}
          </div>
          <div className={`mt-2 text-lg font-medium ${RISK_TEXT[result.risk_level]}`}>
            {RISK_LABEL[result.risk_level]}
          </div>
          <div className="mt-1 text-xs text-ink-faint">по шкале 1–5 · сигнал, не диагноз</div>
        </Card>

        <section className="mt-8">
          <SectionHeader eyebrow="Интерпретация" title="Кратко" />
          <p className="text-sm leading-relaxed text-ink">{interp.summary}</p>
        </section>

        <section className="mt-8">
          <SectionHeader title="Что создаёт давление" />
          <div className="space-y-2">
            {interp.dominant_factors.map((f) => (
              <Card key={f.key} variant="inset" className="px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-medium text-ink">
                    {f.title}
                    {f.subdimension && (
                      <span className="ml-2 text-xs font-normal text-ink-faint">· {f.subdimension}</span>
                    )}
                  </div>
                  <div className="text-lg font-semibold tabular-nums text-ink">{f.score.toFixed(2)}</div>
                </div>
                <p className="mt-1 text-xs leading-relaxed text-ink-muted">{f.explanation}</p>
              </Card>
            ))}
          </div>
        </section>

        <section className="mt-8">
          <SectionHeader title="Что это может означать" />
          <p className="text-sm leading-relaxed text-ink">{interp.possible_meaning}</p>
        </section>

        <section className="mt-8">
          <SectionHeader title="Что проверить дальше" />
          <ul className="space-y-2">
            {interp.check_next.map((item, i) => (
              <Card key={i} variant="inset" className="flex gap-2 px-4 py-3 text-sm leading-relaxed">
                <span className="text-ink-faint">{i + 1}.</span>
                <span className="text-ink">{item}</span>
              </Card>
            ))}
          </ul>
        </section>

        {interp.follow_ups && interp.follow_ups.length > 0 && (
          <details className="mt-8">
            <summary className="cursor-pointer select-none text-sm font-medium text-ink">
              Вопросы для углублённого разбора
            </summary>
            <ul className="mt-3 space-y-1.5 text-sm leading-relaxed text-ink-muted">
              {interp.follow_ups.map((q, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-ink-faint">—</span>
                  <span>{q}</span>
                </li>
              ))}
            </ul>
          </details>
        )}

        <details className="mt-6">
          <summary className="cursor-pointer select-none text-sm font-medium text-ink">
            Как считался результат
          </summary>
          <div className="mt-4 space-y-3 text-xs leading-relaxed text-ink-muted">
            <p>
              Итоговый балл — взвешенная сумма средних по пяти компонентам среды (шкала 1–5). Веса
              отражают вклад каждого компонента в общее давление.
            </p>
            <p>
              Часть вопросов сформулирована «в позитивную сторону» (восстановление, устойчивый ритм):
              для них шкала инвертируется (6 − ответ), чтобы более высокое значение всегда означало
              большее давление среды.
            </p>
            <div className="space-y-2">
              {result.components.map((c) => (
                <div
                  key={c.component}
                  className="flex items-center justify-between rounded-control border border-edge-2 bg-surface-2 px-4 py-2"
                >
                  <div>
                    <div className="text-sm font-medium text-ink">{c.label}</div>
                    <div className="text-[11px] text-ink-faint">вес {(c.weight * 100).toFixed(0)}%</div>
                  </div>
                  <div className="text-base font-semibold tabular-nums text-ink">{c.score.toFixed(2)}</div>
                </div>
              ))}
            </div>
          </div>
        </details>

        <Disclaimer className="mt-8">{interp.disclaimer || RESULT_DISCLAIMER}</Disclaimer>

        <div className="mt-6">
          <button
            onClick={() => router.push("/")}
            className="text-sm text-ink-muted underline-offset-4 hover:underline"
          >
            ← На главную
          </button>
        </div>
      </main>
    );
  }

  // ---- Intro: choose session length ----
  if (!started) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <div className="text-[11px] font-semibold uppercase tracking-[0.09em] text-ink-faint">
          Опросник среды
        </div>
        <h1 className="mt-1 text-3xl font-semibold text-ink">Оценка давления среды</h1>
        <p className="mt-2 text-sm text-ink-muted">
          Несколько утверждений по шкале согласия 1–5. Ответы можно прервать и продолжить позже —
          они сохраняются на этом устройстве.
        </p>

        <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {LEVELS.map((l) => (
            <button
              key={l.id}
              type="button"
              onClick={() => setLevel(l.id)}
              className={`rounded-card border p-4 text-left transition-colors ${
                level === l.id ? "border-accent bg-surface" : "border-edge bg-surface-2 hover:border-white/30"
              }`}
            >
              <div className="font-medium text-ink">{l.label}</div>
              <div className="mt-0.5 text-xs text-ink-muted">{l.hint}</div>
            </button>
          ))}
        </div>

        {scale.length === 5 && (
          <div className="mt-4 text-xs text-ink-muted">
            <span className="font-medium text-ink">1</span> — {scale[0].label} ·{" "}
            <span className="font-medium text-ink">5</span> — {scale[4].label}
          </div>
        )}

        <div className="mt-6">
          <Button onClick={() => setStarted(true)}>
            {answeredCount > 0 ? `Продолжить (${answeredCount}/${total})` : "Начать опрос"}
          </Button>
        </div>
      </main>
    );
  }

  // ---- Consent / submit step ----
  if (step >= total) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <ProgressBar value={1} />
        <div className="mt-6">
          <SectionHeader eyebrow={`Готово · ${answeredCount}/${total}`} title="Согласие и отправка" />
          <Card>
            <p className="text-sm leading-relaxed text-ink">
              Данные среды собираются только с вашего явного согласия. Это сигнальный слой для
              проверки человеком, а не оценка личности или основание для кадрового решения.
            </p>
            <label className="mt-4 flex items-start gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-1"
              />
              <span>Я даю явное согласие на сбор и обработку этих операционных данных.</span>
            </label>
            {!allAnswered && (
              <p className="mt-3 text-xs text-amber-400">
                Отвечено {answeredCount} из {total}. Вернитесь и завершите оставшиеся вопросы.
              </p>
            )}
            {error && <p className="mt-3 text-sm text-orange-400">{error}</p>}
          </Card>

          <div className="mt-4 flex items-center gap-2">
            <Button variant="ghost" onClick={() => setStep(total - 1)} disabled={busy}>
              ← Назад
            </Button>
            <Button onClick={onSubmit} disabled={busy || !allAnswered || !consent}>
              {busy ? "Отправка…" : "Отправить"}
            </Button>
          </div>
        </div>
        <Disclaimer className="mt-8">{RESULT_DISCLAIMER}</Disclaimer>
      </main>
    );
  }

  // ---- One question at a time ----
  const q = questions[step];
  const selected = answers[q.question_id];
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <ProgressBar value={total > 0 ? answeredCount / total : 0} />
      <div className="mt-3 flex items-center justify-between text-xs text-ink-muted">
        <span>
          Вопрос {step + 1} из {total}
        </span>
        <span className="text-ink-faint">{LEVELS.find((l) => l.id === level)?.label}</span>
      </div>

      <Card className="mt-5">
        <div className="text-[11px] uppercase tracking-[0.09em] text-ink-faint">
          {q.component_name}
          {q.subdimension && <span className="text-ink-faint"> · {q.subdimension}</span>}
        </div>
        <p className="mt-2 text-lg leading-relaxed text-ink">{q.text}</p>

        <div className="mt-5 flex flex-wrap gap-2">
          {SCALE.map((v) => (
            <button
              key={v}
              type="button"
              title={scale.find((s) => s.value === v)?.label ?? ""}
              onClick={() => selectAnswer(q.question_id, v, total - 1)}
              className={`flex h-12 w-12 items-center justify-center rounded-control border text-base transition-colors ${
                selected === v
                  ? "border-accent bg-accent/20 text-ink"
                  : "border-edge bg-surface-2 text-ink-muted hover:border-white/30"
              }`}
            >
              {v}
            </button>
          ))}
        </div>
        {scale.length === 5 && (
          <div className="mt-2 flex justify-between text-xs text-ink-faint">
            <span>{scale[0].label}</span>
            <span>{scale[4].label}</span>
          </div>
        )}
      </Card>

      <div className="mt-4 flex items-center justify-between">
        <Button variant="ghost" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>
          ← Назад
        </Button>
        <Button
          variant="secondary"
          onClick={() => setStep((s) => Math.min(total, s + 1))}
          disabled={!selected}
        >
          {step === total - 1 ? "К согласию →" : "Далее →"}
        </Button>
      </div>
    </main>
  );
}
