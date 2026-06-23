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
    return <main className="mx-auto max-w-4xl px-6 py-16 text-sm opacity-60">Загрузка…</main>;
  }

  if (!allowed) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-16">
        <h1 className="text-2xl font-semibold">Управление пользователями</h1>
        <p className="mt-4 rounded-xl border border-white/10 bg-white/5 p-6 text-sm opacity-80">
          Экран доступен только администратору.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold">Управление пользователями</h1>
        <p className="mt-2 text-sm opacity-70">
          Роли, доступ и команды. Все изменения фиксируются в аудит-журнале.
        </p>
      </header>

      {error && <p className="mb-4 text-sm text-orange-400">{error}</p>}
      {created && <p className="mb-4 text-sm text-emerald-400">{created}</p>}

      <form
        onSubmit={onCreate}
        className="mb-8 rounded-xl border border-white/10 bg-white/5 p-4"
      >
        <div className="text-sm font-medium">Создать пользователя</div>
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          <input
            type="email"
            required
            value={nEmail}
            onChange={(e) => setNEmail(e.target.value)}
            placeholder="email"
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none placeholder:opacity-40 focus:border-white/30"
          />
          <input
            required
            value={nName}
            onChange={(e) => setNName(e.target.value)}
            placeholder="Имя"
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none placeholder:opacity-40 focus:border-white/30"
          />
          <input
            type="password"
            required
            minLength={8}
            value={nPassword}
            onChange={(e) => setNPassword(e.target.value)}
            placeholder="Пароль (мин. 8)"
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none placeholder:opacity-40 focus:border-white/30"
          />
          <input
            value={nTeam}
            onChange={(e) => setNTeam(e.target.value)}
            placeholder="team_id (необязательно)"
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none placeholder:opacity-40 focus:border-white/30"
          />
          <select
            value={nRole}
            onChange={(e) => setNRole(e.target.value as Me["role"])}
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-white/30"
          >
            {ROLES.map((r) => (
              <option key={r.value} value={r.value} className="bg-neutral-900">
                {r.label}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={creating}
            className="rounded-lg bg-white/90 px-4 py-2 text-sm font-medium text-black disabled:opacity-50"
          >
            {creating ? "Создание…" : "Создать"}
          </button>
        </div>
      </form>

      <div className="space-y-2">
        {users.map((u) => {
          const isSelf = u.id === meId;
          const saving = savingId === u.id;
          return (
            <div
              key={u.id}
              className={`rounded-xl border border-white/10 bg-white/5 p-4 ${
                u.is_active ? "" : "opacity-50"
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium">
                    {u.full_name}
                    {isSelf && <span className="ml-2 text-xs opacity-50">(вы)</span>}
                  </div>
                  <div className="truncate text-xs opacity-50">{u.email}</div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <select
                    value={u.role}
                    disabled={saving}
                    onChange={(e) => patch(u.id, { role: e.target.value as Me["role"] })}
                    className="rounded-lg border border-white/10 bg-white/5 px-2 py-1.5 text-sm outline-none focus:border-white/30"
                  >
                    {ROLES.map((r) => (
                      <option key={r.value} value={r.value} className="bg-neutral-900">
                        {r.label}
                      </option>
                    ))}
                  </select>

                  <input
                    defaultValue={u.team_id ?? ""}
                    placeholder="team_id"
                    disabled={saving}
                    onBlur={(e) => {
                      const v = e.target.value.trim() || null;
                      if (v !== (u.team_id ?? null)) patch(u.id, { team_id: v });
                    }}
                    className="w-40 rounded-lg border border-white/10 bg-white/5 px-2 py-1.5 text-xs outline-none placeholder:opacity-30 focus:border-white/30"
                  />

                  <button
                    type="button"
                    disabled={saving || isSelf}
                    onClick={() => patch(u.id, { is_active: !u.is_active })}
                    title={isSelf ? "Нельзя отключить свой аккаунт" : ""}
                    className={`rounded-lg border px-3 py-1.5 text-xs font-medium disabled:opacity-40 ${
                      u.is_active
                        ? "border-emerald-400/30 text-emerald-400 hover:bg-emerald-400/5"
                        : "border-orange-400/30 text-orange-400 hover:bg-orange-400/5"
                    }`}
                  >
                    {u.is_active ? "Активен" : "Выключен"}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <p className="mt-8 text-xs opacity-50">
        Роли «Тимлид» и «Этич. ревьюер» — расширенные: тимлид видит только свою команду,
        этический ревьюер ведёт надзор и читает аудит без права ставить review.
      </p>
    </main>
  );
}
