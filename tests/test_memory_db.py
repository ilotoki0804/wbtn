import sys
from pathlib import Path

import pytest
import typing

# Ensure the src directory is importable (project uses src/ layout)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbtn import Webtoon
from wbtn._base import WebtoonOpenError, WebtoonSchemaError, SCHEMA_VERSION


def test_memory_connection_requires_c_mode():
    """Opening an in-memory database with a non-'c' mode should raise."""
    # test a variety of invalid modes for :memory:
    for mode in ("r", "w", "n", "invalid"):
        with pytest.raises(WebtoonOpenError):
            with Webtoon(":memory:", connection_mode=typing.cast(typing.Any, mode)):
                pass


def test_memory_persistence_within_single_connection():
    """Data written to an in-memory DB should be available during the same connection."""
    with Webtoon(":memory:") as w:
        # sanity of connection flags
        assert w.connection.conn is not None
        assert not w.connection.read_only
        # existed should be False for a fresh in-memory DB
        assert w.connection.existed is False

        # perform some operations
        w.info["temp_key"] = "temp_value"
        assert w.info["temp_key"] == "temp_value"

        # add episode and media to ensure other managers work
        ep = w.episode.add(id="mep", name="mem-ep", state="exists")
        med = w.media.add("data", ep, 0, "image", lazy_load=False)
        assert med.data == "data"


def test_memory_application_id_and_user_version_and_upgrade():
    """Check PRAGMA application_id and user_version behavior for in-memory DB."""
    APPLICATION_ID = 0x5742544e
    with Webtoon(":memory:") as w:
        # application id should be set to WBTN magic
        with w.connection.cursor() as cur:
            appid, = cur.execute("PRAGMA application_id").fetchone()
        assert appid == APPLICATION_ID

        # initial user version should equal library SCHEMA_VERSION
        assert w.connection.file_user_version == SCHEMA_VERSION

        # upgrading user_version to a higher value should work
        new_version = SCHEMA_VERSION + 1000
        w.connection.file_user_version = new_version
        assert w.connection.file_user_version == new_version

        # trying to downgrade should raise WebtoonSchemaError
        with pytest.raises(WebtoonSchemaError):
            w.connection.file_user_version = SCHEMA_VERSION


def test_memory_accepts_journal_mode():
    with pytest.raises(WebtoonOpenError):
        with Webtoon(":memory:", journal_mode="wal"):
            pass


def test_memory_isolated_between_connections():
    """Two separate :memory: connections should not share data."""
    with Webtoon(":memory:") as w1:
        w1.info["only_in_w1"] = "value1"
        assert w1.info["only_in_w1"] == "value1"

    # new Webtoon on :memory: should be a fresh, empty DB (except system keys)
    with Webtoon(":memory:") as w2:
        with pytest.raises(KeyError):
            _ = w2.info["only_in_w1"]
