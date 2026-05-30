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
} from "@/lib/api";

const SCALE = [1, 2, 3, 4, 5];

const RISK_LABEL: Record<QuestionnaireResult["risk_level"], string> = {
  low: "Низкий риск",
  medium: "Средний риск",
  high: "Высокий риск",
};

const RISK_CLASS: Record<QuestionnaireResult["risk_level"], string> = {
  low: "text-emerald-400",
  medium: "text-amber-400",
  high: "text-red-400",
};

export default function QuestionnairePage() {
  const router = useRouter();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<number, number>>({});
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
    fetchQuestions()
      .then(setQuestions)
      .catch((err) => setError(err instanceof Error ? err.message : "Ошибка загрузки"))
      .finally(() => setLoading(false));
  }, [router]);

  const allAnswered = questions.length > 0 && questions.every((q) => answers[q.index]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (consent) await giveConsent();
      const payload = questions.map((q) => ({
        question_index: q.index,
        value: answers[q.index],
      }));
      const res = await submitQuestionnaire(payload);
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
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="text-2xl font-semibold">Результат</h1>
        <div className="mt-6 rounded-xl border border-white/10 bg-white/5 p-6">
          <div className="text-sm opacity-70">Давление выгорания</div>
          <div className="mt-1 text-4xl font-semibold">
            {result.burnout_pressure_score.toFixed(2)}
          </div>
          <div className={`mt-2 text-lg font-medium ${RISK_CLASS[result.risk_level]}`}>
            {RISK_LABEL[result.risk_level]}
          </div>
        </div>

        <h2 className="mt-8 text-lg font-medium">Разбор по компонентам</h2>
        <div className="mt-3 space-y-2">
          {result.components.map((c) => (
            <div
              key={c.component}
              className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-4 py-3"
            >
              <div>
                <div className="text-sm font-medium">{c.label}</div>
                <div className="text-xs opacity-50">вес {(c.weight * 100).toFixed(0)}%</div>
              </div>
              <div className="text-lg font-semibold">{c.score.toFixed(2)}</div>
            </div>
          ))}
        </div>

        <p className="mt-8 text-xs opacity-50">
          Светофор-индикаторы не являются основанием для кадровых решений. Все выводы требуют
          проверки человеком.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-2xl font-semibold">Опросник среды</h1>
      <p className="mt-2 text-sm opacity-70">
        Оцените каждое утверждение по шкале от 1 (совсем нет) до 5 (полностью да).
      </p>

      <form onSubmit={onSubmit} className="mt-8 space-y-5">
        {questions.map((q) => (
          <fieldset key={q.index} className="rounded-xl border border-white/10 bg-white/5 p-5">
            <legend className="sr-only">
              {q.index}. {q.text}
            </legend>
            <p className="text-sm leading-relaxed">
              <span className="mr-1 opacity-50">{q.index}.</span>
              {q.text}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {SCALE.map((v) => (
                <label
                  key={v}
                  className={`flex h-10 w-10 cursor-pointer select-none items-center justify-center rounded-lg border text-sm transition-colors ${
                    answers[q.index] === v
                      ? "border-white/60 bg-white/20"
                      : "border-white/10 bg-white/5 hover:border-white/30"
                  }`}
                >
                  <input
                    type="radio"
                    name={`q-${q.index}`}
                    value={v}
                    checked={answers[q.index] === v}
                    onChange={() => setAnswers((a) => ({ ...a, [q.index]: v }))}
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
