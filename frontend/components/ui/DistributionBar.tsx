import { cn } from "./cn";

type Distribution = { low: number; medium: number; high: number };

/** Segmented risk-distribution bar: low (emerald) · medium (amber) · high (orange). */
export function DistributionBar({
  distribution,
  showLegend = true,
  className,
}: {
  distribution: Distribution;
  showLegend?: boolean;
  className?: string;
}) {
  const total = distribution.low + distribution.medium + distribution.high;
  const pct = (n: number) => (total > 0 ? (n / total) * 100 : 0);

  return (
    <div className={className}>
      <div className="flex h-2 overflow-hidden rounded-full bg-white/10">
        <div className="bg-risk-low" style={{ width: `${pct(distribution.low)}%` }} />
        <div className="bg-risk-medium" style={{ width: `${pct(distribution.medium)}%` }} />
        <div className="bg-risk-high" style={{ width: `${pct(distribution.high)}%` }} />
      </div>
      {showLegend && (
        <div className="mt-2 flex gap-4 text-xs text-ink-muted">
          <span>низкий {distribution.low}</span>
          <span>средний {distribution.medium}</span>
          <span>высокий {distribution.high}</span>
        </div>
      )}
    </div>
  );
}
