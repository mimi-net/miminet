import json
from functools import lru_cache
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=1)
def topic_catalog():
    with (DATA_DIR / "topics.json").open("r", encoding="utf-8") as source:
        topics = json.load(source)
    return {topic["key"]: topic for topic in topics}


def public_topics():
    return [
        {"key": topic["key"], "label": topic["label"]}
        for topic in topic_catalog().values()
    ]


def validate_topic_keys(topic_keys):
    known_topics = topic_catalog()
    normalized = []

    for topic_key in topic_keys or []:
        if topic_key in known_topics and topic_key not in normalized:
            normalized.append(topic_key)

    return normalized


def topic_label(topic_key):
    return topic_catalog().get(topic_key, {}).get("label", topic_key)
