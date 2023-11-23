from miminet_model import db
from quiz.entity.Question import Question
from quiz.entity.QuizMixins import IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, GUID


class TextQuestion(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model):

    __tablename__ = "text_question"

    id = db.Column(GUID(), db.ForeignKey(Question.id), primary_key=True)
    text_type = db.Column(db.String(32), default="")

    question = db.relationship(
        'Question',
        uselist=False,
        back_populates='text_question'
    )
