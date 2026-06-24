"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { fetchMe, getToken, type Me } from "@/lib/api";
import { cn } from "@/components/ui";

type Role = Me["role"];

const REVIEWER: Role[] = ["hr", "team_lead", "admin", "ethics_reviewer"];
const OVERSIGHT: Role[] = ["admin", "ethics_reviewer"];
const ADMIN: Role[] = ["admin"];

type NavItem = { href: string; label: string; roles?: Role[] };
type NavGroup = { title: string; items: NavItem[] };

const GROUPS: NavGroup[] = [
  { title: "Среда", items: [{ href: "/dashboard", label: "Дашборд", roles: REVIEWER }] },
  {
    title: "Человек",
    items: [
      { href: "/questionnaire", label: "Опросник" },
      { href: "/recalibration", label: "Рекалибровка" },
      { href: "/review", label: "Review", roles: REVIEWER },
    ],
  },
  { title: "Подбор", items: [{ href: "/hiring", label: "Подбор", roles: REVIEWER }] },
  {
    title: "Администрирование",
    items: [
      { href: "/audit", label: "Аудит", roles: OVERSIGHT },
      { href: "/admin", label: "Управление", roles: ADMIN },
    ],
  },
];

// Routes that render full-width without the app chrome.
const FULL_BLEED = new Set(["/", "/login"]);

function Brand() {
  return (
    <a href="/" className="flex items-center gap-2.5">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/hcos_logo.svg" alt="Human Compatibility OS" width={26} height={26} />
      <span className="text-sm font-semibold tracking-tight text-ink">Human Compatibility OS</span>
    </a>
  );
}

function visible(item: NavItem, role: Role | null): boolean {
  if (!item.roles) return true;
  return role !== null && item.roles.includes(role);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [role, setRole] = useState<Role | null>(null);

  useEffect(() => {
    if (!getToken()) {
      setRole(null);
      return;
    }
    fetchMe()
      .then((me) => setRole(me.role))
      .catch(() => setRole(null));
  }, [pathname]);

  // Login / home: clean full-bleed with a slim brand header.
  if (FULL_BLEED.has(pathname)) {
    return (
      <>
        <header className="border-b border-edge">
          <div className="mx-auto flex max-w-6xl items-center px-6 py-3">
            <Brand />
            <span className="ml-2 hidden text-xs text-ink-faint sm:inline">· Fabrika Sredy</span>
          </div>
        </header>
        {children}
      </>
    );
  }

  const groups = GROUPS.map((g) => ({
    ...g,
    items: g.items.filter((i) => visible(i, role)),
  })).filter((g) => g.items.length > 0);

  const NavLinks = ({ onNavigate }: { onNavigate?: () => void }) => (
    <>
      {groups.map((g) => (
        <div key={g.title} className="mb-4">
          <div className="px-3 text-[11px] font-semibold uppercase tracking-[0.09em] text-ink-faint">
            {g.title}
          </div>
          <div className="mt-1 space-y-0.5">
            {g.items.map((i) => {
              const active = pathname === i.href;
              return (
                <a
                  key={i.href}
                  href={i.href}
                  onClick={onNavigate}
                  className={cn(
                    "block rounded-control px-3 py-1.5 text-sm transition-colors",
                    active
                      ? "bg-surface font-medium text-ink"
                      : "text-ink-muted hover:bg-white/5 hover:text-ink",
                  )}
                >
                  {i.label}
                </a>
              );
            })}
          </div>
        </div>
      ))}
    </>
  );

  return (
    <div className="md:flex">
      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-edge bg-surface-2 px-3 py-4 md:flex">
        <div className="px-2 pb-4">
          <Brand />
        </div>
        <nav className="flex-1 overflow-y-auto">
          <NavLinks />
        </nav>
      </aside>

      {/* Mobile top bar with scrollable nav */}
      <div className="md:hidden">
        <header className="border-b border-edge px-4 py-3">
          <Brand />
        </header>
        <nav className="flex gap-1 overflow-x-auto border-b border-edge px-3 py-2">
          {groups.flatMap((g) =>
            g.items.map((i) => {
              const active = pathname === i.href;
              return (
                <a
                  key={i.href}
                  href={i.href}
                  className={cn(
                    "whitespace-nowrap rounded-control px-3 py-1.5 text-sm",
                    active ? "bg-surface text-ink" : "text-ink-muted hover:bg-white/5",
                  )}
                >
                  {i.label}
                </a>
              );
            }),
          )}
        </nav>
      </div>

      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
