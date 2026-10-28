"""Регрессии диагностики ошибок восстановления журналов при запуске."""

from datetime import datetime
import logging
import traceback

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import database_bootstrap
from database_bootstrap import init_db


@pytest.fixture
def failing_repair(monkeypatch, mocker, mock_db, mock_sqlalchemy_inspect):
    """Подменяем только БД: настоящий обработчик ошибки пишет в стандартный logging."""
    monkeypatch.setenv("MODE", "dev")
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
    mock_sqlalchemy_inspect.has_table.return_value = True
    log_model = mocker.patch("database_bootstrap.SimulateLog")
    return log_model.query.filter.return_value.update, mock_db.session


def _error_record(caplog):
    """Одна ошибка операции должна давать одно диагностическое событие."""
    records = [
        r
        for r in caplog.records
        if r.name == "miminet_model" and r.levelno >= logging.ERROR
    ]
    assert len(records) == 1
    return records[0]


@pytest.mark.parametrize("failure_stage", ["update", "commit"])
def test_repair_failure_logs_traceback_and_context_without_changing_policy(
    failing_repair, failure_stage, mocker, caplog
):
    """Сохраняем возврат None, но получаем место ошибки, этап и время события."""
    update, session = failing_repair
    failure = SQLAlchemyError("test repair failure")

    def raise_failure(*_args, **_kwargs):
        raise failure

    (
        update if failure_stage == "update" else session.commit
    ).side_effect = raise_failure
    with caplog.at_level(logging.ERROR, logger="miminet_model"):
        assert init_db(mocker.MagicMock()) is None

    record = _error_record(caplog)
    assert record.exc_info is not None
    assert "raise_failure" in [
        frame.name for frame in traceback.extract_tb(record.exc_info[2])
    ]
    assert record.bootstrap_stage == "repair_pending_logs"
    assert record.bootstrap_mode == "dev"
    assert record.error_type == "SQLAlchemyError"
    assert datetime.fromisoformat(record.event_time).tzinfo is not None
    formatted = logging.Formatter(logging.BASIC_FORMAT).format(record)
    assert "ERROR:miminet_model:" in formatted
    assert "stage=repair_pending_logs" in formatted
    assert record.event_time in formatted
    # Изменение rollback/исключений — отдельная задача, не побочный эффект логирования.
    session.rollback.assert_not_called()
    if failure_stage == "update":
        session.commit.assert_not_called()


@pytest.mark.parametrize("sqlstate", ["23514", "23505", None, "unsafe-code\n"])
def test_diagnostics_redact_sql_parameters_and_driver_messages(
    failing_repair, sqlstate, mocker, caplog
):
    """Traceback сохраняет кадры, но не выводит SQL, параметры и текст драйвера."""
    update, _session = failing_repair
    secret = "sentinel-secret-not-for-logs"

    class DriverFailure(Exception):
        pgcode = sqlstate

    failure = IntegrityError(
        "UPDATE simulate_log SET network=:network",
        {"network": secret, "password": secret},
        DriverFailure(secret),
    )

    def raise_failure(*_args, **_kwargs):
        raise failure

    update.side_effect = raise_failure
    with caplog.at_level(logging.ERROR, logger="miminet_model"):
        init_db(mocker.MagicMock())

    record = _error_record(caplog)
    formatted = logging.Formatter(logging.BASIC_FORMAT).format(record)
    assert record.exc_info is not None
    assert record.error_type == "IntegrityError"
    assert record.sqlstate == (
        sqlstate if sqlstate in ("23514", "23505") else "unknown"
    )
    assert "Traceback" in formatted
    assert secret not in formatted
    assert "UPDATE simulate_log" not in formatted
    assert "unsafe-code" not in formatted


def test_exception_chains_do_not_leak_private_payload(failing_repair, mocker, caplog):
    """Вложенная причина исключения тоже может содержать приватные данные."""
    update, _session = failing_repair
    secret = "sentinel-private-cause"
    failure = SQLAlchemyError("outer database error")

    def raise_failure(*_args, **_kwargs):
        try:
            raise ValueError(secret)
        except ValueError as cause:
            raise failure from cause

    update.side_effect = raise_failure
    with caplog.at_level(logging.ERROR, logger="miminet_model"):
        init_db(mocker.MagicMock())
    record = _error_record(caplog)
    formatted = logging.Formatter(logging.BASIC_FORMAT).format(record)
    assert record.exc_info is not None
    assert "Traceback" in formatted
    assert secret not in formatted
    assert "outer database error" not in formatted


def test_repeated_failures_do_not_add_or_duplicate_handlers(
    failing_repair, mocker, caplog
):
    """Повторный запуск не добавляет обработчики и не дублирует события."""
    update, _session = failing_repair
    update.side_effect = SQLAlchemyError("test failure")
    logger_handlers = tuple(database_bootstrap.logger.handlers)
    root_handlers = tuple(logging.getLogger().handlers)
    with caplog.at_level(logging.ERROR, logger="miminet_model"):
        init_db(mocker.MagicMock())
        init_db(mocker.MagicMock())
    assert len([r for r in caplog.records if r.name == "miminet_model"]) == 2
    assert tuple(database_bootstrap.logger.handlers) == logger_handlers
    assert tuple(logging.getLogger().handlers) == root_handlers


def test_successful_repair_does_not_emit_error(failing_repair, mocker, caplog):
    """Успешное восстановление не создаёт ложного сообщения об ошибке."""
    with caplog.at_level(logging.ERROR, logger="miminet_model"):
        assert init_db(mocker.MagicMock()) is None
    assert not [r for r in caplog.records if r.name == "miminet_model"]
