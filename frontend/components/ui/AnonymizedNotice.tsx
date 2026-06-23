import { EmptyState } from "./EmptyState";

/**
 * Cohort-anonymization placeholder, shown when `sufficient_data === false`
 * (fewer than `min` contributors). By doctrine, small cohorts must stay hidden —
 * this is a calm, neutral notice, not an error.
 */
export function AnonymizedNotice({
  cohortSize,
  min = 3,
  className,
}: {
  cohortSize?: number | null;
  min?: number;
  className?: string;
}) {
  const current =
    cohortSize === undefined || cohortSize === null ? "" : ` (сейчас ${cohortSize})`;
  return (
    <EmptyState
      dashed
      icon="⊘"
      title="Данные скрыты для анонимности"
      text={`Чтобы команда не превратилась в профиль одного человека, агрегаты показываются при выборке не меньше ${min} участников${current}.`}
      className={className}
    />
  );
}
