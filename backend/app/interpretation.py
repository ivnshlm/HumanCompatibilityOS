"""Interpretation layer over the numeric burnout result.

Turns a ``BurnoutResult`` into a careful, explainable signal for human review:
a short summary, the 2–3 dominant pressure factors, a cautious hypothesis
(never a diagnosis), 3–5 things to check next, and a permanent ethical
disclaimer.

Doctrine (per "Интерпретация результата для Архитектора · v0.1"):
- Show *which element of the environment creates pressure*, never "what is
  wrong with the person".
- Every output is a hypothesis for human review, never a personnel decision.
- Stigmatising phrasings are listed in ``FORBIDDEN_PHRASES`` and enforced by a
  test over the generated text.

The scoring engine already orients every component so that **higher == more
pressure** (recovery is scored as a *deficit*, reverse questions are flipped in
``scoring._oriented_value``). So no extra normalisation layer is needed here —
sorting by ``score`` descending already ranks factors by how much pressure they
contribute.
"""

from dataclasses import dataclass

from app import question_bank
from app.models import RiskLevel
from app.scoring import COMPONENT_BY_BANK_ID, BurnoutResult, Component

# --- Tunables (configurable without touching the generation logic) ---

# A 3rd dominant factor is mentioned only when it is itself meaningful
# (>= floor) and close behind the 2nd factor (gap <= bound). This reproduces
# the reference examples: example A surfaces a 3rd factor, example B does not.
THIRD_FACTOR_FLOOR = 2.5
THIRD_FACTOR_GAP = 0.5

# Below this, the leadership contour is treated as "relatively stable" and the
# summary explicitly avoids attributing pressure to management.
LEADERSHIP_STABLE_BELOW = 2.0

# Permanent ethical disclaimer shown on every individual result.
DISCLAIMER = (
    "Этот результат является сигнальным слоем среды. Он не является диагнозом, "
    "оценкой личности или основанием для кадрового решения. Итоговые выводы "
    "принимаются человеком после проверки контекста."
)

# Opening sentence per risk level — calm, never a verdict (see tone table §6).
RISK_OPENER: dict[RiskLevel, str] = {
    RiskLevel.low: (
        "Среда сейчас не показывает выраженного давления; стоит поддерживать "
        "устойчивые практики и отслеживать изменения."
    ),
    RiskLevel.medium: "Давление среды находится в зоне среднего риска перегруза.",
    RiskLevel.high: (
        "Сигнал требует бережной человеческой проверки: сначала уточнить "
        "контекст, затем снижать давление среды."
    ),
}

# Short noun phrase for the summary ("Основной вклад дают …").
SUMMARY_NAME: dict[Component, str] = {
    Component.emergency_pressure: "авральный режим",
    Component.recovery_deficit: "дефицит восстановления",
    Component.communication_overload: "коммуникационная перегрузка",
    Component.interruption_density: "высокая плотность отвлечений",
    # Careful wording: never "руководитель нестабилен" (forbidden) — name the
    # contour, not the person.
    Component.leadership_instability: "повышенное давление в лидерском контуре",
}

# Friction-zone phrase for the cautious hypothesis ("Вероятная зона трения …").
# Single concepts (no internal "и") so the joined list reads cleanly.
FRICTION: dict[Component, str] = {
    Component.emergency_pressure: "режим аврала",
    Component.recovery_deficit: "нехватка восстановления",
    Component.communication_overload: "перегрузка коммуникации",
    Component.interruption_density: "частые переключения",
    Component.leadership_instability: "нестабильность приоритетов",
}

# What a high score on this component means (shown on the factor card).
EXPLANATION: dict[Component, str] = {
    Component.emergency_pressure: (
        "Много срочных задач и частых переключений, ощущение постоянного пожара."
    ),
    Component.recovery_deficit: (
        "Человек не успевает восстановиться после интенсивной нагрузки."
    ),
    Component.communication_overload: (
        "Слишком много каналов, встреч, сообщений, уточнений и повторов."
    ),
    Component.interruption_density: (
        "Фокусная работа постоянно прерывается внешними запросами."
    ),
    Component.leadership_instability: (
        "Направление и приоритеты часто меняются, маршрут решений непредсказуем."
    ),
}

