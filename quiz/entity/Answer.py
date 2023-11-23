from miminet_model import db
from quiz.entity.QuizMixins import IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, GUID


class Answer(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model):

    __tablename__ = "answer"

    answer_text = db.Column(db.String(512), default="")
    explanation = db.Column(db.String(512), default="")
    is_correct = db.Column(db.Boolean, default="")

    variable_question_id = db.Column(GUID(), db.ForeignKey("variable_question.id"))
    variable_question = db.relationship("VariableQuestion", back_populates="answers")
