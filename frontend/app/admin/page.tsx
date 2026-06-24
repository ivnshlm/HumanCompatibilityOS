"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  createAdminUser,
  fetchAdminUsers,
  fetchMe,
  getToken,
  updateAdminUser,
  type AdminUser,
  type AdminUserPatch,
  type Me,
} from "@/lib/api";
import { Button, Card, EmptyState, Input, PageSkeleton, Select } from "@/components/ui";

// 3 primary roles + 2 advanced (kept for oversight/team scoping).
const ROLES: { value: Me["role"]; label: string }[] = [
  { value: "employee", label: "Сотрудник (тестируемый)" },
  { value: "hr", label: "HR (проверяет)" },
  { value: "admin", label: "Администратор" },
  { value: "team_lead", label: "Тимлид · расширенная" },
  { value: "ethics_reviewer", label: "Этич. ревьюер · расширенная" },
];

export default function AdminPage() {
  const router = useRouter();
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [meId, setMeId] = useState<string>("");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);

  // Create-user form
  const [nEmail, setNEmail] = useState("");
  const [nName, setNName] = useState("");
  const [nPassword, setNPassword] = useState("");
  const [nRole, setNRole] = useState<Me["role"]>("employee");
  const [nTeam, setNTeam] = useState("");
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    (async () => {
      try {
        const me = await fetchMe();
        setMeId(me.id);
        if (me.role !== "admin") {
          setAllowed(false);
          return;
        }
        setAllowed(true);
        setUsers(await fetchAdminUsers());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка загрузки");
        setAllowed(false);
      }
    })();
  }, [router]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    setCreated(null);
    try {
      const u = await createAdminUser({
        email: nEmail.trim(),
        password: nPassword,
        full_name: nName.trim(),
        role: nRole,
        team_id: nTeam.trim() || null,
      });
      setUsers((list) => [u, ...list]);
      setCreated(`Пользователь ${u.email} создан (${u.role}).`);
      setNEmail("");
      setNName("");
      setNPassword("");
      setNRole("employee");
      setNTeam("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось создать пользователя");
    } finally {
      setCreating(false);
    }
  }

  async function patch(id: string, body: AdminUserPatch) {
    setSavingId(id);
    setError(null);
    try {
      const updated = await updateAdminUser(id, body);
      setUsers((list) => list.map((u) => (u.id === id ? updated : u)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить");
    } finally {
      setSavingId(null);
    }
  }

  if (allowed === null) {
    return <PageSkeleton width="4xl" />;
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <header className="mb-8">
        <div className="text-[11px] font-semibold uppercase tracking-[0.09em] text-ink-faint">
          Администрирование
        </div>
        <h1 className="mt-1 text-3xl font-semibold text-ink">Управление пользователями</h1>
        <p className="mt-2 text-sm text-ink-muted">
          Роли, доступ и команды. Все изменения фиксируются в аудит-журнале.
        </p>
      </header>

      {!allowed ? (
        <EmptyState title="Доступ только для администратора" text="Экран управления пользователями доступен роли администратор." />
      ) : (
        <>
          {error && <p className="mb-4 text-sm text-orange-400">{error}</p>}
          {created && <p className="mb-4 text-sm text-emerald-400">{created}</p>}

          <Card className="mb-8">
            <div className="text-sm font-medium text-ink">Создать пользователя</div>
            <form onSubmit={onCreate} className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
              <Input type="email" required value={nEmail} onChange={(e) => setNEmail(e.target.value)} placeholder="email" />
              <Input required value={nName} onChange={(e) => setNName(e.target.value)} placeholder="Имя" />
              <Input
                type="password"
                required
                minLength={8}
                value={nPassword}
                onChange={(e) => setNPassword(e.target.value)}
                placeholder="Пароль (мин. 8)"
              />
              <Input value={nTeam} onChange={(e) => setNTeam(e.target.value)} placeholder="team_id (необязательно)" />
              <Select value={nRole} onChange={(e) => setNRole(e.target.value as Me["role"])}>
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value} className="bg-neutral-900">
                    {r.label}
                  </option>
                ))}
              </Select>
              <Button type="submit" disabled={creating}>
                {creating ? "Создание…" : "Создать"}
              </Button>
            </form>
          </Card>

          <div className="space-y-2">
            {users.map((u) => {
              const isSelf = u.id === meId;
              const saving = savingId === u.id;
              return (
                <Card key={u.id} className={u.is_active ? "" : "opacity-50"}>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium text-ink">
                        {u.full_name}
                        {isSelf && <span className="ml-2 text-xs text-ink-faint">(вы)</span>}
                      </div>
                      <div className="truncate text-xs text-ink-muted">{u.email}</div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <Select
                        value={u.role}
                        disabled={saving}
                        onChange={(e) => patch(u.id, { role: e.target.value as Me["role"] })}
                        className="w-auto px-2 py-1.5"
                      >
                        {ROLES.map((r) => (
                          <option key={r.value} value={r.value} className="bg-neutral-900">
                            {r.label}
                          </option>
                        ))}
                      </Select>

                      <Input
                        defaultValue={u.team_id ?? ""}
                        placeholder="team_id"
                        disabled={saving}
                        onBlur={(e) => {
                          const v = e.target.value.trim() || null;
                          if (v !== (u.team_id ?? null)) patch(u.id, { team_id: v });
                        }}
                        className="w-40 px-2 py-1.5 text-xs"
                      />

                      <button
                        type="button"
                        disabled={saving || isSelf}
                        onClick={() => patch(u.id, { is_active: !u.is_active })}
                        title={isSelf ? "Нельзя отключить свой аккаунт" : ""}
                        className={`rounded-control border px-3 py-1.5 text-xs font-medium disabled:opacity-40 ${
                          u.is_active
                            ? "border-emerald-400/30 text-emerald-400 hover:bg-emerald-400/5"
                            : "border-orange-400/30 text-orange-400 hover:bg-orange-400/5"
                        }`}
                      >
                        {u.is_active ? "Активен" : "Выключен"}
                      </button>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>

          <p className="mt-8 text-xs text-ink-faint">
            Роли «Тимлид» и «Этич. ревьюер» — расширенные: тимлид видит только свою команду,
            этический ревьюер ведёт надзор и читает аудит без права ставить review.
          </p>
        </>
      )}
    </main>
  );
}
