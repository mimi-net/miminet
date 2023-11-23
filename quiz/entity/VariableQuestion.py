from miminet_model import db
from quiz.entity.QuizMixins import IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, GUID


class VariableQuestion(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model):

    __tablename__ = "variable_question"

    id = db.Column(GUID(), db.ForeignKey('text_question.id'), primary_key=True)

    answers = db.relationship("Answer", back_populates="variable_question")
