import json
import random
import uuid
from typing import Any, Dict, List, Optional, cast

from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import has_request_context
from flask_login import current_user
from markupsafe import Markup
from miminet_model import Network, db
from quiz.entity.entity import (
    Question,
    Answer,
    Organization,
    QuizSession,
    Section,
    SessionQuestion,
    Test,
)
from sqlalchemy.orm import joinedload


def calculate_question_count(section: Section) -> int:
    if section.meta_description:
        try:
            meta_data = json.loads(section.meta_description)
            return sum(meta_data.values())
        except json.JSONDecodeError:
            return 0
    return len(section.questions)


MOSCOW_TZ = ZoneInfo("Europe/Moscow")
ORGANIZATION_LOGOS_DIR = (
    Path(__file__).resolve().parents[2] / "static" / "images" / "logo_organizations"
)


def is_answer_available(section):
    available_answer = True
    if section and section.results_available_from:
        now_moscow = datetime.now(MOSCOW_TZ)

        if section.results_available_from.tzinfo is None:
            results_time = section.results_available_from.replace(tzinfo=MOSCOW_TZ)
        else:
            results_time = section.results_available_from.astimezone(MOSCOW_TZ)

        available_answer = results_time <= now_moscow

    return available_answer


def normalize_organization_domain(domain: Optional[str]) -> Optional[str]:
    if domain is None:
        return None

    normalized_domain = domain.strip()
    if not normalized_domain:
        return None

    if "://" in normalized_domain:
        return normalized_domain

    return f"https://{normalized_domain.lstrip('/')}"


@lru_cache(maxsize=128)
def resolve_organization_logo_filename(logo_uri: Optional[str]) -> Optional[str]:
    if logo_uri is None:
        return None

    logo_filename = Path(logo_uri.strip()).name
    if not logo_filename:
        return None

    if not (ORGANIZATION_LOGOS_DIR / logo_filename).is_file():
        return None

    return logo_filename


def get_organizations_by_id(organization_ids) -> Dict[int, Organization]:
    if not organization_ids:
        return {}

    return {
        organization.id: organization
        for organization in Organization.query.filter(
            Organization.id.in_(organization_ids)
        ).all()
    }


def to_section_dto_list(sections: List[Section]):
    dto_list: List[SectionDto] = list(
        map(
            lambda our_section: SectionDto(
                section_id=our_section.id,
                section_name=our_section.name,
                timer=our_section.timer,
                description=our_section.description,
                question_count=calculate_question_count(our_section),
                is_exam=our_section.is_exam,
                is_answer_available=is_answer_available(our_section),
                results_available_from=our_section.results_available_from,
            ),
            sections,
        )
    )
    return dto_list


def to_test_dto_list(tests: List[Test]):
    user_id = get_current_user_id()
    organization_ids = {
        our_test.organization_id
        for our_test in tests
        if getattr(our_test, "organization_id", None) is not None
    }
    organizations_by_id = get_organizations_by_id(organization_ids)
    active_sections_by_test: Dict[int, List[Section]] = {
        our_test.id: get_active_sections(our_test) for our_test in tests
    }
    all_section_ids = [
        section.id
        for sections in active_sections_by_test.values()
        for section in sections
    ]
    solved_question_counts_by_section = get_last_correct_question_count_by_section(
        all_section_ids, user_id
    )

    dto_list: List[TestDto] = []
    for our_test in tests:
        active_sections = active_sections_by_test.get(our_test.id, [])

        organization_id = cast(
            Optional[int], getattr(our_test, "organization_id", None)
        )
        organization = (
            organizations_by_id.get(organization_id)
            if organization_id is not None
            else None
        )
        (
            solved_question_count,
            total_question_count,
            progress_percent,
        ) = calculate_test_progress(active_sections, solved_question_counts_by_section)

        dto_list.append(
            TestDto(
                test_id=our_test.id,
                test_name=our_test.name,
                author_name=our_test.created_by_user.nick,
                description=our_test.description,
                is_retakeable=our_test.is_retakeable,
                is_ready=our_test.is_ready,
                section_count=len(active_sections),
                solved_question_count=solved_question_count,
                total_question_count=total_question_count,
                progress_percent=progress_percent,
                organization_id=organization_id,
                organization_name=getattr(organization, "name", None),
                organization_logo_uri=resolve_organization_logo_filename(
                    getattr(organization, "logo_uri", None)
                ),
                organization_domain=normalize_organization_domain(
                    getattr(organization, "domain", None)
                ),
            )
        )

    return dto_list


def get_current_user_id():
    if not has_request_context():
        return None

    if not current_user.is_authenticated:
        return None

    return current_user.id


def get_active_sections(test: Test) -> List[Section]:
    return [
        section
        for section in cast(List[Section], test.sections)
        if not section.is_deleted
    ]


def count_correct_answers_in_session(session: QuizSession) -> int:
    return sum(
        1
        for question in cast(List[SessionQuestion], session.sessions)
        if question.is_correct
    )


