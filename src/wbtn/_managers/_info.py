from __future__ import annotations

import sqlite3
import typing

from .._base import ValueType, ConversionType, GET_VALUE
from .._base import WebtoonType

_NOTSET = object()

__all__ = ("WebtoonInfoManager",)


class WebtoonInfoManager(typing.MutableMapping[str, ValueType]):
    __slots__ = "webtoon",

    def __init__(self, webtoon: WebtoonType) -> None:
        self.webtoon = webtoon

    def __iter__(self) -> typing.Iterator[str]:
        with self.webtoon.execute_with("SELECT name FROM Info") as cur:
            for result, in cur:
                yield result

    def __len__(self) -> int:
        count, = self.webtoon.execute("SELECT count() FROM Info")
        return count

    def __getitem__(self, key: str) -> ValueType:
        return self.get(key, _NOTSET)

    def __setitem__(self, key: str, value: ValueType) -> None:
        return self.set(key, value)

    def __delitem__(self, key: str) -> None:
        return self.delete(key)

    def pop(self, key: str, default=_NOTSET, system: bool = False) -> typing.Any:
        if not system:
            self._protect_system_key(key)
        result = self.webtoon.execute(f"DELETE FROM Info WHERE name == ? RETURNING conversion, {GET_VALUE}", (key,))
        if result is None:
            if default is _NOTSET:
                raise KeyError(key)
            else:
                return default
        conversion, value = result
        value = self.webtoon.value.load(conversion, value)
        return value

    def items(self) -> typing.Iterator[tuple[str, ValueType]]:
        with self.webtoon.execute_with(f"SELECT name, conversion, {GET_VALUE} FROM Info") as cur:
            for name, conversion, value in cur:
                value = self.webtoon.value.load(conversion, value)
                yield name, value

    def values(self) -> typing.Iterator[ValueType]:
        with self.webtoon.execute_with(f"SELECT conversion, {GET_VALUE} FROM Info") as cur:
            for conversion, value in cur:
                value = self.webtoon.value.load(conversion, value)
                yield value

    def clear(self, system: bool = False) -> None:
        if system:
            self.webtoon.execute("DELETE FROM Info")
        else:
            self.webtoon.execute("DELETE FROM Info WHERE name NOT LIKE 'sys\\_%' ESCAPE '\\'")

    def delete(self, key: str, system: bool = False):
        if not system:
            self._protect_system_key(key)
        result = self.webtoon.execute("DELETE FROM Info WHERE name == ? RETURNING 1", (key,))
        if result is None:
            raise KeyError(key)

    def get(self, name: str, default=None) -> ValueType:
        result = self.webtoon.execute(f"SELECT conversion, {GET_VALUE} FROM Info WHERE name == ?", (name,))
        if result is None:
            if default is _NOTSET:
                raise KeyError(name)
            else:
                return default
        conversion, value = result
        value = self.webtoon.value.load(conversion, value)
        return value

    def set(self, name: str, value: ValueType, system: bool = False) -> None:
        if not system:
            self._protect_system_key(name)
        conversion, query, value = self.webtoon.value.dump_conversion_query_value(value, primitive_conversion=False)
        self.webtoon.execute(f"INSERT OR REPLACE INTO Info VALUES (?, ?, {query})", (name, conversion, value))

    def setdefault(self, name: str, value: ValueType) -> None:
        conversion, query, value = self.webtoon.value.dump_conversion_query_value(value, primitive_conversion=False)
        try:
            self.webtoon.execute(f"INSERT INTO Info VALUES (?, ?, {query})", (name, conversion, value))
        except sqlite3.IntegrityError:  # 이미 값이 있을 경우
            pass

    def get_conversion(self, name: str) -> ConversionType | None:
        result = self.webtoon.execute("SELECT conversion FROM Info WHERE name == ?", (name,))
        if result is None:
            raise KeyError(name)
        conversion, = result
        return conversion

    @staticmethod
    def _protect_system_key(key: str):
        if key.startswith("sys_"):
            raise KeyError(f"Cannot modify or delete system information {key!r}. Set system=True to modify the key.")
