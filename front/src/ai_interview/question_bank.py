import json
import random
from functools import lru_cache

from ai_interview.catalog import DATA_DIR, topic_catalog


QUESTION_FIELDS = {"id", "topic_key", "question", "reference_answer"}


def _validate_question(question, source):
    if not isinstance(question, dict) or set(question) != QUESTION_FIELDS:
        raise ValueError(f"Некорректная структура вопроса в {source}.")

    normalized = {key: str(question.get(key) or "").strip() for key in QUESTION_FIELDS}
    if not all(normalized.values()):
        raise ValueError(f"Пустое обязательное поле вопроса в {source}.")
    if normalized["topic_key"] not in topic_catalog():
        raise ValueError(f"Неизвестная тема вопроса {normalized['id']} в {source}.")
    return normalized


@lru_cache(maxsize=1)
def load_question_bank():
    question_dir = DATA_DIR / "example_questions"
    questions = []
    ids = set()

    for path in sorted(question_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as source:
            payload = json.load(source)
        if not isinstance(payload, list):
            raise ValueError(f"Банк вопросов {path.name} должен быть JSON-массивом.")

        for item in payload:
            question = _validate_question(item, path.name)
            if question["id"] in ids:
                raise ValueError(f"Повторяющийся id вопроса: {question['id']}.")
            ids.add(question["id"])
            questions.append(question)

    topics_with_questions = {question["topic_key"] for question in questions}
    missing_topics = set(topic_catalog()) - topics_with_questions
    if missing_topics:
        raise ValueError(
            "В банке нет вопросов для тем: " + ", ".join(sorted(missing_topics))
        )
    return questions


def questions_for_topic(topic_key):
    return [
        question
        for question in load_question_bank()
        if question["topic_key"] == topic_key
    ]


def choose_question(topic_key, rng=None):
    questions = questions_for_topic(topic_key)
    if not questions:
        raise ValueError(f"В банке нет вопросов для темы {topic_key}.")
    return (rng or random.SystemRandom()).choice(questions)