def get_last_correct_question_count_by_section(
    section_ids: List[int], user_id
) -> Dict[int, int]:
    if not section_ids or user_id is None:
        return {}

    sessions = (
        QuizSession.query.options(joinedload(cast(Any, QuizSession.sessions)))
        .filter(QuizSession.section_id.in_(section_ids))
        .filter(QuizSession.created_by_id == user_id)
        .filter(QuizSession.is_deleted.is_(False))
        .order_by(QuizSession.section_id.asc(), QuizSession.finished_at.desc())
        .all()
    )

    section_progress: Dict[int, int] = {}
    for session in sessions:
        if session.section_id in section_progress:
            continue
        section_progress[int(session.section_id)] = count_correct_answers_in_session(
            session
        )

    return section_progress


def calculate_progress_percent(
    solved_question_count: int, total_question_count: int
) -> int:
    if total_question_count <= 0:
        return 0

    normalized_solved_count = max(0, min(solved_question_count, total_question_count))
    return round((normalized_solved_count / total_question_count) * 100)


def calculate_test_progress(
    sections: List[Section], solved_question_counts_by_section: Dict[int, int]
):
    solved_question_count = 0
    total_question_count = 0

    for section in sections:
        question_count = calculate_question_count(section)
        total_question_count += question_count
        solved_question_count += min(
            solved_question_counts_by_section.get(section.id, 0),
            question_count,
        )

    progress_percent = calculate_progress_percent(
        solved_question_count, total_question_count
    )

    return solved_question_count, total_question_count, progress_percent


def to_question_for_editor_dto_list(questions: List[Question]):
    dto_list: List[QuestionForEditorDto] = list(
        map(
            lambda question: QuestionForEditorDto(
                question_id=question.id, question_text=question.text
            ),
            questions,
        )
    )

    return dto_list


class PracticeAnswerResultDto:
    def __init__(self, score: int, explanation: str, max_score: int, hints: list):
        self.score = score
        self.explanation = explanation
        self.max_score = max_score
        self.hints = hints

    def to_dict(self):
        return {
            "score": self.score,
            "explanation": self.explanation,
            "max_score": self.max_score,
            "hints": self.hints,
        }


def calculate_max_score(requirements: list) -> int:
    def recursive_sum(data):
        if isinstance(data, dict):
            points = data.get("points", 0)
            valid_points = (
                points if isinstance(points, (int, float)) and points > 0 else 0
            )
            return valid_points + sum(recursive_sum(value) for value in data.values())
        elif isinstance(data, list):
            return sum(recursive_sum(item) for item in data)
        return 0

    return recursive_sum(requirements)


class AnswerResultDto:
    def __init__(self, explanation, is_correct: bool) -> None:
        self.explanation = explanation
        self.is_correct = is_correct

    def to_dict(self):
        if isinstance(self.explanation, list):
            return {"explanation": [self.explanation], "is_correct": self.is_correct}
        else:
            return {"explanation": self.explanation, "is_correct": self.is_correct}


class AnswerDto:
    def __init__(self, question_type: str, answer: Answer) -> None:
        if question_type == "matching":
            self.left = answer.left
            self.right = answer.right
        else:
            self.variant = answer.variant

    def to_dict(self):
        attributes = ["variant", "left", "right"]
        data = {attr: getattr(self, attr) for attr in attributes if hasattr(self, attr)}
        return data


class PracticeQuestionDto:
    def __init__(self, user_id, practice_question, session_question_id: str) -> None:
        attributes = [
            "description",
            "available_host",
            "available_l1_hub",
            "available_server",
            "available_l2_switch",
            "available_l3_router",
        ]

        for attribute in attributes:
            setattr(self, attribute, getattr(practice_question, attribute))

        session_question = SessionQuestion.query.filter_by(
            id=session_question_id
        ).first()

        if session_question.network_guid:
            net_copy = Network.query.filter_by(
                guid=session_question.network_guid
            ).first()
        else:
            net = Network.query.filter(
                Network.guid == practice_question.start_configuration
            ).first()

            u = uuid.uuid4()
            net_copy = Network(
                guid=str(u),
                author_id=user_id,
                network=net.network,
                title=net.title,
                description="Network copy",
                preview_uri=net.preview_uri,
                is_task=True,
            )
            db.session.add(net_copy)

            session_question.network_guid = net_copy.guid
            db.session.commit()

        escaped_string = net_copy.network.replace('\\"', '"').replace('"', '\\"')
        self.start_configuration = escaped_string
        self.network_guid = net_copy.guid

    def to_dict(self):
        attributes = [
            "description",
            "available_host",
            "available_l1_hub",
            "available_server",
            "available_l2_switch",
            "available_l3_router",
            "start_configuration",
            "network_guid",
        ]

        return {attribute: str(getattr(self, attribute)) for attribute in attributes}


def get_question_type(question_type: int):
    types = {0: "practice", 1: "variable", 2: "sorting", 3: "matching"}
    return types.get(question_type, "")


