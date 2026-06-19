"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  fetchEnvironmentMetrics,
  fetchMe,
  fetchOnboarding,
  fetchPilotMetric,
  fetchTeamDashboard,
  getToken,
  type BlockAggregate,
  type EnvironmentMetrics,
  type Me,
  type OnboardingHealth,
  type PilotMetric,
  type RiskLevel,
  type TeamDashboard,
} from "@/lib/api";

const REVIEWER_ROLES = new Set(["hr", "team_lead", "admin", "ethics_reviewer"]);

const RISK_LABEL: Record<RiskLevel, string> = {
  low: "Низкий",
  medium: "Средний",
  high: "Высокий",
};

const RISK_TEXT: Record<RiskLevel, string> = {
  low: "text-emerald-400",
  medium: "text-amber-400",
  high: "text-red-400",
};

const RISK_DOT: Record<RiskLevel, string> = {
  low: "bg-emerald-400",
  medium: "bg-amber-400",
  high: "bg-red-400",
};

function BlockCard({ block }: { block: BlockAggregate }) {
  const total =
    block.distribution.low + block.distribution.medium + block.distribution.high;
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-lg font-medium">{block.label}</div>
          <div className="text-xs uppercase tracking-wide opacity-50">{block.label_en}</div>
        </div>
        <span className={`mt-1 inline-flex items-center gap-2 text-sm font-medium ${RISK_TEXT[block.risk_level]}`}>
          <span className={`h-2.5 w-2.5 rounded-full ${RISK_DOT[block.risk_level]}`} />
          {RISK_LABEL[block.risk_level]}
        </span>
      </div>

      <div className="mt-4 text-4xl font-semibold">{block.score.toFixed(2)}</div>
      <div className="text-xs opacity-50">по шкале 1–5 (выше — больше риска)</div>

      {total > 0 && (
        <div className="mt-4">
          <div className="flex h-2 overflow-hidden rounded-full bg-white/10">
            <div className="bg-emerald-400/80" style={{ width: `${(block.distribution.low / total) * 100}%` }} />
            <div className="bg-amber-400/80" style={{ width: `${(block.distribution.medium / total) * 100}%` }} />
            <div className="bg-red-400/80" style={{ width: `${(block.distribution.high / total) * 100}%` }} />
          </div>
          <div className="mt-2 flex gap-4 text-xs opacity-60">
            <span>низкий {block.distribution.low}</span>
            <span>средний {block.distribution.medium}</span>
            <span>высокий {block.distribution.high}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [dashboard, setDashboard] = useState<TeamDashboard | null>(null);
  const [metrics, setMetrics] = useState<EnvironmentMetrics | null>(null);
  const [pilot, setPilot] = useState<PilotMetric | null>(null);
  const [onboarding, setOnboarding] = useState<OnboardingHealth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    (async () => {
      try {
        const profile = await fetchMe();
        setMe(profile);
        if (!REVIEWER_ROLES.has(profile.role) || !profile.team_id) return;
        const [dash, env, pm, ob] = await Promise.all([
          fetchTeamDashboard(profile.team_id),
          fetchEnvironmentMetrics(profile.team_id),
          fetchPilotMetric(profile.team_id).catch(() => null),
          fetchOnboarding(profile.team_id).catch(() => null),
        ]);
        setDashboard(dash);
        setMetrics(env);
        setPilot(pm);
        setOnboarding(ob);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка загрузки");
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  if (loading) {
    return <main className="mx-auto max-w-5xl px-6 py-16 text-sm opacity-60">Загрузка…</main>;
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold">Дашборд среды</h1>
        <p className="mt-2 text-sm opacity-70">
          Агрегаты по команде. Среда важнее героизма.
        </p>
      </header>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {me && !REVIEWER_ROLES.has(me.role) && (
        <div className="rounded-xl border border-white/10 bg-white/5 p-6 text-sm opacity-80">
          Дашборд доступен только ролям HR, руководитель команды, администратор и этический ревьюер.
        </div>
      )}

      {me && REVIEWER_ROLES.has(me.role) && !me.team_id && (
        <div className="rounded-xl border border-white/10 bg-white/5 p-6 text-sm opacity-80">
          К вашему профилю не привязана команда (team_id). Привяжите команду, чтобы видеть агрегаты.
        </div>
      )}

      {dashboard && !dashboard.sufficient_data && (
        <div className="rounded-xl border border-amber-400/30 bg-amber-400/5 p-6 text-sm opacity-90">
          {dashboard.notice ??
            "Недостаточно данных для командного вывода. Чтобы защитить участников от деанонимизации, командная аналитика доступна только при выборке от 3 человек."}
          <div className="mt-1 text-xs opacity-60">
            Участников с данными: {dashboard.cohort_size}
          </div>
        </div>
      )}

      {dashboard && dashboard.sufficient_data && (
        <>
          <div className="mb-4 text-xs opacity-60">
            Участников в выборке: {dashboard.cohort_size}
          </div>
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {dashboard.blocks.map((b) => (
              <BlockCard key={b.block} block={b} />
            ))}
          </section>
        </>
      )}

      {pilot && pilot.sufficient_data && pilot.headline && (
        <section className="mt-10 rounded-xl border border-white/10 bg-white/5 p-5">
          <h2 className="text-lg font-medium">Пилотная метрика — изменение за 90 дней</h2>
          <p className="mt-1 text-xs opacity-50">
            Базовая точка → 90 дней. Снижение = улучшение среды.
          </p>

          <div className="mt-4 flex flex-wrap items-end gap-6">
            <div>
              <div className="text-xs opacity-50">{pilot.headline.label} (цель {pilot.target_pct}%)</div>
              <div
                className={`text-3xl font-semibold ${
                  pilot.target_met ? "text-emerald-400" : "text-amber-400"
                }`}
              >
                {pilot.headline.pct_change > 0 ? "+" : ""}
                {pilot.headline.pct_change}%
              </div>
            </div>
            <div className="text-sm opacity-70">
              {pilot.headline.baseline_mean.toFixed(2)} → {pilot.headline.latest_mean.toFixed(2)}
            </div>
            <div className="text-sm">
              Цель:{" "}
              <span className={pilot.target_met ? "text-emerald-400" : "text-amber-400"}>
                {pilot.target_met ? "достигнута" : "не достигнута"}
              </span>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {pilot.blocks.map((b) => (
              <div
                key={b.key}
                className="flex items-center justify-between rounded-lg border border-white/10 px-3 py-2 text-sm"
              >
                <span className="opacity-80">{b.label}</span>
                <span className="flex items-center gap-2">
                  <span className="opacity-50">
                    {b.baseline_mean.toFixed(2)} → {b.latest_mean.toFixed(2)}
                  </span>
                  <span className={b.improved ? "text-emerald-400" : "text-amber-400"}>
                    {b.pct_change > 0 ? "+" : ""}
                    {b.pct_change}%
                  </span>
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {onboarding && onboarding.sufficient_data && (
        <section className="mt-10 rounded-xl border border-white/10 bg-white/5 p-5">
          <h2 className="text-lg font-medium">Онбординг — адаптация новых сотрудников</h2>
          <p className="mt-1 text-xs opacity-50">
            Новички (в команде &lt; {onboarding.window_days} дней) против устоявшейся команды.
          </p>
          <div className="mt-4 flex flex-wrap items-end gap-6">
            <div>
              <div className="text-xs opacity-50">давление у новичков</div>
              <div className="text-3xl font-semibold">
                {onboarding.new_hire_mean?.toFixed(2) ?? "—"}
              </div>
            </div>
            <div className="text-sm opacity-70">
              устоявшаяся команда:{" "}
              {onboarding.tenured_mean !== null ? onboarding.tenured_mean.toFixed(2) : "нет данных"}
            </div>
            {onboarding.integration_friction !== null && (
              <div className="text-sm">
                трение интеграции:{" "}
                <span className={onboarding.friction_flag ? "text-red-400" : "text-emerald-400"}>
                  {onboarding.integration_friction > 0 ? "+" : ""}
                  {onboarding.integration_friction.toFixed(2)}
                  {onboarding.friction_flag ? " (внимание)" : " (норма)"}
                </span>
              </div>
            )}
            <div className="text-sm opacity-70">
              новичков в высоком риске: <span className="font-medium">{onboarding.at_risk_count}</span>
            </div>
          </div>
        </section>
      )}

      {metrics && metrics.aggregates.length > 0 && (
        <section className="mt-10">
          <h2 className="text-lg font-medium">Метрики среды</h2>
          <div className="mt-3 overflow-hidden rounded-xl border border-white/10">
            <table className="w-full text-sm">
              <thead className="bg-white/5 text-left text-xs uppercase tracking-wide opacity-60">
                <tr>
                  <th className="px-4 py-2 font-medium">Метрика</th>
                  <th className="px-4 py-2 font-medium">N</th>
                  <th className="px-4 py-2 font-medium">Среднее</th>
                  <th className="px-4 py-2 font-medium">Мин</th>
                  <th className="px-4 py-2 font-medium">Макс</th>
                </tr>
              </thead>
              <tbody>
                {metrics.aggregates.map((m) => (
                  <tr key={m.metric_type} className="border-t border-white/10">
                    <td className="px-4 py-2">{m.metric_type}</td>
                    <td className="px-4 py-2">{m.count}</td>
                    <td className="px-4 py-2">{m.mean.toFixed(2)}</td>
                    <td className="px-4 py-2">{m.minimum.toFixed(2)}</td>
                    <td className="px-4 py-2">{m.maximum.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <p className="mt-10 text-xs opacity-50">
        Светофор-индикаторы не являются основанием для кадровых решений. Все выводы требуют
        проверки человеком. Данные показываются только при достаточном размере выборки.
      </p>
    </main>
  );
}
