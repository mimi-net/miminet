from miminet_model import db
from quiz.entity.QuizMixins import IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, GUID, Json


class MatchingQuestion(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model):

    __tablename__ = "matching_question"

    id = db.Column(GUID(), db.ForeignKey('text_question.id'), primary_key=True)
    map = db.Column(Json(), default="")
    explanation = db.Column(db.String(512), default="")
