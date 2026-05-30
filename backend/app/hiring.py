"""Compatibility Hiring reference & advisory logic (HR Workbook v6).

Static reference content (signals, behavioral indicators, interview questions,
risk legend, decision guidance) lifted from the canonical HR Workbook, plus an
*advisory* overall-risk suggestion. Per doctrine, nothing here decides: the
suggestion is a hint for a human reviewer, never an automatic rejection.
"""

from dataclasses import dataclass

from app.models import OverallRisk


@dataclass(frozen=True)
class Signal:
    key: str
    label: str  # RU
    label_en: str
    indicator: str  # behavioral indicator (RU)
    question: str  # interview question (RU)
    focus: str  # observation focus (RU)
    legend_low: str
    legend_medium: str
    legend_high: str
    quick_screen: bool  # part of the 4-signal quick screen


SIGNALS: list[Signal] = [
    Signal(
        "explainability", "Объяснимость", "Explainability",
        "Ясно объясняет ход мысли и решения",
        "Расскажите о трудном решении и как вы к нему пришли.",
        "Ясность рассуждения",
        "Объясняет решения, показывает ход мысли, признаёт неопределённость",
        "Объясняет частично, ход мысли местами непрозрачен",
        "Не объясняет решения, рассуждение непрозрачно",
        True,
    ),
    Signal(
        "feedback_stability", "Устойчивость к обратной связи", "Feedback Stability",
        "Принимает коррекцию без эго-защиты",
        "Опишите момент, когда ваш подход поставили под сомнение.",
        "Адаптация или защита?",
        "Открыт к коррекции",
        "Защищается под стрессом",
        "Агрессивно отвергает обратную связь",
        True,
    ),
    Signal(
        "chaos_relationship", "Отношение к хаосу", "Chaos Relationship",
        "Снижает или повышает хаос вокруг себя",
        "Что происходит вокруг вас во время давления?",
        "Стабилизирует или эскалирует?",
        "Создаёт ясность",
        "Смешанно под давлением",
        "Создаёт энтропию и напряжение",
        True,
    ),
    Signal(
        "responsibility", "Ответственность", "Responsibility Layer",
        "Держит последствия своих решений",
        "Расскажите об ошибке, которую вы признали.",
        "Принятие ответственности или перекладывание вины",
        "Держит последствия",
        "Частичное принятие ответственности",
        "Externalizes — перекладывает вину",
        True,
    ),
    Signal(
        "long_distance_capacity", "Долгосрочная устойчивость", "Long-Distance Capacity",
        "Удерживает операционный ритм надолго",
        "Как вы поддерживаете ритм в долгосрочной перспективе?",
        "Постоянство против вспышек",
        "Стабильный устойчивый ритм",
        "Ритм держится неровно",
        "Только короткие вспышки, быстро выгорает",
        False,
    ),
    Signal(
        "human_warmth", "Человеческое тепло", "Human Warmth",
        "Уважительное и стабильное взаимодействие",
        "Как вы поддерживаете людей, не снимая с них ответственности?",
        "Тепло без инфантилизации",
        "Тепло и уважение без инфантилизации",
        "Тепло ситуативно",
        "Холодно/механистично либо чрезмерная опека",
        False,
    ),
    Signal(
        "role_clarity", "Ясность роли", "Role Clarity",
        "Понимает границы ответственности",
        "Как вы определяете границы ответственности?",
        "Ясность владения зоной",
        "Чётко понимает зону ответственности",
        "Границы размыты",
        "Не понимает границ ответственности",
        False,
    ),
    Signal(
        "energy_recovery", "Энергия и восстановление", "Energy & Recovery",
        "Избегает выгорания и режима героя",
        "Как вы восстанавливаетесь после длительного стресса?",
        "Здоровое восстановление",
        "Здоровое восстановление, без героизма",
        "Восстановление нерегулярное",
        "Хронический героизм, риск выгорания",
        False,
    ),
    Signal(
        "conflict_handling", "Работа с конфликтом", "Conflict Handling",
        "Конструктивно перерабатывает напряжение",
        "Как вы проживаете нарастающее разногласие?",
        "Конструктивно или деструктивно",
        "Конструктивно разрешает напряжение",
        "По-разному в зависимости от давления",
        "Эскалирует, разрушительно для среды",
        False,
    ),
    Signal(
        "leadership_compatibility", "Совместимость с лидерством", "Leadership Compatibility",
        "Влияние на нервную систему команды",
        "Как ваше присутствие влияет на команду под давлением?",
        "Влияние на нервную систему команды",
        "Стабилизирует команду",
        "Зависит от давления",
        "Экспортирует хаос в команду",
        False,
    ),
]

QUICK_SCREEN_SIGNALS: list[str] = [s.key for s in SIGNALS if s.quick_screen]

DIMENSIONS: list[dict[str, str]] = [
    {"key": "long_term_compatibility", "label": "Долгосрочная совместимость"},
    {"key": "tactical_value", "label": "Тактическая ценность"},
    {"key": "chaos_cost", "label": "Стоимость хаоса"},
    {"key": "team_influence", "label": "Влияние на команду"},
    {"key": "growth_potential", "label": "Потенциал роста"},
]

DECISION_GUIDANCE: list[str] = [
    "Высокая стоимость хаоса + негативное влияние на команду → не интегрировать в ядро.",
    "Высокая тактическая ценность + высокая стоимость хаоса → тактическая или контролируемая интеграция.",
    "Низкая долгосрочная совместимость → не назначать на лидерские роли.",
]

OVERALL_RISK_LABELS: dict[OverallRisk, str] = {
    OverallRisk.green: "Зелёный — рекомендуется",
    OverallRisk.yellow: "Жёлтый — условно",
    OverallRisk.red: "Красный — тактически / усиленный надзор",
}

DISCLAIMER = (
    "Оценка совместимости — со средой, а не с ценностью человека. "
    "Никакого автоматического отказа: финальное решение принимает человек."
)


def suggest_overall_risk(signals: dict[str, str]) -> OverallRisk:
    """Advisory overall-risk hint from per-signal ratings. Never a decision."""
    highs = sum(1 for v in signals.values() if v == "high")
    mediums = sum(1 for v in signals.values() if v == "medium")
    if highs >= 2:
        return OverallRisk.red
    if highs == 1 or mediums >= 2:
        return OverallRisk.yellow
    return OverallRisk.green
