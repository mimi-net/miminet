from miminet_model import db
from quiz.entity.QuizMixins import IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin


class Section(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model):

    __tablename__ = "section"

    name = db.Column(db.String(512), default="")
    description = db.Column(db.String(512), default="")
    timer = db.Column(db.DateTime, default=db.func.now())
    test_id = db.Column(db.ForeignKey("test.id"))

    test = db.relationship("Test", back_populates="sections")
    questions = db.relationship("Question", back_populates="section")