# "Что проверить дальше" — practical, non-prescriptive checks per component.
CHECK_ITEMS: dict[Component, list[str]] = {
    Component.emergency_pressure: [
        "Сколько задач становятся срочными и кто создаёт срочность",
        "Есть ли понятная приоритизация и критерий «это действительно срочно»",
    ],
    Component.recovery_deficit: [
        "Есть ли реальные паузы после интенсивных периодов",
        "Соблюдаются ли границы рабочего времени и циклы нагрузки",
    ],
    Component.communication_overload: [
        "Какие каналы и встречи дублируются и что можно убрать",
        "Фиксируются ли решения письменно вместо повторных уточнений",
    ],
    Component.interruption_density: [
        "Сколько переключений контекста в течение дня",
        "Есть ли защищённые окна фокусной работы",
    ],
    Component.leadership_instability: [
        "Как часто меняются цели и кто подтверждает приоритет",
        "Есть ли единый предсказуемый маршрут принятия решений",
    ],
}

# Stigmatising phrasings that must never appear in generated interpretation.
# Enforced by tests/test_interpretation.py over every produced string.
FORBIDDEN_PHRASES: list[str] = [
    "сотрудник выгорает",
    "нужно вмешаться hr",
    "руководитель нестабилен",
    "кандидат не подходит",
    "риск увольнения",
    "опасный человек",
    "нужно заменить",
    "нужно срочно заменить",
    "критический сотрудник",
    "плохой руководитель",
    "плохой сотрудник",
]


# Bank component_id keyed by internal Component (inverse of scoring's map).
BANK_ID_BY_COMPONENT = {v: k for k, v in COMPONENT_BY_BANK_ID.items()}

# Which review layer each role sees (see report_layers in the bank).
ROLE_TO_LAYER = {
    "employee": "participant",
    "hr": "hrd",
    "team_lead": "manager",
    "admin": "architect",
    "ethics_reviewer": "architect",
}

LAYER_LABELS_RU = {
    "participant": "Слой сотрудника",
    "hrd": "Слой HRD",
    "manager": "Слой руководителя",
    "architect": "Слой архитектора среды",
}


@dataclass(frozen=True)
class DominantFactor:
    key: str
    title: str
    score: float
    explanation: str
    subdimension: str = ""


@dataclass(frozen=True)
class Interpretation:
    summary: str
    dominant_factors: list[DominantFactor]
    possible_meaning: str
    check_next: list[str]
    disclaimer: str
    follow_ups: list[str] | None = None


@dataclass(frozen=True)
class LayerNote:
    component: str
    label: str
    note: str


@dataclass(frozen=True)
class ReportLayer:
    layer: str  # participant | hrd | manager | architect
    label: str
    description: str
    notes: list[LayerNote]


def _join_names(names: list[str]) -> str:
    """Russian-style list join: "a, b и c"."""
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " и " + names[-1]


def _summary_factors(names: list[str]) -> str:
    """Name the drivers in the summary. A 3rd factor is demoted to a softer
    "; в меньшей степени — …" tail (gender-neutral, mirrors the reference)."""
    if len(names) <= 2:
        return _join_names(names)
    return f"{names[0]} и {names[1]}; в меньшей степени — {names[2]}"


def _dominant_components(result: BurnoutResult) -> list:
    """Top 2 components by pressure (3rd only if meaningful and close behind).

    Tie-break by formula weight so the higher-weighted factor leads — this
    matches the reference examples where emergency_pressure (0.30) is named
    before equally-scored interruption (0.15) / communication (0.20).
    """
    ranked = sorted(result.components, key=lambda c: (c.score, c.weight), reverse=True)
    dominant = ranked[:2]
    if len(ranked) > 2:
        third = ranked[2]
        if third.score >= THIRD_FACTOR_FLOOR and (dominant[1].score - third.score) <= THIRD_FACTOR_GAP:
            dominant = ranked[:3]
    return dominant


