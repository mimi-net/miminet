from miminet_model import db
from quiz.entity.QuizMixins import IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin


class Test(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model):

    __tablename__ = "test"

    name = db.Column(db.String(512), default="")
    description = db.Column(db.String(512), default="")

    sections = db.relationship("Section", back_populates="test")
