from __future__ import annotations

from dataclasses import dataclass
import datetime
import typing
from pathlib import Path

from .._base import (
    GET_VALUE,
    ConversionType,
    ValueType,
    fromtimestamp,
    timestamp,
)
from .._base import WebtoonType

_NOTSET = object()

__all__ = ("WebtoonExtraFileManager", "ExtraFile")


class WebtoonExtraFileManager:
    __slots__ = "webtoon",

    def __init__(self, webtoon: WebtoonType) -> None:
        self.webtoon = webtoon

    def __iter__(self) -> typing.Iterator[ExtraFile]:
        return self.iterate()

    def __len__(self) -> int:
        length, = self.webtoon.execute("SELECT count() FROM ExtraFile")
        return length

    def add_path(self, path: Path, conversion: ConversionType | None, purpose: str | None = None) -> ExtraFile:
        return self._add(path, purpose, conversion=conversion)

    def add_value(self, path: Path, value: ValueType, purpose: str | None = None) -> ExtraFile:
        return self._add(path, purpose, value=value)

    def dump(self, extra_file: ExtraFile, *, mkdir: bool = True, exist_ok: bool = False):
        # extra_file의 데이터를 path에 dump함
        raise NotImplementedError()

    def _add(
        self,
        path: Path,
        purpose: str | None = None,
        *,
        conversion: ConversionType | None = None,
        value: ValueType = _NOTSET,  # type: ignore
    ) -> ExtraFile:
        if value is _NOTSET:
            query, value = "?", None
        else:
            conversion, query, value = self.webtoon.value.dump_conversion_query_value(value, primitive_conversion=True)

        file_id, = self.webtoon.execute(
            f"INSERT INTO ExtraFile (kind, value, conversion, path, added_at) VALUES (?, {query}, ?, ?, ?) RETURNING file_id",
            (purpose, value, conversion, self.webtoon.path.dump(path), time := timestamp()),
        )
        return ExtraFile.from_id(file_id, self.webtoon)

    def set(self, extra_file: ExtraFile) -> None:
        result = self.webtoon.execute(
            "UPDATE ExtraFile SET kind = ?, value = ?, conversion = ?, path = ?, added_at = ? WHERE file_id = ? RETURNING 1",
            (extra_file.kind, extra_file.value, extra_file.conversion, self.webtoon.path.dump(extra_file.path), extra_file.added_at.timestamp(), extra_file.file_id)
        )
        if result is None:
            raise KeyError(extra_file)

    def iterate(self, kind: str | None = _NOTSET) -> typing.Iterator[ExtraFile]:  # type: ignore
        if kind is _NOTSET:
            query = f"SELECT file_id, kind, {GET_VALUE}, conversion, path, added_at FROM ExtraFile"
            params = ()
        elif kind is None:
            query = f"SELECT file_id, kind, {GET_VALUE}, conversion, path, added_at FROM ExtraFile WHERE kind IS NULL"
            params = ()
        else:
            query = f"SELECT file_id, kind, {GET_VALUE}, conversion, path, added_at FROM ExtraFile WHERE kind == ?"
            params = (kind,)
        with self.webtoon.execute_with(query, params) as cur:
            for file_id, kind, value, conversion, path, added_at in cur:
                value = self.webtoon.value.load(conversion, value)
                yield ExtraFile(file_id, kind, value, conversion, self.webtoon.path.load_str(path), fromtimestamp(added_at))

    def remove(self, file: ExtraFile) -> None:
        result = self.webtoon.execute("DELETE FROM ExtraFile WHERE file_id == ? RETURNING 1", (file.file_id,))
        if result is None:
            raise KeyError(file)


@dataclass(slots=True)
class ExtraFile:
    file_id: int
    kind: str | None
    value: ValueType
    conversion: ConversionType | None
    path: Path
    added_at: datetime.datetime

    # TODO: 이것도 데이터를 바로 불러오는 건 좀 부담될 것 같음
    @classmethod
    def from_id(cls, file_id: int, webtoon: WebtoonType) -> ExtraFile:
        result = webtoon.execute(f"SELECT file_id, kind, {GET_VALUE}, conversion, path, added_at FROM ExtraFile WHERE file_id == ?", (file_id,))
        if result is None:
            raise KeyError(file_id)
        file_id, kind, value, conversion, path, added_at = result
        value = webtoon.value.load(conversion, value)
        return ExtraFile(file_id, kind, value, conversion, webtoon.path.load_str(path), fromtimestamp(added_at))
