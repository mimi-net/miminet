from types import SimpleNamespace

from quiz.util.dto import calculate_progress_percent, calculate_test_progress


def test_calculate_progress_percent_returns_zero_without_questions():
    assert calculate_progress_percent(5, 0) == 0


def test_calculate_test_progress_uses_total_solved_over_total_questions(mocker):
    sections = [SimpleNamespace(id=101), SimpleNamespace(id=202)]
    mocker.patch(
        "quiz.util.dto.calculate_question_count",
        side_effect=[5, 5],
    )

    solved_count, total_count, progress_percent = calculate_test_progress(
        sections,
        {
            101: 2,
            202: 3,
        },
    )

    assert solved_count == 5
    assert total_count == 10
    assert progress_percent == 50


def test_calculate_test_progress_caps_progress_per_section(mocker):
    sections = [SimpleNamespace(id=101), SimpleNamespace(id=202)]
    mocker.patch(
        "quiz.util.dto.calculate_question_count",
        side_effect=[5, 3],
    )

    solved_count, total_count, progress_percent = calculate_test_progress(
        sections,
        {
            101: 7,
            202: 1,
        },
    )

    assert solved_count == 6
    assert total_count == 8
    assert progress_percent == 75
