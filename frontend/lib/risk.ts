import type { RiskLevel } from "@/lib/api";

export const RISK_LABEL: Record<RiskLevel, string> = {
  low: "Низкий",
  medium: "Средний",
  high: "Высокий",
};

// Calm palette by doctrine: high risk must NOT read as an aggressive red
// verdict. We use a muted amber/orange warning, never red.
export const RISK_TEXT: Record<RiskLevel, string> = {
  low: "text-emerald-400",
  medium: "text-amber-400",
  high: "text-orange-400",
};

export const RISK_DOT: Record<RiskLevel, string> = {
  low: "bg-emerald-400",
  medium: "bg-amber-400",
  high: "bg-orange-400",
};

export const NO_DECISION_DISCLAIMER =
  "Светофор-индикаторы не являются основанием для кадровых решений. Все выводы требуют проверки человеком.";
