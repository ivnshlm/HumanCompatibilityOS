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
import { RISK_DOT } from "@/lib/risk";
import {
  Button,
  Card,
  Disclaimer,
  EmptyState,
  Field,
  PageSkeleton,
  SectionHeader,
  Select,
  Sparkline,
  StatCard,
  Textarea,
} from "@/components/ui";

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
  insufficient: "text-ink-faint",
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
    setTimeline(await fetchRecalibration(uid));
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
    return <PageSkeleton width="3xl" />;
  }

  const trendPoints =
    timeline?.events
      .map((e) => e.burnout_pressure_score)
      .filter((s): s is number => s !== null) ?? [];

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <header className="mb-8">
        <div className="text-[11px] font-semibold uppercase tracking-[0.09em] text-ink-faint">
          Динамика
        </div>
        <h1 className="mt-1 text-3xl font-semibold text-ink">Рекалибровка</h1>
        <p className="mt-2 text-sm text-ink-muted">
          Циклы: базовая точка → 30 дней → 90 дней → ретроспектива. Сравнение с базовой точкой и
          рекомендации по среде.
        </p>
      </header>

      {error && <p className="mb-4 text-sm text-orange-400">{error}</p>}

      {timeline && (
        <section className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <StatCard
            eyebrow="Базовая точка"
            value={timeline.baseline_score !== null ? timeline.baseline_score.toFixed(2) : "—"}
            caption="давление среды на старте"
          />
          <StatCard
            eyebrow="Тренд"
            value={<span className={`text-2xl ${TREND_TEXT[timeline.trend]}`}>{timeline.trend_label}</span>}
            footer={
              trendPoints.length >= 2 ? (
                <Sparkline points={trendPoints} className={TREND_TEXT[timeline.trend]} width={140} />
              ) : undefined
            }
          />
        </section>
      )}

      {timeline && timeline.recommendations.length > 0 && (
        <section className="mb-8">
          <SectionHeader title="Рекомендации по развитию среды" />
          <Card>
            <ul className="list-disc space-y-1.5 pl-5 text-sm text-ink">
              {timeline.recommendations.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </Card>
        </section>
      )}

      <section className="mb-8">
        <SectionHeader title="История событий" />
        {timeline && timeline.events.length > 0 ? (
          <div className="space-y-2">
            {timeline.events.map((ev) => (
              <Card key={ev.id} variant="inset" className="flex items-center justify-between px-4 py-3">
                <div>
                  <div className="text-sm font-medium text-ink">{CYCLE_LABEL[ev.cycle]}</div>
                  {ev.notes && <div className="mt-0.5 text-xs text-ink-muted">{ev.notes}</div>}
                </div>
                <div className="text-right">
                  <div className="flex items-center justify-end gap-2 text-lg font-semibold tabular-nums text-ink">
                    {ev.burnout_pressure_score !== null ? ev.burnout_pressure_score.toFixed(2) : "—"}
                    {ev.risk_level && (
                      <span className={`h-2 w-2 rounded-full ${RISK_DOT[ev.risk_level]}`} />
                    )}
                  </div>
                  <div className="text-xs tabular-nums text-ink-faint">
                    Δ {formatDelta(ev.delta_vs_baseline)}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState title="Событий пока нет" text="Создайте первое событие рекалибровки ниже." />
        )}
      </section>

      <section>
        <SectionHeader title="Новое событие рекалибровки" />
        <Card>
          <p className="text-xs text-ink-muted">
            Привязывается к вашему последнему заполненному опроснику.
          </p>
          <form onSubmit={onCreate} className="mt-4 space-y-4">
            <Field label="Цикл">
              <Select value={cycle} onChange={(e) => setCycle(e.target.value as RecalibrationCycle)}>
                {CYCLES.map((c) => (
                  <option key={c} value={c} className="bg-neutral-900">
                    {CYCLE_LABEL[c]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Заметки (необязательно)">
              <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
            </Field>
            <Button type="submit" disabled={busy}>
              {busy ? "Создание…" : "Создать событие"}
            </Button>
          </form>
        </Card>
      </section>

      <Disclaimer className="mt-8">
        Рекомендации носят развивающий характер и предназначены для проверки человеком. Они не
        являются основанием для кадровых решений.
      </Disclaimer>
    </main>
  );
}
