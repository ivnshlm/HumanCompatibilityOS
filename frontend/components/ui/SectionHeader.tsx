import type { ReactNode } from "react";

import { cn } from "./cn";

type SectionHeaderProps = {
  /** Small uppercase label above the title. */
  eyebrow?: string;
  title: ReactNode;
  /** Optional right-aligned slot (filters, actions). */
  right?: ReactNode;
  className?: string;
};

/** Consistent section rhythm: eyebrow + heading (+ optional right slot). */
export function SectionHeader({ eyebrow, title, right, className }: SectionHeaderProps) {
  return (
    <div className={cn("mb-4 flex items-end justify-between gap-3", className)}>
      <div>
        {eyebrow && (
          <div className="text-[11px] font-semibold uppercase tracking-[0.09em] text-ink-faint">
            {eyebrow}
          </div>
        )}
        <h2 className="text-lg font-semibold text-ink">{title}</h2>
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  );
}
