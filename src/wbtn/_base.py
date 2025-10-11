from __future__ import annotations

import datetime
import typing
import warnings
from sqlite3 import sqlite_version as SQLITE_VERSION

__all__ = (
    "ConnectionMode",
    "ConversionType",
    "EpisodeState",
    "JOURNAL_MODES",
    "JournalModes",
    "JsonType",
    "PrimitiveType",
    "RestrictedPrimitiveType",
    "SCHEMA_VERSION",
    "SCHEMA_VERSIONS",
    "SQLITE_VERSION",
    "SUPPORT_JSON",
    "SUPPORT_JSONB",
    "VERSION",
    "WebtoonError",
    "WebtoonOpenError",
    "WebtoonSchemaError",
)

VERSION = "0.0.0a2"
SCHEMA_VERSION = 1000
SCHEMA_VERSIONS = {
    "0.0.0a2": 1000,
}
SUPPORT_JSON = [3, 38, 0] <= [int(version) for version in SQLITE_VERSION.split(".")]
SUPPORT_JSONB = [3, 45, 0] <= [int(version) for version in SQLITE_VERSION.split(".")]

if not SUPPORT_JSON:
    warnings.warn(
        "Sqlite seems not support json functions. The package may not work properly and could result in errors."
    )

JournalModes = typing.Literal["delete", "truncate", "persist", "memory", "wal", "off"]
ConnectionMode = typing.Literal["r", "w", "c", "n"]
JsonType = typing.Any
RestrictedPrimitiveType = str | int | bool | float
PrimitiveType = RestrictedPrimitiveType | bytes | None
# EpisodeState = typing.Literal["exists", "downloading", "empty", "impaired"]
EpisodeState = str
ConversionType = typing.Literal["json", "jsonb"] | None

JOURNAL_MODES = ("delete", "truncate", "persist", "memory", "wal", "off")
# EPISODE_STATE = (None, "exists", "empty", "impaired", "downloading")


def timestamp() -> float:
    return datetime.datetime.now().timestamp()


def fromtimestamp(timestamp: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(timestamp)


class WebtoonError(Exception):
    """Base exception for every wbtn errors"""


class WebtoonOpenError(WebtoonError):
    """Exceptions being occurred during opening a webtoon file"""


class WebtoonSchemaError(WebtoonError):
    """Exceptions regarding webtoon schema"""
