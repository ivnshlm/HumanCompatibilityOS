"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { login, setToken } from "@/lib/api";
import { Button, Card, Field, Input } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const { access_token } = await login(email, password);
      setToken(access_token);
      router.push("/questionnaire");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка входа");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-md px-6 py-20">
      <div className="text-[11px] font-semibold uppercase tracking-[0.09em] text-ink-faint">
        Human Compatibility OS
      </div>
      <h1 className="mt-1 text-3xl font-semibold text-ink">Вход</h1>
      <p className="mt-2 text-sm text-ink-muted">Среда важнее героизма.</p>

      <Card className="mt-6">
        <form onSubmit={onSubmit} className="space-y-4">
          <Field label="Email">
            <Input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </Field>
          <Field label="Пароль">
            <Input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>

          {error && <p className="text-sm text-orange-400">{error}</p>}

          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "Вход…" : "Войти"}
          </Button>
        </form>
      </Card>
    </main>
  );
}
