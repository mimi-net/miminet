def _analysis_for_grade(turn_or_analysis):
    if isinstance(turn_or_analysis, dict):
        return turn_or_analysis
    return turn_or_analysis.analysis or {}


def _focus_for_grade(turn_or_analysis):
    if isinstance(turn_or_analysis, dict):
        return turn_or_analysis.get("focus") or {}
    return turn_or_analysis.focus or {}


def _has_strong_reasoning_turn(turns, analyses):
    for turn, analysis in zip(turns, analyses):
        focus = _focus_for_grade(turn)
        difficulty = focus.get("difficulty") or focus.get("target_difficulty")
        question_type = focus.get("question_type")
        score = int(analysis.get("answer_score", 0))
        if score < 3:
            continue
        if difficulty in {"practice", "advanced"}:
            return True
        if question_type in {"diagnosis", "packet_trace", "minimal_fix", "consequence"}:
            return True
    return False


def normalize_grade(turns, candidate_grade=None):
    analyses = [_analysis_for_grade(turn) for turn in turns]
    scores = [int(analysis.get("answer_score", 0)) for analysis in analyses]
    score_total = sum(max(0, min(score, 3)) for score in scores)
    critical_error = any(analysis.get("critical_error") for analysis in analyses)
    question_count = max(1, len(scores))
    score_ratio = score_total / (question_count * 3)
    last_score = scores[-1] if scores else 0

    if score_ratio >= 0.83 and last_score >= 2 and not critical_error:
        rubric_grade = 5
    elif score_ratio >= 0.62:
        rubric_grade = 4
    elif score_ratio >= 0.35:
        rubric_grade = 3
    else:
        rubric_grade = 2

    if critical_error:
        rubric_grade = min(rubric_grade, 3)
    if rubric_grade == 5 and not _has_strong_reasoning_turn(turns, analyses):
        rubric_grade = 4

    try:
        candidate_grade = int(candidate_grade)
    except (TypeError, ValueError):
        return rubric_grade
    return max(2, min(rubric_grade, candidate_grade, 5))


def normalize_analysis(payload, answer):
    return {
        "covered_concepts": payload["covered_concepts"],
        "missed_concepts": payload["missed_concepts"],
        "misconceptions": payload["misconceptions"],
        "answer_score": payload["answer_score"],
        "critical_error": payload["critical_error"],
    }


def normalize_final_result(turns, llm_result):
    final_result = dict(llm_result)
    final_result["grade"] = normalize_grade(turns, llm_result.get("grade"))
    return final_result
