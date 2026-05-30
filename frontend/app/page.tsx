const BLOCKS = [
  { title: "Давление выгорания", hint: "Burnout Pressure" },
  { title: "Устойчивость восстановления", hint: "Recovery Sustainability" },
  { title: "Коммуникационная энтропия", hint: "Communication Entropy" },
  { title: "Устойчивость лидерства", hint: "Leadership Stability" },
];

export default function Home() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <header className="mb-10">
        <h1 className="text-3xl font-semibold">Human Compatibility OS</h1>
        <p className="mt-2 text-sm opacity-70">
          Мониторинг выгорания и устойчивости среды. «Среда важнее героизма.»
        </p>
        <nav className="mt-5 flex gap-3 text-sm">
          <a
            href="/login"
            className="rounded-lg bg-white/90 px-4 py-2 font-medium text-black"
          >
            Войти
          </a>
          <a
            href="/questionnaire"
            className="rounded-lg border border-white/15 px-4 py-2 font-medium"
          >
            Пройти опросник
          </a>
          <a
            href="/dashboard"
            className="rounded-lg border border-white/15 px-4 py-2 font-medium"
          >
            Дашборд
          </a>
          <a
            href="/recalibration"
            className="rounded-lg border border-white/15 px-4 py-2 font-medium"
          >
            Рекалибровка
          </a>
          <a
            href="/review"
            className="rounded-lg border border-white/15 px-4 py-2 font-medium"
          >
            Review
          </a>
        </nav>
      </header>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {BLOCKS.map((b) => (
          <div
            key={b.hint}
            className="rounded-xl border border-white/10 bg-white/5 p-5"
          >
            <div className="text-lg font-medium">{b.title}</div>
            <div className="mt-1 text-xs uppercase tracking-wide opacity-50">
              {b.hint}
            </div>
            <div className="mt-4 text-sm opacity-60">
              <a href="/dashboard" className="underline underline-offset-4 hover:opacity-100">
                Открыть на дашборде
              </a>
            </div>
          </div>
        ))}
      </section>

      <p className="mt-10 text-xs opacity-50">
        Светофор-индикаторы не являются основанием для кадровых решений.
        Все выводы требуют проверки человеком.
      </p>
    </main>
  );
}
