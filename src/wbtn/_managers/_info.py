from __future__ import annotations

import sqlite3
import typing

from .._base import ValueType, ConversionType
from .._base import WebtoonType

_NOTSET = object()
GET_VALUE: typing.LiteralString = "CASE conversion WHEN 'jsonb' THEN json(value) WHEN 'json' THEN json(value) ELSE value END"

__all__ = ("WebtoonInfoManager",)


class WebtoonInfoManager(typing.MutableMapping[str, ValueType]):
    __slots__ = "webtoon",

    def __init__(self, webtoon: WebtoonType) -> None:
        self.webtoon = webtoon

    def __iter__(self) -> typing.Iterator[str]:
        with self.webtoon.connection.cursor() as cur:
            for result, in cur.execute("SELECT name FROM info"):
                yield result

    def __len__(self) -> int:
        with self.webtoon.connection.cursor() as cur:
            count, = cur.execute("SELECT count() FROM info").fetchone()
        return count

    def __getitem__(self, key: str) -> ValueType:
        return self.get(key, _NOTSET)

    def __setitem__(self, key: str, value: ValueType) -> None:
        return self.set(key, value)

    def __delitem__(self, key: str) -> None:
        return self.delete(key)

    def pop(self, key: str, default=_NOTSET, delete_system: bool = False) -> typing.Any:
        if not delete_system:
            self._protect_system_key(key)
        with self.webtoon.connection.cursor() as cur:
            result = cur.execute(f"DELETE FROM info WHERE name == ? RETURNING conversion, {GET_VALUE}", (key,)).fetchone()
        if result is None:
            if default is _NOTSET:
                raise KeyError(key)
            else:
                return default
        conversion, value = result
        value = self.webtoon.value.load(conversion, value)
        return value

    def items(self) -> typing.Iterator[tuple[str, ValueType]]:
        with self.webtoon.connection.cursor() as cur:
            for name, conversion, value in cur.execute(f"SELECT name, conversion, {GET_VALUE} FROM info"):
                value = self.webtoon.value.load(conversion, value)
                yield name, value

    def values(self) -> typing.Iterator[ValueType]:
        with self.webtoon.connection.cursor() as cur:
            for conversion, value in cur.execute(f"SELECT conversion, {GET_VALUE} FROM info"):
                value = self.webtoon.value.load(conversion, value)
                yield value

    def clear(self, delete_system: bool = False) -> None:
        with self.webtoon.connection.cursor() as cur:
            if delete_system:
                cur.execute("DELETE FROM info")
            else:
                cur.execute("DELETE FROM info WHERE name NOT LIKE 'sys\\_%' ESCAPE '\\'")

    def delete(self, key: str, delete_system: bool = False):
        if not delete_system:
            self._protect_system_key(key)
        with self.webtoon.connection.cursor() as cur:
            result = cur.execute("DELETE FROM info WHERE name == ? RETURNING 1", (key,)).fetchone()
            if result is None:
                raise KeyError(key)

    def get(self, name: str, default=None) -> ValueType:
        # with nullcontext(_cursor) if _cursor is not None else self.webtoon.connection.cursor() as cur:
        with self.webtoon.connection.cursor() as cur:
            result = cur.execute(f"SELECT conversion, {GET_VALUE} FROM info WHERE name == ?", (name,)).fetchone()
        if result is None:
            if default is _NOTSET:
                raise KeyError(name)
            else:
                return default
        conversion, value = result
        value = self.webtoon.value.load(conversion, value)
        return value

    def set(self, name: str, value: ValueType) -> None:
        conversion, query, value = self.webtoon.value.dump_conversion_query_value(value)
        with self.webtoon.connection.cursor() as cur:
            cur.execute(f"INSERT OR REPLACE INTO info VALUES (?, ?, {query})", (name, conversion, value))

    def setdefault(self, name: str, value: ValueType) -> None:
        conversion, query, value = self.webtoon.value.dump_conversion_query_value(value)
        with self.webtoon.connection.cursor() as cur:
            try:
                cur.execute(f"INSERT INTO info VALUES (?, ?, {query})", (name, conversion, value))
            except sqlite3.IntegrityError:  # 이미 값이 있을 경우
                pass

    def get_conversion(self, name: str) -> ConversionType | None:
        with self.webtoon.connection.cursor() as cur:
            result = cur.execute("SELECT conversion FROM info WHERE name == ?", (name,)).fetchone()
        if result is None:
            raise KeyError(name)
        conversion, = result
        return conversion

    @staticmethod
    def _protect_system_key(key: str):
        if key.startswith("sys_"):
            raise KeyError(f"Cannot delete info {key!r} since it's system key. Set delete_system=True to delete the key.")
