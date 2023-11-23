from miminet_model import db
from quiz.entity.QuizMixins import IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, GUID
from quiz.entity.Section import Section


class Question(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model):

    __tablename__ = "question"

    question_text = db.Column(db.String(512), default="")
    question_type = db.Column(db.String(32), default="")
    section_id = db.Column(GUID(), db.ForeignKey(Section.id))

    section = db.relationship("Section", back_populates="questions")

    text_question = db.relationship(
        'TextQuestion',
        uselist=False,
        back_populates='question'
    )
