import json
import uuid

from sqlalchemy import types
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.orm import declared_attr

from miminet_model import db


class GUID(TypeDecorator):
    impl = CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value


class Json(TypeDecorator):

    @property
    def python_type(self):
        return object

    impl = types.String

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_literal_param(self, value, dialect):
        return value

    def process_result_value(self, value, dialect):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return None


class IdMixin(object):

    __table_args__ = {'extend_existing': True}

    id = db.Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))


class SoftDeleteMixin(object):

    __table_args__ = {'extend_existing': True}

    is_deleted = db.Column(db.Boolean, default=False)


class TimeMixin(object):

    __table_args__ = {'extend_existing': True}

    created_on = db.Column(db.DateTime, default=db.func.now())
    updated_on = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())


class CreatedByMixin(object):

    __table_args__ = {'extend_existing': True}

    @declared_attr
    def created_by_id(cls):
        return db.Column('created_by_id', db.ForeignKey('user.id'))

    @declared_attr
    def created_by_user(cls):
        return db.relationship("User")
