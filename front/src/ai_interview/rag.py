import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache

from ai_interview.catalog import DATA_DIR, topic_catalog


WORD_RE = re.compile(r"[A-Za-zА-Яа-я0-9/+.-]+")

CLASSIFIED_TOPIC_MAP = {
    "TCP/IP": "network_l3",
    "IP-адресация": "network_l3",
    "ARP": "network_l3",
    "ICMP": "transport_and_icmp",
    "Маршрутизация": "network_l3",
    "TCP и UDP": "transport_and_icmp",
    "DHCP": "advanced_networking",
    "NAT": "network_l3",
    "VLAN": "advanced_networking",
    "Ethernet (CSMA/CD)": "ethernet_l2",
    "PMTUD": "advanced_networking",
    "Модель OSI": "network_intro",
    "Туннели и инкапсуляция": "advanced_networking",
    "Основы сетей и коммутации": "network_intro",
    "Сетевые утилиты": "transport_and_icmp",
    "Wi‑Fi": "ethernet_l2",
    "Wi-Fi": "ethernet_l2",
    "Стандарты и RFC": "network_intro",
    "Каналы связи": "network_intro",
}


COURSE_TOPIC_MAP = {
    "О курсе": "network_intro",
    "Введение": "network_intro",
    "Коммутация каналов и пакетная коммутация": "network_intro",
    "Каналы передачи данных": "network_intro",
    "Модель ISO/OSI": "network_intro",
    "Сетевые стандарты": "network_intro",
    "Ethernet (CSMA/CD)": "ethernet_l2",
    "Смотрим Ethernet кадр в Wireshark": "ethernet_l2",
    "Топологии": "ethernet_l2",
    "Концентратор (репитор, хаб)": "ethernet_l2",
    "Коммутатор (свитч)": "ethernet_l2",
    "Масштабируемость технологии канального уровня": "ethernet_l2",
    "Сетевой уровень": "network_l3",
    "IP адреса": "network_l3",
    "IP сети": "network_l3",
    "ARP": "network_l3",
    "Отправка пакета в другой сегмент сети": "network_l3",
    "Маршрутизация": "network_l3",
    "IP протокол": "network_l3",
    "NAT (Network Address Translation)": "network_l3",
    "Групповые адреса (Multicast)": "network_l3",
    "IPv6": "network_l3",
    "Транспортный уровень": "transport_and_icmp",
    "UDP": "transport_and_icmp",
    "TCP": "transport_and_icmp",
    "Тонкости работы TCP": "transport_and_icmp",
    "ICMP": "transport_and_icmp",
    "VLAN": "advanced_networking",
    "VPN (туннелирование)": "advanced_networking",
    "DHCP": "advanced_networking",
    "ARP proxy": "advanced_networking",
    "Proxy ARP": "advanced_networking",
    "NAT (разновидности)": "advanced_networking",
    "PMTUD (Path MTU Discovery)": "advanced_networking",
}


@dataclass(frozen=True)
class RetrievedContext:
    chunks: list
    example_questions: list
    text: str

    def provenance(self):
        return {
            "chunks": [
                {
                    "id": chunk["id"],
                    "block_id": chunk["topic"],
                    "course_topic": chunk.get("source_topic"),
                    "subtopics": chunk.get("subtopics", []),
                }
                for chunk in self.chunks
            ],
            "example_question_ids": [
                example["id"] for example in self.example_questions
            ],
            "context_chars": len(self.text),
        }


def _normalize_words(value):
    return {part.casefold() for part in WORD_RE.findall(str(value or ""))}


def _jsonl_rows(path):
    rows = []
    with path.open("r", encoding="utf-8") as source:
        for line in source:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _heading_for_chunk(chunk):
    heading_path = chunk.get("heading_path") or []
    if heading_path:
        return " > ".join(str(part) for part in heading_path if part)
    return (
        chunk.get("heading")
        or chunk.get("topic")
        or chunk.get("section")
        or chunk["id"]
    )


