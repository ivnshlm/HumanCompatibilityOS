"""Question Bank v0.1 — canonical 75-question environment-pressure instrument.

The bank (5 components x 15 questions) replaces the old hardcoded 15-question
list as the source of questionnaire items. It is loaded from the committed JSON
resource (a stable, versioned spec artifact) into an in-memory registry — no DB
table, since the bank is small and immutable per version.

Each question carries: component, subdimension, family_id, scoring_direction
(pressure_direct | protective_reverse), item_type (core|validation|rotation),
selection_level (short|base|deep), required_for_short, and review-side metadata
(follow_up_question, hrd/manager/architect notes).

Session selection is deterministic (no RNG) so a level always yields a stable,
comparable set and historical sessions can be reproduced from stored question_ids.
Scoring math itself lives in scoring.py; this module only supplies the items.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_RESOURCE = Path(__file__).parent / "resources" / "question_bank_v0_1.json"

# Canonical component order (matches the spec / formula weight order).
COMPONENT_ORDER = ["DA", "DV", "KP", "PO", "NL"]

# Questions selected per component for each session level.
LEVEL_TARGETS = {"short": 3, "base": 5, "deep": 8}
LEVELS = tuple(LEVEL_TARGETS)


@dataclass(frozen=True)
class BankQuestion:
    question_id: str
    component_id: str
    component_name: str
    component_weight: float
    subdimension: str
    family_id: str
    question_text: str
    scoring_direction: str  # "pressure_direct" | "protective_reverse"
    reverse_scored: bool
    item_weight: float
    item_type: str  # "core" | "validation" | "rotation"
    required_for_short: bool
    selection_level: str  # "short" | "base" | "deep"
    avoid_same_family_in_session: bool
    follow_up_question: str
    subdimension_id: str
    hrd_note: str
    manager_note: str
    architect_note: str


@dataclass(frozen=True)
class ComponentMeta:
    component_id: str
    component_name: str
    weight: float
    description: str
    high_signal: str
    hrd_layer: str
    manager_layer: str
    architect_layer: str


@lru_cache(maxsize=1)
def _raw() -> dict:
    with _RESOURCE.open(encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def bank_version() -> str:
    return _raw()["metadata"]["version"]


@lru_cache(maxsize=1)
def scale() -> list[dict]:
    """The 1-5 agreement scale with Russian labels + meanings (for the UI)."""
    return list(_raw()["scale"])


@lru_cache(maxsize=1)
def components() -> dict[str, ComponentMeta]:
    out: dict[str, ComponentMeta] = {}
    for c in _raw()["components"]:
        out[c["component_id"]] = ComponentMeta(
            component_id=c["component_id"],
            component_name=c["component_name"],
            weight=c["weight"],
            description=c["description"],
            high_signal=c["high_signal"],
            hrd_layer=c["hrd_layer"],
            manager_layer=c["manager_layer"],
            architect_layer=c["architect_layer"],
        )
    return out


@lru_cache(maxsize=1)
def _questions() -> list[BankQuestion]:
    out: list[BankQuestion] = []
    for q in _raw()["questions"]:
        if not q.get("active", True):
            continue
        out.append(
            BankQuestion(
                question_id=q["question_id"],
                component_id=q["component_id"],
                component_name=q["component_name"],
                component_weight=q["component_weight"],
                subdimension=q["subdimension"],
                family_id=q["family_id"],
                question_text=q["question_text"],
                scoring_direction=q["scoring_direction"],
                reverse_scored=bool(q["reverse_scored"]),
                item_weight=float(q["item_weight"]),
                item_type=q["item_type"],
                required_for_short=bool(q["required_for_short"]),
                selection_level=q["selection_level"],
                avoid_same_family_in_session=bool(q["avoid_same_family_in_session"]),
                follow_up_question=q.get("follow_up_question", ""),
                subdimension_id=q["family_id"],
                hrd_note=q.get("hrd_note", ""),
                manager_note=q.get("manager_note", ""),
                architect_note=q.get("architect_note", ""),
            )
        )
    return out


@lru_cache(maxsize=1)
def by_id() -> dict[str, BankQuestion]:
    return {q.question_id: q for q in _questions()}


@lru_cache(maxsize=1)
def by_component() -> dict[str, list[BankQuestion]]:
    out: dict[str, list[BankQuestion]] = {c: [] for c in COMPONENT_ORDER}
    for q in _questions():
        out[q.component_id].append(q)
    for c in out:
        out[c].sort(key=lambda q: q.question_id)
    return out


def get(question_id: str) -> BankQuestion | None:
    return by_id().get(question_id)


def validate_bank() -> None:
    """Integrity checks; raise if the bank is malformed (called at startup/tests)."""
    qs = _questions()
    if len(qs) != 75:
        raise ValueError(f"Question bank must have 75 active questions, got {len(qs)}")
    grouped = by_component()
    for comp_id in COMPONENT_ORDER:
        if len(grouped[comp_id]) != 15:
            raise ValueError(f"Component {comp_id} must have 15 questions, got {len(grouped[comp_id])}")
    weight_sum = round(sum(c.weight for c in components().values()), 6)
    if weight_sum != 1.0:
        raise ValueError(f"Component weights must sum to 1.0, got {weight_sum}")
    ids = [q.question_id for q in qs]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate question_id in bank")


def _priority_key(level: str):
    if level == "short":
        return lambda q: (0 if q.required_for_short else 1, q.question_id)
    if level == "base":
        return lambda q: (0 if q.item_type == "core" else 1, q.question_id)
    # deep: core, then validation, then rotation
    order = {"core": 0, "validation": 1, "rotation": 2}
    return lambda q: (order.get(q.item_type, 3), q.question_id)


def _select_component(comp_id: str, level: str) -> list[BankQuestion]:
    target = LEVEL_TARGETS[level]
    ranked = sorted(by_component()[comp_id], key=_priority_key(level))

    chosen: list[BankQuestion] = []
    families: set[str] = set()
    for q in ranked:
        if len(chosen) >= target:
            break
        if q.avoid_same_family_in_session and q.family_id in families:
            continue
        chosen.append(q)
        families.add(q.family_id)
    # Relax the family constraint only if a component lacks enough families.
    if len(chosen) < target:
        for q in ranked:
            if len(chosen) >= target:
                break
            if q not in chosen:
                chosen.append(q)

    # base/deep require at least one reverse (protective) item per component;
    # swap the lowest-priority item for a reverse one while keeping families distinct.
    if level in ("base", "deep") and not any(q.reverse_scored for q in chosen):
        kept_families = {q.family_id for q in chosen[:-1]}
        replacement = next(
            (q for q in ranked if q.reverse_scored and q not in chosen and q.family_id not in kept_families),
            None,
        )
        if replacement is not None:
            chosen[-1] = replacement
    return chosen[:target]


def select_session(level: str) -> list[str]:
    """Deterministic list of question_ids for a session level (short/base/deep).

    Stable across calls (no randomness) so sessions are comparable and a stored
    session can be reproduced. short=15, base=25, deep=40 (N per component x 5).
    """
    if level not in LEVEL_TARGETS:
        raise ValueError(f"Unknown session level: {level}")
    out: list[str] = []
    for comp_id in COMPONENT_ORDER:
        out.extend(q.question_id for q in _select_component(comp_id, level))
    return out
