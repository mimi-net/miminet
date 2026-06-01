from ai_interview.catalog import topic_catalog, validate_topic_keys
from ai_interview.question_bank import choose_question


PAIRS_PER_TOPIC = 2


def build_topic_schedule(topic_keys):
    selected = set(validate_topic_keys(topic_keys))
    return [topic_key for topic_key in topic_catalog() if topic_key in selected]


def pair_count_for_topics(topic_keys):
    return len(build_topic_schedule(topic_keys)) * PAIRS_PER_TOPIC


def topic_for_pair(topic_keys, pair_position):
    schedule = build_topic_schedule(topic_keys)
    topic_index = (pair_position - 1) // PAIRS_PER_TOPIC
    return schedule[topic_index]


def topic_position_for_pair(pair_position):
    return (pair_position - 1) // PAIRS_PER_TOPIC + 1


def topic_pair_position(pair_position):
    return (pair_position - 1) % PAIRS_PER_TOPIC + 1


def question_position_for_turn(pair_position, flow_type):
    return (topic_pair_position(pair_position) - 1) * 2 + (
        2 if flow_type == "followup" else 1
    )


def build_main_focus(question, pair_position):
    return {
        "flow_type": "main",
        "pair_position": pair_position,
        "topic_position": topic_position_for_pair(pair_position),
        "topic_pair_position": topic_pair_position(pair_position),
        "source_question_id": question["id"],
        "reference_answer": question["reference_answer"],
        "difficulty": "mechanism",
    }


def build_followup_focus(main_turn, reference_answer):
    return {
        "flow_type": "followup",
        "pair_position": main_turn.focus["pair_position"],
        "topic_position": main_turn.focus["topic_position"],
        "topic_pair_position": main_turn.focus["topic_pair_position"],
        "source_question_id": main_turn.focus["source_question_id"],
        "reference_answer": reference_answer,
        "difficulty": "advanced",
    }


def choose_main_question(topic_key, pair_position, rng=None, excluded_ids=None):
    question = choose_question(topic_key, rng=rng, excluded_ids=excluded_ids)
    return question, build_main_focus(question, pair_position)
