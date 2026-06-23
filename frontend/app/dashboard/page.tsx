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
  type EnvironmentMetrics,
  type Me,
  type OnboardingHealth,
  type PilotMetric,
  type TeamDashboard,
} from "@/lib/api";
import { NO_DECISION_DISCLAIMER } from "@/lib/risk";
import {
  AnonymizedNotice,
  Card,
  DistributionBar,
  Disclaimer,
  EmptyState,
  RiskBadge,
  SectionHeader,
  StatCard,
  Table,
  TD,
  TH,
  THead,
  TR,
} from "@/components/ui";

const REVIEWER_ROLES = new Set(["hr", "team_lead", "admin", "ethics_reviewer"]);

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
    return <main className="mx-auto max-w-6xl px-6 py-16 text-sm text-ink-muted">Загрузка…</main>;
  }

  const notReviewer = me && !REVIEWER_ROLES.has(me.role);
  const noTeam = me && REVIEWER_ROLES.has(me.role) && !me.team_id;

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <header className="mb-8">
        <div className="text-[11px] font-semibold uppercase tracking-[0.09em] text-ink-faint">
          Среда команды
        </div>
        <h1 className="mt-1 text-3xl font-semibold text-ink">Дашборд среды</h1>
        <p className="mt-2 text-sm text-ink-muted">Агрегаты по команде. Среда важнее героизма.</p>
      </header>

      {error && <p className="mb-4 text-sm text-orange-400">{error}</p>}

      {notReviewer && (
        <EmptyState
          title="Доступ только для проверяющих ролей"
          text="Дашборд доступен ролям HR, руководитель команды, администратор и этический ревьюер."
        />
      )}

      {noTeam && (
        <EmptyState
          title="Команда не привязана"
          text="К вашему профилю не привязана команда (team_id). Привяжите команду, чтобы видеть агрегаты."
        />
      )}

      {dashboard && !dashboard.sufficient_data && (
        <AnonymizedNotice cohortSize={dashboard.cohort_size} />
      )}

      {dashboard && dashboard.sufficient_data && (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-muted">
            <span>Участников в выборке: {dashboard.cohort_size}</span>
            {dashboard.interpretation && (
              <>
                <span className="text-ink-faint">·</span>
                <span>{dashboard.interpretation}</span>
              </>
            )}
          </div>
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {dashboard.blocks.map((b) => (
              <StatCard
                key={b.block}
                eyebrow={b.label_en}
                title={b.label}
                value={b.score.toFixed(2)}
                caption="по шкале 1–5 (выше — больше риска)"
                badge={<RiskBadge level={b.risk_level} />}
                footer={<DistributionBar distribution={b.distribution} />}
              />
            ))}
          </section>
        </>
      )}

      {pilot && pilot.sufficient_data && pilot.headline && (
        <section className="mt-10">
          <SectionHeader
            eyebrow="Пилот"
            title="Изменение за 90 дней"
            right={
              <span className="text-xs text-ink-muted">
                Базовая точка → 90 дней · снижение = улучшение
              </span>
            }
          />
          <Card>
            <div className="flex flex-wrap items-end gap-6">
              <div>
                <div className="text-[11px] uppercase tracking-[0.09em] text-ink-faint">
                  {pilot.headline.label} (цель {pilot.target_pct}%)
                </div>
                <div
                  className={`text-4xl font-semibold tabular-nums ${
                    pilot.target_met ? "text-emerald-400" : "text-amber-400"
                  }`}
                >
                  {pilot.headline.pct_change > 0 ? "+" : ""}
                  {pilot.headline.pct_change}%
                </div>
              </div>
              <div className="text-sm tabular-nums text-ink-muted">
                {pilot.headline.baseline_mean.toFixed(2)} → {pilot.headline.latest_mean.toFixed(2)}
              </div>
              <div className="text-sm text-ink-muted">
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
                  className="flex items-center justify-between rounded-control border border-edge-2 bg-surface-2 px-3 py-2 text-sm"
                >
                  <span className="text-ink">{b.label}</span>
                  <span className="flex items-center gap-2 tabular-nums">
                    <span className="text-ink-faint">
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
          </Card>
        </section>
      )}

      {onboarding && onboarding.sufficient_data && (
        <section className="mt-10">
          <SectionHeader
            eyebrow="Онбординг"
            title="Адаптация новых сотрудников"
            right={
              <span className="text-xs text-ink-muted">
                Новички (&lt; {onboarding.window_days} дней) vs устоявшаяся команда
              </span>
            }
          />
          <Card>
            <div className="flex flex-wrap items-end gap-x-8 gap-y-4">
              <div>
                <div className="text-[11px] uppercase tracking-[0.09em] text-ink-faint">
                  давление у новичков
                </div>
                <div className="text-4xl font-semibold tabular-nums text-ink">
                  {onboarding.new_hire_mean?.toFixed(2) ?? "—"}
                </div>
              </div>
              <div className="text-sm text-ink-muted">
                устоявшаяся команда:{" "}
                <span className="tabular-nums text-ink">
                  {onboarding.tenured_mean !== null ? onboarding.tenured_mean.toFixed(2) : "нет данных"}
                </span>
              </div>
              {onboarding.integration_friction !== null && (
                <div className="text-sm text-ink-muted">
                  трение интеграции:{" "}
                  <span
                    className={`tabular-nums ${
                      onboarding.friction_flag ? "text-orange-400" : "text-emerald-400"
                    }`}
                  >
                    {onboarding.integration_friction > 0 ? "+" : ""}
                    {onboarding.integration_friction.toFixed(2)}
                    {onboarding.friction_flag ? " (внимание)" : " (норма)"}
                  </span>
                </div>
              )}
              <div className="text-sm text-ink-muted">
                новичков в высоком риске:{" "}
                <span className="font-medium text-ink">{onboarding.at_risk_count}</span>
              </div>
            </div>
          </Card>
        </section>
      )}

      {metrics && metrics.aggregates.length > 0 && (
        <section className="mt-10">
          <SectionHeader eyebrow="Телеметрия" title="Метрики среды" />
          <Table>
            <THead>
              <tr>
                <TH>Метрика</TH>
                <TH>N</TH>
                <TH>Среднее</TH>
                <TH>Мин</TH>
                <TH>Макс</TH>
              </tr>
            </THead>
            <tbody>
              {metrics.aggregates.map((m) => (
                <TR key={m.metric_type}>
                  <TD className="text-ink">{m.metric_type}</TD>
                  <TD className="tabular-nums">{m.count}</TD>
                  <TD className="tabular-nums">{m.mean.toFixed(2)}</TD>
                  <TD className="tabular-nums">{m.minimum.toFixed(2)}</TD>
                  <TD className="tabular-nums">{m.maximum.toFixed(2)}</TD>
                </TR>
              ))}
            </tbody>
          </Table>
        </section>
      )}

      <Disclaimer className="mt-10">{NO_DECISION_DISCLAIMER}</Disclaimer>
    </main>
  );
}
