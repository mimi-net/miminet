"""Grading of theory questions by answer id.

The quiz page used to send back the visible text of the chosen options, and the
server compared that text with the stored one. A browser translator rewrites
the visible text, so correct answers were graded as wrong. The page now sends
the ``Answer.id`` of every option instead; these helpers grade by id and build
the stored user answer from the original texts, so the results page shows the
same texts as before.

The helpers take plain answer rows and the submitted payload and touch neither
the database nor Flask, so they can be unit-tested directly.
"""


def _sort_key(answer):
    return (
        answer.position is None,
        answer.position if answer.position is not None else 0,
        answer.id,
    )


def _by_id(answers):
    return {str(answer.id): answer for answer in answers}


def is_variable_by_id(payload) -> bool:
    return (
        isinstance(payload, list)
        and len(payload) > 0
        and all(isinstance(item, dict) and "id" in item for item in payload)
    )


def is_sorting_by_id(payload) -> bool:
    return (
        isinstance(payload, dict)
        and len(payload) > 0
        and all(isinstance(item, dict) and "id" in item for item in payload.values())
    )


def is_matching_by_id(payload) -> bool:
    return (
        isinstance(payload, list)
        and len(payload) > 0
        and all(
            isinstance(item, dict) and "left_id" in item and "right_id" in item
            for item in payload
        )
    )


def grade_variable(answers, payload):
    """Single or multiple choice: [{"id": ...}, ...].

    Returns (is_correct, user_answer). user_answer keeps the old
    [{"variant": text}] shape used by the results page.
    """
    answers_by_id = _by_id(answers)
    selected = [str(item["id"]) for item in payload]

    user_answer = [
        {"id": answer_id, "variant": answers_by_id[answer_id].variant}
        for answer_id in selected
        if answer_id in answers_by_id
    ]

    if len(set(selected)) != len(selected) or any(
        answer_id not in answers_by_id for answer_id in selected
    ):
        return False, user_answer

    correct_ids = {
        answer_id for answer_id, answer in answers_by_id.items() if answer.is_correct
    }
    return set(selected) == correct_ids, user_answer


def grade_sorting(answers, payload):
    """Ordering: {"0": {"id": ...}, "1": {"id": ...}, ...}.

    Returns (is_correct, user_answer). user_answer keeps the old
    {"0": text, "1": text} shape used by the results page.
    """
    answers_by_id = _by_id(answers)
    ordered = sorted(payload.items(), key=lambda item: int(item[0]))
    submitted = [str(item["id"]) for _, item in ordered]

    user_answer = {
        str(index): answers_by_id[answer_id].variant
        for index, answer_id in enumerate(submitted)
        if answer_id in answers_by_id
    }

    expected = [str(answer.id) for answer in sorted(answers, key=_sort_key)]
    return submitted == expected, user_answer


def grade_matching(answers, payload):
    """Matching: [{"left_id": ..., "right_id": ...}, ...].

    Each Answer row stores one correct left/right pair, so a pair is correct
    when both sides come from the same row. Returns (is_correct, user_answer);
    user_answer keeps the old [{"left": text, "right": text}] shape.
    """
    answers_by_id = _by_id(answers)
    pairs = [(str(item["left_id"]), str(item["right_id"])) for item in payload]

    user_answer = [
        {"left": answers_by_id[left].left, "right": answers_by_id[right].right}
        for left, right in pairs
        if left in answers_by_id and right in answers_by_id
    ]

    left_ids = [left for left, _ in pairs]
    is_correct = (
        len(pairs) == len(answers_by_id)
        and len(set(left_ids)) == len(left_ids)
        and set(left_ids) == set(answers_by_id)
        and all(left == right for left, right in pairs)
    )
    return is_correct, user_answer