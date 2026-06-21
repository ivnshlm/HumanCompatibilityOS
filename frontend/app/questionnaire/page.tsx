"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  fetchQuestions,
  getToken,
  giveConsent,
  submitQuestionnaire,
  type Question,
  type QuestionnaireResult,
  type ScaleOption,
} from "@/lib/api";

const SCALE = [1, 2, 3, 4, 5];

// Safe-language labels (§6): name the overload regime, not the person.
const RISK_LABEL: Record<QuestionnaireResult["risk_level"], string> = {
  low: "Низкий риск",
  medium: "Средний риск перегруза",
  high: "Высокий риск перегруза",
};

// Calm palette: high risk is a muted warning, never an aggressive red verdict.
const RISK_CLASS: Record<QuestionnaireResult["risk_level"], string> = {
  low: "text-emerald-400",
  medium: "text-amber-400",
  high: "text-orange-400",
};

const LEVELS = [
  { id: "short", label: "Короткий", hint: "15 вопросов · ~5 мин" },
  { id: "base", label: "Базовый", hint: "25 вопросов · ~10 мин" },
  { id: "deep", label: "Углублённый", hint: "40 вопросов · ~15–20 мин" },
] as const;

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

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setLoading(true);
    fetchQuestions(level)
      .then((set) => {
        setQuestions(set.questions);
        setScale(set.scale);
        setAnswers({}); // a new level is a different question set
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Ошибка загрузки"))
      .finally(() => setLoading(false));
  }, [router, level]);

  const allAnswered = questions.length > 0 && questions.every((q) => answers[q.question_id]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (consent) await giveConsent();
      const payload = questions.map((q) => ({
        question_id: q.question_id,
        value: answers[q.question_id],
      }));
      const res = await submitQuestionnaire(payload, level);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка отправки");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <main className="mx-auto max-w-3xl px-6 py-16 text-sm opacity-60">Загрузка…</main>;
  }

  if (result) {
    const interp = result.interpretation;
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="text-2xl font-semibold">Результат</h1>

        {/* Numeric block (preserved) */}
        <div className="mt-6 rounded-xl border border-white/10 bg-white/5 p-6">
          <div className="text-sm opacity-70">Давление среды на человека</div>
          <div className="mt-1 text-4xl font-semibold">
            {result.burnout_pressure_score.toFixed(2)}
          </div>
          <div className={`mt-2 text-lg font-medium ${RISK_CLASS[result.risk_level]}`}>
            {RISK_LABEL[result.risk_level]}
          </div>
        </div>

        {/* Краткая интерпретация */}
        <section className="mt-8">
          <h2 className="text-lg font-medium">Краткая интерпретация</h2>
          <p className="mt-2 text-sm leading-relaxed opacity-90">{interp.summary}</p>
        </section>

        {/* Что создаёт давление (доминирующие факторы) */}
        <section className="mt-8">
          <h2 className="text-lg font-medium">Что создаёт давление</h2>
          <div className="mt-3 space-y-2">
            {interp.dominant_factors.map((f) => (
              <div
                key={f.key}
                className="rounded-lg border border-white/10 bg-white/5 px-4 py-3"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-medium">{f.title}</div>
                  <div className="text-lg font-semibold tabular-nums">{f.score.toFixed(2)}</div>
                </div>
                <p className="mt-1 text-xs leading-relaxed opacity-60">{f.explanation}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Что это может означать */}
        <section className="mt-8">
          <h2 className="text-lg font-medium">Что это может означать</h2>
          <p className="mt-2 text-sm leading-relaxed opacity-90">{interp.possible_meaning}</p>
        </section>

        {/* Что проверить дальше */}
        <section className="mt-8">
          <h2 className="text-lg font-medium">Что проверить дальше</h2>
          <ul className="mt-3 space-y-2">
            {interp.check_next.map((item, i) => (
              <li
                key={i}
                className="flex gap-2 rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm leading-relaxed"
              >
                <span className="opacity-40">{i + 1}.</span>
                <span className="opacity-90">{item}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* Как считался результат (раскрытие + полный разбор по компонентам) */}
        <details className="mt-8 rounded-xl border border-white/10 bg-white/5 px-5 py-4">
          <summary className="cursor-pointer select-none text-sm font-medium opacity-90">
            Как считался результат
          </summary>
          <div className="mt-4 space-y-3 text-xs leading-relaxed opacity-70">
            <p>
              Итоговый балл — это взвешенная сумма средних по пяти компонентам среды (шкала
              1–5). Веса отражают вклад каждого компонента в общее давление.
            </p>
            <p>
              Часть вопросов сформулирована «в позитивную сторону» (например, про
              восстановление и устойчивый ритм): для них шкала инвертируется (6 − ответ), чтобы
              у всех компонентов более высокое значение означало большее давление среды.
            </p>
            <div className="mt-2 space-y-2">
              {result.components.map((c) => (
                <div
                  key={c.component}
                  className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-4 py-2"
                >
                  <div>
                    <div className="text-sm font-medium opacity-90">{c.label}</div>
                    <div className="text-[11px] opacity-50">вес {(c.weight * 100).toFixed(0)}%</div>
                  </div>
                  <div className="text-base font-semibold tabular-nums opacity-90">
                    {c.score.toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
            <p>
              Результат — это <strong>сигнал среды для проверки человеком</strong>, а не
              кадровое решение и не оценка личности.
            </p>
          </div>
        </details>

        {/* Постоянный этический дисклеймер */}
        <p className="mt-8 rounded-lg border border-amber-400/20 bg-amber-400/5 px-4 py-3 text-xs leading-relaxed opacity-70">
          {interp.disclaimer}
        </p>

        <div className="mt-6">
          <button
            onClick={() => router.push("/")}
            className="text-sm opacity-60 underline-offset-4 hover:underline"
          >
            ← На главную
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-2xl font-semibold">Опросник среды</h1>
      <p className="mt-2 text-sm opacity-70">
        Оцените каждое утверждение по шкале согласия от 1 до 5.
      </p>

      {/* Session level selector */}
      <div className="mt-5 flex flex-wrap gap-2">
        {LEVELS.map((l) => (
          <button
            key={l.id}
            type="button"
            onClick={() => setLevel(l.id)}
            disabled={busy}
            className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
              level === l.id
                ? "border-white/60 bg-white/15"
                : "border-white/10 bg-white/5 hover:border-white/30"
            }`}
          >
            <div className="font-medium">{l.label}</div>
            <div className="text-xs opacity-50">{l.hint}</div>
          </button>
        ))}
      </div>

      {scale.length === 5 && (
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs opacity-50">
          {scale.map((s) => (
            <span key={s.value}>
              <span className="font-medium opacity-80">{s.value}</span> — {s.label}
            </span>
          ))}
        </div>
      )}

      <form onSubmit={onSubmit} className="mt-8 space-y-5">
        {questions.map((q, i) => (
          <fieldset key={q.question_id} className="rounded-xl border border-white/10 bg-white/5 p-5">
            <legend className="sr-only">
              {i + 1}. {q.text}
            </legend>
            <p className="text-sm leading-relaxed">
              <span className="mr-1 opacity-50">{i + 1}.</span>
              {q.text}
            </p>
            <div className="mt-1 text-xs opacity-40">{q.component_name} · {q.subdimension}</div>
            <div className="mt-4 flex flex-wrap gap-2">
              {SCALE.map((v) => (
                <label
                  key={v}
                  title={scale.find((s) => s.value === v)?.label ?? ""}
                  className={`flex h-10 w-10 cursor-pointer select-none items-center justify-center rounded-lg border text-sm transition-colors ${
                    answers[q.question_id] === v
                      ? "border-white/60 bg-white/20"
                      : "border-white/10 bg-white/5 hover:border-white/30"
                  }`}
                >
                  <input
                    type="radio"
                    name={`q-${q.question_id}`}
                    value={v}
                    checked={answers[q.question_id] === v}
                    onChange={() => setAnswers((a) => ({ ...a, [q.question_id]: v }))}
                    className="sr-only"
                  />
                  {v}
                </label>
              ))}
            </div>
          </fieldset>
        ))}

        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            className="mt-1"
          />
          <span className="opacity-80">
            Я даю явное согласие на сбор и обработку этих операционных данных.
          </span>
        </label>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <button
          type="submit"
          disabled={busy || !allAnswered || !consent}
          className="rounded-lg bg-white/90 px-5 py-2 text-sm font-medium text-black disabled:opacity-40"
        >
          {busy ? "Отправка…" : "Отправить"}
        </button>
      </form>
    </main>
  );
}