class QuestionDto:
    def __init__(self, user_id, question: Question, session_question_id) -> None:
        self.question_type = get_question_type(question.question_type)
        self.question_text = Markup.unescape(question.text)
        self.correct_count = 0

        self.images = [img.file_path for img in question.images]  # type: ignore

        if self.question_type == "practice":
            self.practice_question = PracticeQuestionDto(
                user_id, question.practice_question, session_question_id
            ).to_dict()
            return

        filtered_answers = Answer.query.filter_by(
            question_id=question.id, is_deleted=False
        ).all()

        if self.question_type == "variable":
            self.correct_count = sum(answer.is_correct for answer in filtered_answers)

        self.answers = [
            AnswerDto(question_type=self.question_type, answer=answer).to_dict()
            for answer in filtered_answers
        ]
        random.shuffle(self.answers)

        # text_question = question.text_question
        # self.text_type = text_question.text_type

        # if self.question_type == "variable":
        #     variable_question = text_question.variable_question
        #     self.answers = [
        #         AnswerDto(answer_text=i.answer_text).to_dict()
        #         for i in Answer.query.filter_by(
        #             variable_question_id=variable_question.id, is_deleted=False
        #         ).all()
        #     ]
        #
        # elif self.question_type == "matching":
        #     matching_question = text_question.matching_question
        #
        #     data = matching_question.map
        #     keys = list(data.keys())
        #     values = list(data.values())
        #     random.shuffle(keys)
        #     res = {keys[i]: values[i] for i in range(len(keys))}
        #
        #     self.answers = json.dumps(res)
        #
        # elif self.question_type == "sorting":
        #     sorting_question = text_question.sorting_question
        #     words = sorting_question.right_sequence.split()
        #     random.shuffle(words)
        #     self.answers = " ".join(words)


class SectionDto:
    def __init__(
        self,
        section_id: str,
        section_name: str,
        timer: str,
        description: str,
        question_count: int,
        is_exam: bool,
        is_answer_available: bool,
        results_available_from,
    ):
        self.section_id = section_id
        self.section_name = section_name
        self.timer = timer
        self.description = description
        self.question_count = question_count
        self.is_exam = is_exam
        self.answer_available = is_answer_available
        self.results_available_from = results_available_from

        current_user_sessions = QuizSession.query.filter(
            QuizSession.created_by_id == current_user.id
        ).filter(QuizSession.section_id == section_id)

        self.sessions_count = current_user_sessions.count()

        session = current_user_sessions.order_by(QuizSession.finished_at.desc()).first()
        if session:
            self.last_correct_count = count_correct_answers_in_session(session)
            if session.guid:
                self.session_guid = session.guid

        section = Section.query.get(section_id)
        test = section.test

        unfinished_session = (
            current_user_sessions.filter(QuizSession.finished_at.is_(None))
            .order_by(QuizSession.created_on.desc())
            .first()
        )

        self.there_is_unfinished = False

        if unfinished_session and is_exam and not test.is_retakeable:
            self.there_is_unfinished = True

            unanswered = (
                SessionQuestion.query.filter_by(quiz_session_id=unfinished_session.id)
                .filter(SessionQuestion.is_correct.is_(None))
                .order_by(SessionQuestion.id.asc())
                .first()
            )

            if unanswered:
                self.last_question = unanswered.id


class TestDto:
    def __init__(
        self,
        test_id: str,
        test_name: str,
        author_name: str,
        description: str,
        is_retakeable: bool,
        is_ready: bool,
        section_count: int,
        solved_question_count: int,
        total_question_count: int,
        progress_percent: int,
        organization_id: Optional[int] = None,
        organization_name: Optional[str] = None,
        organization_logo_uri: Optional[str] = None,
        organization_domain: Optional[str] = None,
    ):
        self.test_id = test_id
        self.test_name = test_name
        self.author_name = author_name
        self.description = description
        self.is_retakeable = is_retakeable
        self.is_ready = is_ready
        self.section_count = section_count
        self.solved_question_count = solved_question_count
        self.total_question_count = total_question_count
        self.progress_percent = progress_percent
        self.organization_id = organization_id
        self.organization_name = organization_name
        self.organization_logo_uri = organization_logo_uri
        self.organization_domain = organization_domain


class QuestionForEditorDto:
    def __init__(self, question_id: str, question_text: str):
        self.question_id = question_id
        self.question_text = question_text


class SessionResultDto:
    def __init__(
        self,
        test_name: str,
        section_name: str,
        theory_correct: int,
        theory_count: int,
        practice_results: list,
        results: list,  # Добавили поле для списка вопросов
        start_time: str,
        time_spent: str,
        is_exam: bool,
        answer_available: bool,
        available_from,
    ):
        self.test_name = test_name
        self.section_name = section_name
        self.theory_correct = theory_correct
        self.theory_count = theory_count
        self.practice_results = practice_results
        self.results = results
        self.start_time = start_time
        self.time_spent = time_spent
        self.is_exam = is_exam
        self.answer_available = answer_available
        self.available_from = available_from

    def to_dict(self):
        return {
            "test_name": self.test_name,
            "section_name": self.section_name,
            "theory_correct": self.theory_correct,
            "theory_count": self.theory_count,
            "practice_results": self.practice_results,
            "results": self.results,
            "start_time": self.start_time,
            "time_spent": self.time_spent,
            "is_exam": self.is_exam,
            "answer_available": self.answer_available,
            "results_available_from": self.available_from,
        }
