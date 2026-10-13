"""Unit tests for id-based grading of theory questions.

Regression: with a browser translator on, the quiz page sent translated text,
so correct answers were graded as wrong. Grading now uses Answer ids.

Runs without the app or browser:
    PYTHONPATH=front/src pytest front/tests/test_quiz_answer_grading.py --noconftest
"""

from types import SimpleNamespace

from quiz.service.answer_grading import (
    grade_matching,
    grade_sorting,
    grade_variable,
    is_matching_by_id,
    is_sorting_by_id,
    is_variable_by_id,
)


def row(id, variant="", is_correct=False, position=None, left="", right=""):
    return SimpleNamespace(
        id=id,
        variant=variant,
        is_correct=is_correct,
        position=position,
        left=left,
        right=right,
    )


VARIABLE = [
    row(1, "Маршрутизатор", is_correct=True),
    row(2, "Коммутатор"),
    row(3, "Концентратор", is_correct=True),
]

SORTING = [
    row(10, "Прикладной", position=0),
    row(11, "Транспортный", position=1),
    row(12, "Сетевой", position=2),
]

MATCHING = [
    row(20, left="ARP", right="Канальный"),
    row(21, left="IP", right="Сетевой"),
    row(22, left="TCP", right="Транспортный"),
]


# --- format detection ---


def test_old_text_payloads_are_not_treated_as_ids():
    assert not is_variable_by_id([{"variant": "Router"}])
    assert not is_sorting_by_id({"0": "Application"})
    assert not is_matching_by_id([{"left": "ARP", "right": "Link"}])


def test_id_payloads_are_detected():
    assert is_variable_by_id([{"id": "1"}])
    assert is_sorting_by_id({"0": {"id": "10"}})
    assert is_matching_by_id([{"left_id": "20", "right_id": "20"}])


# --- variable ---


def test_variable_all_correct_selected():
    correct, user_answer = grade_variable(VARIABLE, [{"id": "1"}, {"id": "3"}])
    assert correct
    # stored with the original Russian text, whatever the page showed
    assert [item["variant"] for item in user_answer] == [
        "Маршрутизатор",
        "Концентратор",
    ]


def test_variable_missing_or_extra_choice_is_wrong():
    assert not grade_variable(VARIABLE, [{"id": "1"}])[0]
    assert not grade_variable(VARIABLE, [{"id": "1"}, {"id": "2"}, {"id": "3"}])[0]


def test_variable_unknown_or_duplicate_id_is_wrong():
    assert not grade_variable(VARIABLE, [{"id": "1"}, {"id": "999"}])[0]
    assert not grade_variable(VARIABLE, [{"id": "1"}, {"id": "1"}, {"id": "3"}])[0]


def test_variable_accepts_numeric_ids():
    assert grade_variable(VARIABLE, [{"id": 1}, {"id": 3}])[0]


# --- sorting ---


def test_sorting_correct_order():
    payload = {"0": {"id": "10"}, "1": {"id": "11"}, "2": {"id": "12"}}
    correct, user_answer = grade_sorting(SORTING, payload)
    assert correct
    assert user_answer == {"0": "Прикладной", "1": "Транспортный", "2": "Сетевой"}


def test_sorting_wrong_order():
    payload = {"0": {"id": "11"}, "1": {"id": "10"}, "2": {"id": "12"}}
    assert not grade_sorting(SORTING, payload)[0]


def test_sorting_index_keys_sorted_numerically():
    answers = [row(i, str(i), position=i) for i in range(12)]
    payload = {str(i): {"id": str(i)} for i in reversed(range(12))}
    assert grade_sorting(answers, payload)[0]


# --- matching ---


def test_matching_correct_pairs():
    payload = [
        {"left_id": "22", "right_id": "22"},
        {"left_id": "20", "right_id": "20"},
        {"left_id": "21", "right_id": "21"},
    ]
    correct, user_answer = grade_matching(MATCHING, payload)
    assert correct
    assert {"left": "ARP", "right": "Канальный"} in user_answer


def test_matching_swapped_pair_is_wrong():
    payload = [
        {"left_id": "20", "right_id": "21"},
        {"left_id": "21", "right_id": "20"},
        {"left_id": "22", "right_id": "22"},
    ]
    assert not grade_matching(MATCHING, payload)[0]


def test_matching_incomplete_or_repeated_is_wrong():
    assert not grade_matching(MATCHING, [{"left_id": "20", "right_id": "20"}])[0]
    repeated = [{"left_id": "20", "right_id": "20"}] * 3
    assert not grade_matching(MATCHING, repeated)[0]
