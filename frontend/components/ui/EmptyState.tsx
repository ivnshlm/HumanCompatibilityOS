import type { ReactNode } from "react";

import { cn } from "./cn";

type EmptyStateProps = {
  icon?: ReactNode;
  title: string;
  text?: ReactNode;
  /** Dashed framing for the cohort-anonymization case. */
  dashed?: boolean;
  className?: string;
};

/** Friendly empty/placeholder state — calm tone, never alarmist. */
export function EmptyState({ icon, title, text, dashed = false, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-2 rounded-card px-6 py-10 text-center",
        dashed ? "border border-dashed border-edge" : "border border-edge bg-surface-2",
        className,
      )}
    >
      {icon && (
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/5 text-lg text-ink-faint">
          {icon}
        </div>
      )}
      <div className="text-sm font-medium text-ink">{title}</div>
      {text && <div className="max-w-sm text-xs text-ink-muted">{text}</div>}
    </div>
  );
}
