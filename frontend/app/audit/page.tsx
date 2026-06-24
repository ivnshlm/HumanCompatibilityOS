"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { fetchAudit, fetchMe, getToken, type AuditEntry } from "@/lib/api";
import { EmptyState, PageSkeleton, Table, TD, TH, THead, TR } from "@/components/ui";

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
    return <PageSkeleton width="4xl" />;
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <header className="mb-8">
        <div className="text-[11px] font-semibold uppercase tracking-[0.09em] text-ink-faint">
          Надзор
        </div>
        <h1 className="mt-1 text-3xl font-semibold text-ink">Аудит</h1>
        <p className="mt-2 text-sm text-ink-muted">
          Журнал действий и просмотров. Подотчётность вместо скрытого профайлинга.
        </p>
      </header>

      {!allowed ? (
        <EmptyState
          title="Доступ только для надзора"
          text="Аудит-журнал доступен ролям администратор и этический ревьюер."
        />
      ) : (
        <>
          {error && <p className="mb-4 text-sm text-orange-400">{error}</p>}
          {entries.length === 0 ? (
            <EmptyState icon="✓" title="Записей нет" text="Действия появятся здесь по мере работы." />
          ) : (
            <Table>
              <THead>
                <tr>
                  <TH>Время</TH>
                  <TH>Действие</TH>
                  <TH>Объект</TH>
                  <TH>Детали</TH>
                </tr>
              </THead>
              <tbody>
                {entries.map((e) => (
                  <TR key={e.id}>
                    <TD className="whitespace-nowrap text-xs text-ink-muted">
                      {new Date(e.created_at).toLocaleString("ru-RU")}
                    </TD>
                    <TD className="font-medium text-ink">{e.action}</TD>
                    <TD className="text-xs text-ink-muted">
                      {e.entity_type ?? "—"}
                      {e.entity_id ? ` · ${e.entity_id.slice(0, 8)}…` : ""}
                    </TD>
                    <TD className="text-xs text-ink-faint">
                      {e.detail ? JSON.stringify(e.detail) : "—"}
                    </TD>
                  </TR>
                ))}
              </tbody>
            </Table>
          )}
        </>
      )}
    </main>
  );
}
