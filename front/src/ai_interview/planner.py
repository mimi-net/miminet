import random

from ai_interview.catalog import topic_catalog, validate_topic_keys


MIN_QUESTIONS = 4
MAX_QUESTIONS = 8
MAX_FOLLOWUPS_PER_TOPIC = 1

QUESTION_TEMPLATES = [
    {
        "key": "recall",
        "label": "Короткая проверка понятия",
        "difficulty": "basic",
        "operation": "one_fact",
        "allowed_plan_reasons": {"coverage", "rescue"},
        "concept_count": 1,
        "instruction": (
            "Задай короткий вопрос на понимание одного понятия. "
            "Не превращай его в длинный кейс и не проси перечислять редкие детали."
        ),
    },
    {
        "key": "mechanism",
        "label": "Механизм",
        "difficulty": "mechanism",
        "operation": "cause_effect",
        "allowed_plan_reasons": {"coverage", "clarify", "rescue"},
        "concept_count": 2,
        "instruction": (
            "Попроси объяснить, как работает механизм. "
            "Вопрос должен требовать связать причину и следствие, а не просто назвать термин."
        ),
    },
    {
        "key": "consequence",
        "label": "Что произойдет, если",
        "difficulty": "practice",
        "operation": "two_fact_link",
        "allowed_plan_reasons": {"coverage", "clarify", "challenge"},
        "concept_count": 2,
        "instruction": (
            "Сформулируй вопрос вида 'что произойдет, если изменить условие'. "
            "Проверяй следствие из двух понятий, но держи формулировку простой."
        ),
    },
    {
        "key": "diagnosis",
        "label": "Найти причину",
        "difficulty": "practice",
        "operation": "error_detection",
        "allowed_plan_reasons": {"clarify", "challenge"},
        "concept_count": 2,
        "instruction": (
            "Дай короткое наблюдение или симптом и спроси наиболее вероятную причину. "
        ),
    },
    {
        "key": "compare",
        "label": "Сравнение по последствию",
        "difficulty": "mechanism",
        "operation": "two_fact_link",
        "allowed_plan_reasons": {"coverage", "clarify", "challenge"},
        "concept_count": 2,
        "instruction": (
            "Попроси сравнить два близких механизма через практическое последствие. "
            "Не задавай вопрос как просьбу пересказать два определения подряд."
        ),
    },
]

QUESTION_TEMPLATE_BY_KEY = {
    template["key"]: template for template in QUESTION_TEMPLATES
}


def question_limit_for_topics(topic_keys):
    topic_count = len(validate_topic_keys(topic_keys))
    if topic_count <= 1:
        return 4
    return min(MAX_QUESTIONS, topic_count + 3)


def build_topic_schedule(topic_keys):
    normalized = validate_topic_keys(topic_keys)
    if not normalized:
        return []

    return list(normalized)


def _difficulty_for_stage(position):
    if position <= 1:
        return "basic"
    if position == 2:
        return "mechanism"
    if position == 3:
        return "practice"
    return "advanced"


def _difficulty_for_plan_reason(plan_reason, position):
    if plan_reason == "rescue":
        return "basic"
    if plan_reason == "clarify":
        return "mechanism"
    if plan_reason == "challenge":
        return "advanced"
    if position <= 1:
        return "basic"
    if position == 2:
        return "mechanism"
    return "practice"


def _templates_for_reason(plan_reason, target_difficulty=None):
    templates = [
        template
        for template in QUESTION_TEMPLATES
        if plan_reason in template["allowed_plan_reasons"]
    ]
    if target_difficulty:
        exact = [
            template
            for template in templates
            if template["difficulty"] == target_difficulty
        ]
        if exact:
            return exact
    return templates or QUESTION_TEMPLATES


def _choose_question_template(plan_reason, target_difficulty, rng):
    return rng.choice(_templates_for_reason(plan_reason, target_difficulty))


def question_template_options():
    return [
        {
            "key": template["key"],
            "label": template["label"],
            "difficulty": template["difficulty"],
            "operation": template["operation"],
        }
        for template in QUESTION_TEMPLATES
    ]


