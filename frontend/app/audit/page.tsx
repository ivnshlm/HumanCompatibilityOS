"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { fetchAudit, fetchMe, getToken, type AuditEntry } from "@/lib/api";

const OVERSIGHT_ROLES = new Set(["admin", "ethics_reviewer"]);

export default function AuditPage() {
  const router = useRouter();
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    (async () => {
      try {
        const me = await fetchMe();
        if (!OVERSIGHT_ROLES.has(me.role)) {
          setAllowed(false);
          return;
        }
        setAllowed(true);
        setEntries(await fetchAudit(200));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка загрузки");
        setAllowed(false);
      }
    })();
  }, [router]);

  if (allowed === null) {
    return <main className="mx-auto max-w-4xl px-6 py-16 text-sm opacity-60">Загрузка…</main>;
  }

  if (!allowed) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-16">
        <h1 className="text-2xl font-semibold">Аудит</h1>
        <p className="mt-4 rounded-xl border border-white/10 bg-white/5 p-6 text-sm opacity-80">
          Аудит-лог доступен только надзорным ролям (администратор, этический ревьюер).
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold">Аудит</h1>
        <p className="mt-2 text-sm opacity-70">
          Журнал действий и просмотров. Подотчётность вместо скрытого профайлинга.
        </p>
      </header>

      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}

      <div className="overflow-hidden rounded-xl border border-white/10">
        <table className="w-full text-sm">
          <thead className="bg-white/5 text-left text-xs uppercase tracking-wide opacity-60">
            <tr>
              <th className="px-4 py-2 font-medium">Время</th>
              <th className="px-4 py-2 font-medium">Действие</th>
              <th className="px-4 py-2 font-medium">Объект</th>
              <th className="px-4 py-2 font-medium">Детали</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.id} className="border-t border-white/10 align-top">
                <td className="px-4 py-2 whitespace-nowrap text-xs opacity-60">
                  {new Date(e.created_at).toLocaleString("ru-RU")}
                </td>
                <td className="px-4 py-2 font-medium">{e.action}</td>
                <td className="px-4 py-2 text-xs opacity-70">
                  {e.entity_type ?? "—"}
                  {e.entity_id ? ` · ${e.entity_id.slice(0, 8)}…` : ""}
                </td>
                <td className="px-4 py-2 text-xs opacity-60">
                  {e.detail ? JSON.stringify(e.detail) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {entries.length === 0 && <p className="mt-4 text-sm opacity-60">Записей нет.</p>}
    </main>
  );
}
