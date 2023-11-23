from miminet_model import db
from quiz.entity.QuizMixins import IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, GUID


class SortingQuestion(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model):

    __tablename__ = "sorting_question"

    id = db.Column(GUID(), db.ForeignKey('text_question.id'), primary_key=True)
    right_sequence = db.Column(db.UnicodeText, default="")
    explanation = db.Column(db.String(512), default="")
