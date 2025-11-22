import pytest
import os
from unittest.mock import MagicMock
from psycopg2 import OperationalError

# Assumes sys.path is updated in conftest.py to include src
from app import get_database_uri
from miminet_model import ensure_db_exists, init_db


class TestConfigDB:
    """Test suite for database configuration and initialization logic."""

    def test_get_database_uri_dev(self, mock_env_dev):
        """Verify URI format for Development environment."""
        uri = get_database_uri("dev")
        assert "postgresql+psycopg2://" in uri
        assert "@localhost/" in uri
        assert "sslmode" not in uri

    def test_get_database_uri_prod(self, mock_env_prod):
        """Verify URI format and SSL parameters for Production environment."""
        uri = get_database_uri("prod")
        assert "postgresql+psycopg2://" in uri
        assert "rc1a-test" in uri
        assert "sslmode=verify-full" in uri
        assert "sslrootcert=/tmp/root.crt" in uri

    def test_get_database_uri_prod_missing_creds(self, mock_env_prod, monkeypatch):
        """Verify Fail Fast behavior when credentials are missing in Prod."""
        monkeypatch.delenv("YANDEX_POSTGRES_PASSWORD")
        with pytest.raises(ValueError, match="Missing Yandex Cloud PostgreSQL credentials"):
            get_database_uri("prod")

    def test_ensure_db_exists_prod_success(self, mock_env_prod, mock_psycopg2):
        """Verify Prod connection success does not trigger creation logic."""
        mock_connect, _ = mock_psycopg2

        res = ensure_db_exists("host", "u", "p", "db", mode="prod", sslmode="require")

        assert res is True
        mock_connect.assert_called_once()
        assert mock_connect.call_args[1]['dbname'] == 'db'

    def test_ensure_db_exists_prod_failure(self, mock_env_prod, mock_psycopg2):
        """Verify Prod connection failure raises exception immediately."""
        mock_connect, _ = mock_psycopg2
        mock_connect.side_effect = OperationalError("Connection failed")

        with pytest.raises(OperationalError):
            ensure_db_exists("host", "u", "p", "db", mode="prod")

        # CRITICAL: Must not attempt to connect to 'postgres' system DB in PROD
        assert mock_connect.call_count == 1

    def test_ensure_db_exists_dev_create(self, mock_env_dev, mock_psycopg2):
        """Verify Dev mode creates database if it's missing."""
        mock_connect, mock_cursor = mock_psycopg2

        # Sequence:
        # 1. Connect to target_db -> Fails (DB doesn't exist)
        # 2. Connect to postgres -> Succeeds
        success_conn = MagicMock()
        success_conn.cursor.return_value.__enter__.return_value = mock_cursor
        success_conn.__enter__.return_value = success_conn

        mock_connect.side_effect = [OperationalError("DB missing"), success_conn]
        mock_cursor.fetchone.return_value = None  # DB not found in pg_database

        ensure_db_exists("h", "u", "p", "new_db", mode="dev")

        assert mock_connect.call_count == 2
        # Verify second connection was to system db
        assert mock_connect.call_args[1]['dbname'] == 'postgres'
        # Verify creation SQL
        mock_cursor.execute.assert_any_call("CREATE DATABASE new_db")

    def test_init_db_dev(self, mock_env_dev, mocker, mock_sqlalchemy_inspect, mock_db):
        """Verify init_db creates schema in Dev mode."""
        mocker.patch("miminet_model.ensure_db_exists", return_value=True)

        # Simulate tables missing
        mock_sqlalchemy_inspect.has_table.return_value = False

        app_mock = MagicMock()

        init_db(app_mock)

        mock_db.create_all.assert_called_once()
        mock_sqlalchemy_inspect.has_table.assert_called_with("user")
        # Users creation check omitted as the user list is currently empty in source
