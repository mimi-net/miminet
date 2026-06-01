from ai_interview.catalog import topic_catalog, validate_topic_keys
from ai_interview.question_bank import choose_question


def build_topic_schedule(topic_keys):
    selected = set(validate_topic_keys(topic_keys))
    return [topic_key for topic_key in topic_catalog() if topic_key in selected]


def pair_count_for_topics(topic_keys):
    return len(build_topic_schedule(topic_keys))


def build_main_focus(question, pair_position):
    return {
        "flow_type": "main",
        "pair_position": pair_position,
        "source_question_id": question["id"],
        "reference_answer": question["reference_answer"],
        "difficulty": "mechanism",
    }


def build_followup_focus(main_turn, reference_answer):
    return {
        "flow_type": "followup",
        "pair_position": main_turn.focus["pair_position"],
        "source_question_id": main_turn.focus["source_question_id"],
        "reference_answer": reference_answer,
        "difficulty": "advanced",
    }


def choose_main_question(topic_key, pair_position, rng=None):
    question = choose_question(topic_key, rng=rng)
    return question, build_main_focus(question, pair_position)
