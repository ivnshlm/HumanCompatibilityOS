import type { ReactNode } from "react";

import { Card } from "./Card";
import { cn } from "./cn";

type StatCardProps = {
  eyebrow?: string;
  title?: ReactNode;
  /** The headline value (large, tabular-nums). */
  value: ReactNode;
  caption?: ReactNode;
  /** Top-right slot, e.g. a RiskBadge. */
  badge?: ReactNode;
  /** Footer slot, e.g. a DistributionBar or Sparkline. */
  footer?: ReactNode;
  className?: string;
};

/** KPI surface: eyebrow/title + large number + optional badge / caption / footer. */
export function StatCard({ eyebrow, title, value, caption, badge, footer, className }: StatCardProps) {
  return (
    <Card className={cn("flex flex-col", className)}>
      <div className="flex items-start justify-between gap-3">
        <div>
          {eyebrow && (
            <div className="text-[11px] font-semibold uppercase tracking-[0.09em] text-ink-faint">
              {eyebrow}
            </div>
          )}
          {title && <div className="text-base font-medium text-ink">{title}</div>}
        </div>
        {badge && <div className="shrink-0">{badge}</div>}
      </div>

      <div className="mt-3 text-4xl font-semibold tabular-nums text-ink">{value}</div>
      {caption && <div className="mt-1 text-xs text-ink-muted">{caption}</div>}
      {footer && <div className="mt-4">{footer}</div>}
    </Card>
  );
}