def _dominant_item(component: Component, answers: dict[str, int] | None):
    """The answered bank item contributing the most pressure in a component.

    Used to surface the leading subdimension and its drill-down follow-up.
    Returns None when no answers are available (e.g. legacy recompute).
    """
    if not answers:
        return None
    bank_id = BANK_ID_BY_COMPONENT[component]
    scored = []
    for qid, value in answers.items():
        bq = question_bank.get(qid)
        if bq is None or bq.component_id != bank_id:
            continue
        oriented = (6 - value) if bq.scoring_direction == "protective_reverse" else value
        scored.append((oriented, bq.question_id, bq))
    if not scored:
        return None
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return scored[0][2]


def build_interpretation(
    result: BurnoutResult, answers: dict[str, int] | None = None
) -> Interpretation:
    """Generate the careful, explainable interpretation for a result.

    Pure function of the scored ``BurnoutResult`` (+ optional answer map for the
    subdimension/follow-up enrichment) — does not touch the database or the
    original formula. Safe to reuse anywhere the result is shown.
    """
    dominant = _dominant_components(result)
    dominant_keys = {c.component for c in dominant}

    # --- summary ---
    summary = (
        f"{RISK_OPENER[result.risk_level]} "
        f"Основной вклад дают {_summary_factors([SUMMARY_NAME[c.component] for c in dominant])}."
    )
    # Special rule: if leadership is low and not itself a driver, reassure that
    # pressure is unlikely to be a management problem (needs human check anyway).
    leadership = next(
        c for c in result.components if c.component is Component.leadership_instability
    )
    if leadership.score < LEADERSHIP_STABLE_BELOW and Component.leadership_instability not in dominant_keys:
        summary += (
            " Лидерский контур выглядит относительно стабильным, поэтому первичная "
            "гипотеза — давление связано с режимом работы и нагрузкой, а не с управлением."
        )

    # --- dominant factors (cards) + leading subdimension / drill-down follow-ups ---
    dominant_factors: list[DominantFactor] = []
    follow_ups: list[str] = []
    for c in dominant:
        item = _dominant_item(c.component, answers)
        dominant_factors.append(
            DominantFactor(
                key=c.component.value,
                title=c.label,
                score=c.score,
                explanation=EXPLANATION[c.component],
                subdimension=item.subdimension if item else "",
            )
        )
        if item and item.follow_up_question and item.follow_up_question not in follow_ups:
            follow_ups.append(item.follow_up_question)

    # --- possible meaning (cautious hypothesis, not a diagnosis) ---
    possible_meaning = (
        f"Вероятная зона трения среды — {_join_names([FRICTION[c.component] for c in dominant])}. "
        "Это осторожная гипотеза для проверки человеком, а не вывод о личности или "
        "работе сотрудника."
    )

    # --- what to check next (3–5 items, deduped, dominant factors first) ---
    check_next: list[str] = []
    for c in dominant:
        for item in CHECK_ITEMS[c.component]:
            if item not in check_next:
                check_next.append(item)
    check_next = check_next[:5]

    return Interpretation(
        summary=summary,
        dominant_factors=dominant_factors,
        possible_meaning=possible_meaning,
        check_next=check_next,
        disclaimer=DISCLAIMER,
        follow_ups=follow_ups or None,
    )


def build_report_layer(result: BurnoutResult, role: str | None) -> ReportLayer | None:
    """Role-specific framing of the dominant factors (spec report_layers).

    Reviewers (HR/manager/architect) get curated, environment-focused guidance
    per dominant component (hrd_layer / manager_layer / architect_layer). The
    participant (employee) layer adds nothing beyond the careful base reading, so
    None is returned — the subject always sees the explainable participant view.
    """
    layer = ROLE_TO_LAYER.get(role or "", "participant")
    if layer == "participant":
        return None

    comp_meta = question_bank.components()
    notes: list[LayerNote] = []
    for c in _dominant_components(result):
        meta = comp_meta.get(BANK_ID_BY_COMPONENT[c.component])
        if meta is None:
            continue
        note = {
            "hrd": meta.hrd_layer,
            "manager": meta.manager_layer,
            "architect": meta.architect_layer,
        }[layer]
        notes.append(LayerNote(component=c.component.value, label=c.label, note=note))

    return ReportLayer(
        layer=layer,
        label=LAYER_LABELS_RU[layer],
        description=question_bank.report_layers().get(layer, ""),
        notes=notes,
    )
