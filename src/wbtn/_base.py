from __future__ import annotations

import datetime as _datetime
import typing as _typing
import warnings as _warnings
from sqlite3 import sqlite_version as SQLITE_VERSION

VERSION = "0.0.0a2"
SCHEMA_VERSION = 1000
SCHEMA_VERSIONS = {
    "0.0.0a2": 1000,
}
SUPPORT_JSON = [3, 38, 0] <= [int(version) for version in SQLITE_VERSION.split(".")]
SUPPORT_JSONB = [3, 45, 0] <= [int(version) for version in SQLITE_VERSION.split(".")]

if not SUPPORT_JSON:  # pragma: no cover
    _warnings.warn(
        "Sqlite seems not support json functions. The package may not work properly and could result in errors."
    )

JournalModes = _typing.Literal["delete", "truncate", "persist", "memory", "wal", "off"]
JsonType = _typing.Any
RestrictedPrimitiveType = str | int | bool | float
PrimitiveType = RestrictedPrimitiveType | bytes | None
# EpisodeState = _typing.Literal["exists", "downloading", "empty", "impaired"]
EpisodeState = str | None
ConversionType = _typing.Literal["json", "jsonb", "path", "str", "bytes", "int", "float", "bool", "null"]

if _typing.TYPE_CHECKING:  # pragma: no cover
    from ._webtoon import Webtoon as WebtoonType
    from ._json_data import JsonData
    from pathlib import Path
    ValueType = PrimitiveType | JsonData | Path
    del JsonData, Path
else:
    WebtoonType = "Webtoon"
    ValueType = "PrimitiveType | JsonData"

JOURNAL_MODES = ("delete", "truncate", "persist", "memory", "wal", "off")
# EPISODE_STATE = (None, "exists", "empty", "impaired", "downloading")


def timestamp() -> float:
    return _datetime.datetime.now().timestamp()


def fromtimestamp(timestamp: float) -> _datetime.datetime:
    return _datetime.datetime.fromtimestamp(timestamp)


class WebtoonError(Exception):
    """Base exception for every wbtn errors"""


class WebtoonOpenError(WebtoonError):
    """Exceptions being occurred during opening a webtoon file"""


class WebtoonConnectionError(WebtoonError):
    """Connection with webtoon file has a problem"""


class WebtoonSchemaError(WebtoonError):
    """Exceptions regarding webtoon schema"""


class WebtoonPathError(WebtoonError):
    """Failed convert a path"""

    def __init__(self, msg, name: str | None = None):
        self.name = name
        super().__init__(msg + f" ({name})" * (name is not None))


class WebtoonPathInitializationError(WebtoonPathError):
    """Failed to initialize path properly."""
