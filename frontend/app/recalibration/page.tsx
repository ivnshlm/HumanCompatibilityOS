"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  createRecalibration,
  fetchMe,
  fetchRecalibration,
  getToken,
  type RecalibrationCycle,
  type RecalibrationTimeline,
} from "@/lib/api";
import { RISK_TEXT } from "@/lib/risk";

const CYCLE_LABEL: Record<RecalibrationCycle, string> = {
  baseline: "Базовая точка",
  day_30: "30 дней",
  day_90: "90 дней",
  retrospective: "Ретроспектива",
};

const CYCLES: RecalibrationCycle[] = ["baseline", "day_30", "day_90", "retrospective"];

const TREND_TEXT: Record<RecalibrationTimeline["trend"], string> = {
  improving: "text-emerald-400",
  worsening: "text-orange-400",
  stable: "text-amber-400",
  insufficient: "opacity-60",
};

function formatDelta(delta: number | null): string {
  if (delta === null) return "—";
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(2)}`;
}

export default function RecalibrationPage() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<RecalibrationTimeline | null>(null);
  const [cycle, setCycle] = useState<RecalibrationCycle>("baseline");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (uid: string) => {
    const data = await fetchRecalibration(uid);
    setTimeline(data);
  }, []);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    (async () => {
      try {
        const me = await fetchMe();
        setUserId(me.id);
        await load(me.id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка загрузки");
      } finally {
        setLoading(false);
      }
    })();
  }, [router, load]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!userId) return;
    setError(null);
    setBusy(true);
    try {
      await createRecalibration(userId, cycle, notes);
      setNotes("");
      await load(userId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка создания события");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <main className="mx-auto max-w-3xl px-6 py-16 text-sm opacity-60">Загрузка…</main>;
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold">Рекалибровка</h1>
        <p className="mt-2 text-sm opacity-70">
          Циклы: базовая точка → 30 дней → 90 дней → ретроспектива. Сравнение с базовой точкой
          и рекомендации по среде.
        </p>
      </header>

      {error && <p className="mb-4 text-sm text-orange-400">{error}</p>}

      {timeline && (
        <section className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-white/10 bg-white/5 p-5">
            <div className="text-sm opacity-70">Базовая точка</div>
            <div className="mt-1 text-3xl font-semibold">
              {timeline.baseline_score !== null ? timeline.baseline_score.toFixed(2) : "—"}
            </div>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-5">
            <div className="text-sm opacity-70">Тренд</div>
            <div className={`mt-1 text-lg font-medium ${TREND_TEXT[timeline.trend]}`}>
              {timeline.trend_label}
            </div>
          </div>
        </section>
      )}

      {timeline && timeline.recommendations.length > 0 && (
        <section className="mb-8 rounded-xl border border-white/10 bg-white/5 p-5">
          <h2 className="text-sm font-medium opacity-80">Рекомендации по развитию среды</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm opacity-80">
            {timeline.recommendations.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="mb-8">
        <h2 className="text-lg font-medium">История событий</h2>
        {timeline && timeline.events.length > 0 ? (
          <div className="mt-3 space-y-2">
            {timeline.events.map((ev) => (
              <div
                key={ev.id}
                className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-4 py-3"
              >
                <div>
                  <div className="text-sm font-medium">{CYCLE_LABEL[ev.cycle]}</div>
                  {ev.notes && <div className="mt-0.5 text-xs opacity-50">{ev.notes}</div>}
                </div>
                <div className="text-right">
                  <div className="text-lg font-semibold">
                    {ev.burnout_pressure_score !== null
                      ? ev.burnout_pressure_score.toFixed(2)
                      : "—"}
                    {ev.risk_level && (
                      <span className={`ml-2 text-xs ${RISK_TEXT[ev.risk_level]}`}>
                        ●
                      </span>
                    )}
                  </div>
                  <div className="text-xs opacity-50">Δ {formatDelta(ev.delta_vs_baseline)}</div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-3 text-sm opacity-60">Событий пока нет.</p>
        )}
      </section>

      <section className="rounded-xl border border-white/10 bg-white/5 p-5">
        <h2 className="text-lg font-medium">Новое событие рекалибровки</h2>
        <p className="mt-1 text-xs opacity-60">
          Привязывается к вашему последнему заполненному опроснику.
        </p>
        <form onSubmit={onCreate} className="mt-4 space-y-4">
          <label className="block">
            <span className="text-sm opacity-70">Цикл</span>
            <select
              value={cycle}
              onChange={(e) => setCycle(e.target.value as RecalibrationCycle)}
              className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-white/30"
            >
              {CYCLES.map((c) => (
                <option key={c} value={c} className="bg-neutral-900">
                  {CYCLE_LABEL[c]}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-sm opacity-70">Заметки (необязательно)</span>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-white/30"
            />
          </label>

          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-white/90 px-5 py-2 text-sm font-medium text-black disabled:opacity-40"
          >
            {busy ? "Создание…" : "Создать событие"}
          </button>
        </form>
      </section>

      <p className="mt-8 text-xs opacity-50">
        Рекомендации носят развивающий характер и предназначены для проверки человеком. Они не
        являются основанием для кадровых решений.
      </p>
    </main>
  );
}
