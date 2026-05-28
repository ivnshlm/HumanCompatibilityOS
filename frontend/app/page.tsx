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
            <div className="mt-4 text-sm opacity-60">— нет данных (Фаза 0)</div>
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
