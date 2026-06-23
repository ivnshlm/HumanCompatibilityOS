import type { RiskLevel } from "@/lib/api";
import { RISK_DOT, RISK_LABEL, RISK_TEXT } from "@/lib/risk";

import { cn } from "./cn";

/** The single source of risk colour in the UI — never invents its own palette. */
export function RiskBadge({ level, className }: { level: RiskLevel | null; className?: string }) {
  if (!level) return <span className={cn("text-xs text-ink-faint", className)}>—</span>;
  return (
    <span
      className={cn("inline-flex items-center gap-1.5 text-sm font-medium", RISK_TEXT[level], className)}
    >
      <span className={cn("h-2 w-2 rounded-full", RISK_DOT[level])} />
      {RISK_LABEL[level]}
    </span>
  );
}