def _topic_key_for_chunk(chunk):
    raw_topic = chunk.get("topic")
    if raw_topic in topic_catalog():
        return raw_topic
    if raw_topic in COURSE_TOPIC_MAP:
        return COURSE_TOPIC_MAP[raw_topic]

    topic_text = str(chunk.get("topic") or "").casefold()
    for marker, topic_key in COURSE_TOPIC_MAP.items():
        if marker.casefold() in topic_text:
            return topic_key

    heading_text = " ".join(
        str(part) for part in chunk.get("heading_path", [])
    ).casefold()
    for marker, topic_key in COURSE_TOPIC_MAP.items():
        if marker.casefold() in heading_text:
            return topic_key

    fallback_text = " ".join(
        str(part) for part in [chunk.get("section", ""), chunk.get("topic_file", "")]
    ).casefold()
    for marker, topic_key in COURSE_TOPIC_MAP.items():
        if marker.casefold() in fallback_text:
            return topic_key
    return None


def _normalize_chunk(chunk):
    topic_key = _topic_key_for_chunk(chunk)
    if topic_key is None:
        return None

    normalized = dict(chunk)
    normalized["source_topic"] = chunk.get("topic")
    normalized["topic"] = topic_key
    normalized["block_id"] = topic_key
    normalized["heading"] = _heading_for_chunk(chunk)
    normalized["subtopics"] = (
        chunk.get("subtopics") or chunk.get("subtopics_in_chunk") or []
    )
    normalized["text"] = str(chunk.get("text") or "").strip()
    return normalized


@lru_cache(maxsize=1)
def load_chunks():
    chunks = []
    for chunk in _jsonl_rows(DATA_DIR / "stepik_network_course.jsonl"):
        normalized = _normalize_chunk(chunk)
        if normalized is not None and normalized["text"]:
            chunks.append(normalized)
    return chunks


def load_chunks_for_topic(topic_key):
    return [chunk for chunk in load_chunks() if chunk["topic"] == topic_key]