def build_focus(
    topic_key,
    position,
    rng=None,
    avoid_section_ids=None,
    plan_reason="coverage",
):
    rng = rng or random.SystemRandom()
    topic = topic_catalog()[topic_key]
    avoid_section_ids = set(avoid_section_ids or [])
    target_difficulty = _difficulty_for_plan_reason(plan_reason, position)
    question_template = _choose_question_template(
        plan_reason, target_difficulty, rng
    )
    available_sections = [
        section
        for section in topic["sections"]
        if section["id"] not in avoid_section_ids
    ]
    section = rng.choice(available_sections or topic["sections"])
    concept_pool = list(dict.fromkeys(section["concepts"]))
    concept_count = min(len(concept_pool), question_template["concept_count"])
    concepts = rng.sample(concept_pool, concept_count)
    return {
        "block_id": topic_key,
        "section_id": section["id"],
        "section_label": section["label"],
        "concepts": concepts,
        "question_type": question_template["key"],
        "question_type_label": question_template["label"],
        "cognitive_operation": question_template["operation"],
        "question_instruction": question_template["instruction"],
        "position": position,
        "plan_reason": plan_reason,
        "target_difficulty": target_difficulty,
    }


def _answered_turns(session):
    return [
        turn
        for turn in sorted(session.turns, key=lambda item: item.position)
        if turn.answer is not None
    ]


def _topic_state(topic_data):
    if topic_data["asked"] == 0:
        return "unseen"
    if topic_data["critical_errors"]:
        return "weak"
    if any(score >= 3 for score in topic_data["scores"]):
        return "strong"
    if any(score >= 2 for score in topic_data["scores"]):
        return "partial"
    return "weak"


def topic_confidence(session):
    confidence = {
        topic_key: {
            "topic_key": topic_key,
            "asked": 0,
            "scores": [],
            "critical_errors": 0,
            "missed_concepts": [],
            "misconceptions": [],
            "section_ids": [],
            "followups": 0,
            "state": "unseen",
        }
        for topic_key in session.selected_topics
    }

    for turn in _answered_turns(session):
        if turn.topic_key not in confidence:
            continue
        item = confidence[turn.topic_key]
        analysis = turn.analysis or {}
        focus = turn.focus or {}
        item["asked"] += 1
        item["scores"].append(int(analysis.get("answer_score", 0)))
        item["critical_errors"] += 1 if analysis.get("critical_error") else 0
        item["missed_concepts"].extend(analysis.get("missed_concepts", []))
        item["misconceptions"].extend(analysis.get("misconceptions", []))
        if focus.get("section_id"):
            item["section_ids"].append(focus["section_id"])
        if focus.get("plan_reason") in {"rescue", "clarify"}:
            item["followups"] += 1

    for item in confidence.values():
        item["state"] = _topic_state(item)
    return confidence


def _ordered_topics_for_session(session):
    scheduled = [
        topic_key
        for topic_key in (session.topic_schedule or [])
        if topic_key in session.selected_topics
    ]
    return scheduled + [
        topic_key for topic_key in session.selected_topics if topic_key not in scheduled
    ]


def _first_topic_by_state(session, confidence, states, allow_followup=False):
    for topic_key in _ordered_topics_for_session(session):
        item = confidence[topic_key]
        if item["state"] not in states:
            continue
        if allow_followup and item["followups"] >= MAX_FOLLOWUPS_PER_TOPIC:
            continue
        return topic_key
    return None


def choose_next_seed(session, position, rng=None):
    rng = rng or random.SystemRandom()
    confidence = topic_confidence(session)

    topic_key = _first_topic_by_state(session, confidence, {"unseen"})
    plan_reason = "coverage"

    if topic_key is None:
        topic_key = _first_topic_by_state(
            session, confidence, {"weak"}, allow_followup=True
        )
        plan_reason = "rescue"

    if topic_key is None:
        topic_key = _first_topic_by_state(
            session, confidence, {"partial"}, allow_followup=True
        )
        plan_reason = "clarify"

    if topic_key is None:
        strong_topics = [
            topic
            for topic in _ordered_topics_for_session(session)
            if confidence[topic]["state"] == "strong"
        ]
        topic_key = rng.choice(strong_topics or _ordered_topics_for_session(session))
        plan_reason = "challenge"

    focus = build_focus(
        topic_key,
        position,
        rng=rng,
        avoid_section_ids=confidence[topic_key]["section_ids"],
        plan_reason=plan_reason,
    )
    return {
        "topic_key": topic_key,
        "focus": focus,
        "question_limit": question_limit_for_topics(session.selected_topics),
        "confidence": confidence[topic_key],
    }
