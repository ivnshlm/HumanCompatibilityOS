import pytest

from app import question_bank


def test_bank_loads_and_validates():
    question_bank.validate_bank()
    assert question_bank.bank_version() == "v0.1"
    assert len(question_bank.scale()) == 5
    assert set(question_bank.components()) == set(question_bank.COMPONENT_ORDER)


@pytest.mark.parametrize(("level", "per_comp"), [("short", 3), ("base", 5), ("deep", 8)])
def test_session_size_and_per_component(level, per_comp):
    ids = question_bank.select_session(level)
    assert len(ids) == per_comp * 5
    by_comp: dict[str, int] = {}
    for qid in ids:
        by_comp[question_bank.get(qid).component_id] = by_comp.get(question_bank.get(qid).component_id, 0) + 1
    assert by_comp == {c: per_comp for c in question_bank.COMPONENT_ORDER}


@pytest.mark.parametrize("level", ["short", "base", "deep"])
def test_no_duplicate_family_within_session(level):
    ids = question_bank.select_session(level)
    families = [question_bank.get(qid).family_id for qid in ids]
    assert len(families) == len(set(families)), "a family must not repeat within a session"


@pytest.mark.parametrize("level", ["short", "base", "deep"])
def test_selection_is_deterministic(level):
    assert question_bank.select_session(level) == question_bank.select_session(level)


def test_short_prefers_required_for_short():
    # Every required_for_short item that survives the family constraint should be
    # in the short session; short never pulls a non-required item over a required
    # one from a fresh family.
    ids = set(question_bank.select_session("short"))
    for comp_id in question_bank.COMPONENT_ORDER:
        required = [q for q in question_bank.by_component()[comp_id] if q.required_for_short]
        # at least the first required (distinct family) is always present
        assert required[0].question_id in ids


@pytest.mark.parametrize("level", ["base", "deep"])
def test_base_deep_have_reverse_per_component(level):
    ids = question_bank.select_session(level)
    for comp_id in question_bank.COMPONENT_ORDER:
        comp_ids = [q for q in ids if question_bank.get(q).component_id == comp_id]
        assert any(question_bank.get(q).reverse_scored for q in comp_ids), (
            f"{comp_id} in {level} session must include a reverse item"
        )


def test_unknown_level_raises():
    with pytest.raises(ValueError, match="Unknown session level"):
        question_bank.select_session("medium")