@lru_cache(maxsize=1)
def load_example_questions():
    example_dir = DATA_DIR / "example_questions"
    rows = []

    examples_jsonl = example_dir / "examples.jsonl"
    if examples_jsonl.exists():
        for row in _jsonl_rows(examples_jsonl):
            row = dict(row)
            row["source_topic"] = row.get("topic")
            if row["topic"] in topic_catalog():
                rows.append(row)

    for path in sorted(example_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as source:
            payload = json.load(source)
        for index, question in enumerate(payload.get("questions", []), start=1):
            topic_key = CLASSIFIED_TOPIC_MAP.get(question.get("topic"))
            text = str(question.get("question") or "").strip()
            if not topic_key or not text:
                continue

            rows.append(
                {
                    "id": f"{path.stem}-{index}",
                    "topic": topic_key,
                    "text": text,
                    "difficulty": question.get("difficulty"),
                    "source": path.name,
                    "source_topic": question.get("topic"),
                }
            )

    deduplicated = []
    seen = set()
    for row in rows:
        key = (
            row.get("topic"),
            " ".join(WORD_RE.findall(row.get("text", "").casefold())),
        )
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(row)
    return deduplicated


def _document_words(document):
    parts = [
        document.get("heading", ""),
        document.get("text", ""),
        document.get("source_topic", ""),
        document.get("section", ""),
        " ".join(document.get("subtopics", [])),
        " ".join(document.get("heading_path", [])),
    ]
    return _normalize_words(" ".join(parts))


def _score_document(document, query_words, topic_keys, example_words):
    if document["topic"] not in topic_keys:
        return -1

    overlap = len(query_words & _document_words(document))
    example_overlap = len(example_words & _document_words(document))
    heading_overlap = len(query_words & _normalize_words(document.get("heading", "")))
    return 8 + overlap * 4 + heading_overlap * 3 + example_overlap


def _bounded_env_int(key, default, minimum, maximum):
    try:
        value = int(os.environ.get(key, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


def context_chunk_limit():
    return _bounded_env_int("AI_INTERVIEW_RAG_CHUNK_LIMIT", 3, 1, 6)


def context_char_limit():
    return _bounded_env_int("AI_INTERVIEW_RAG_CONTEXT_CHARS", 5000, 400, 6000)


def _paragraphs(text):
    return [part.strip() for part in re.split(r"\n\s*\n", text or "") if part.strip()]


def _best_excerpt(text, query_words, max_chars):
    paragraphs = _paragraphs(text)
    if not paragraphs:
        return ""

    ranked = sorted(
        enumerate(paragraphs),
        key=lambda item: len(query_words & _normalize_words(item[1])),
        reverse=True,
    )
    best_index = ranked[0][0]
    selected = [paragraphs[best_index]]
    used_indexes = {best_index}

    left = best_index - 1
    right = best_index + 1
    while len("\n\n".join(selected)) < max_chars and (
        left >= 0 or right < len(paragraphs)
    ):
        candidates = []
        if left >= 0:
            candidates.append((left, paragraphs[left]))
        if right < len(paragraphs):
            candidates.append((right, paragraphs[right]))
        candidates.sort(
            key=lambda item: len(query_words & _normalize_words(item[1])),
            reverse=True,
        )
        index, paragraph = candidates[0]
        if index in used_indexes:
            break
        if index < best_index:
            selected.insert(0, paragraph)
            left -= 1
        else:
            selected.append(paragraph)
            right += 1
        used_indexes.add(index)

    excerpt = "\n\n".join(selected)
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars].rsplit(" ", 1)[0]
    return excerpt


def _context_part(chunk, excerpt):
    subtopics = ", ".join(chunk.get("subtopics") or []) or "не указаны"
    return "\n".join(
        [
            f"[{chunk['id']}]",
            f"Блок: {topic_catalog()[chunk['topic']]['label']}",
            f"Тема курса: {chunk.get('source_topic') or chunk.get('heading')}",
            f"Подтемы чанка: {subtopics}",
            "Фрагмент курса:",
            excerpt,
        ]
    )


def retrieve_context(topic_keys, query, limit=None, max_chars=None):
    limit = limit if limit is not None else context_chunk_limit()
    max_chars = max_chars if max_chars is not None else context_char_limit()
    topic_keys = [topic for topic in topic_keys if topic in topic_catalog()]
    query_words = _normalize_words(query)
    examples = [
        question
        for question in load_example_questions()
        if question["topic"] in topic_keys
    ]
    ranked_examples = sorted(
        examples,
        key=lambda example: len(query_words & _normalize_words(example["text"])),
        reverse=True,
    )[: min(3, len(examples))]
    example_words = _normalize_words(
        " ".join(example["text"] for example in ranked_examples)
    )
    ranked_chunks = sorted(
        load_chunks(),
        key=lambda chunk: _score_document(
            chunk, query_words, topic_keys, example_words
        ),
        reverse=True,
    )

    selected = []
    text_parts = []
    current_chars = 0
    for chunk in ranked_chunks:
        if len(selected) >= limit:
            break
        if _score_document(chunk, query_words, topic_keys, example_words) < 0:
            continue

        remaining = max_chars - current_chars
        if remaining <= 0:
            break
        excerpt = _best_excerpt(chunk["text"], query_words | example_words, remaining)
        part = _context_part(chunk, excerpt)
        if len(part) > remaining:
            part = part[:remaining].rsplit(" ", 1)[0]
        if not part:
            break

        selected.append(chunk)
        text_parts.append(part)
        current_chars += len(part) + 1

    return RetrievedContext(
        chunks=selected,
        example_questions=ranked_examples,
        text="\n".join(text_parts),
    )


def is_verbatim_example(question, examples):
    question_words = " ".join(WORD_RE.findall(str(question or "").casefold()))
    return any(
        question_words
        and question_words == " ".join(WORD_RE.findall(example["text"].casefold()))
        for example in examples
    )
