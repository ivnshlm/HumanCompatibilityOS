import { Card } from "@/components/ui";

const BLOCKS = [
  { title: "Давление среды", hint: "Burnout Pressure" },
  { title: "Устойчивость восстановления", hint: "Recovery Sustainability" },
  { title: "Коммуникационная энтропия", hint: "Communication Entropy" },
  { title: "Устойчивость лидерства", hint: "Leadership Stability" },
];

const NAV = [
  { href: "/questionnaire", label: "Пройти опросник" },
  { href: "/dashboard", label: "Дашборд" },
  { href: "/recalibration", label: "Рекалибровка" },
  { href: "/review", label: "Review" },
  { href: "/hiring", label: "Подбор" },
  { href: "/audit", label: "Аудит" },
  { href: "/admin", label: "Админ" },
];

export default function Home() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <header className="mb-10">
        <div className="text-[11px] font-semibold uppercase tracking-[0.09em] text-ink-faint">
          Fabrika Sredy
        </div>
        <h1 className="mt-1 text-4xl font-semibold text-ink">Среда важнее героизма</h1>
        <p className="mt-3 max-w-xl text-sm leading-relaxed text-ink-muted">
          Операционная платформа, которая видит давление среды — выгорание, перегрузку,
          коммуникационный шум — и помогает его снизить. Сигналы для проверки человеком, не
          оценка людей.
        </p>
        <nav className="mt-6 flex flex-wrap gap-2">
          <a
            href="/login"
            className="rounded-control bg-white/90 px-4 py-2 text-sm font-medium text-black hover:bg-white"
          >
            Войти
          </a>
          {NAV.map((n) => (
            <a
              key={n.href}
              href={n.href}
              className="rounded-control border border-white/15 px-4 py-2 text-sm font-medium text-ink hover:bg-white/5"
            >
              {n.label}
            </a>
          ))}
        </nav>
      </header>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {BLOCKS.map((b) => (
          <Card key={b.hint}>
            <div className="text-[11px] uppercase tracking-[0.09em] text-ink-faint">{b.hint}</div>
            <div className="mt-1 text-lg font-medium text-ink">{b.title}</div>
            <div className="mt-4 text-sm">
              <a href="/dashboard" className="text-ink-muted underline-offset-4 hover:text-ink hover:underline">
                Открыть на дашборде →
              </a>
            </div>
          </Card>
        ))}
      </section>

      <p className="mt-10 text-xs text-ink-faint">
        Светофор-индикаторы не являются основанием для кадровых решений. Все выводы требуют
        проверки человеком.
      </p>
    </main>
  );
}
