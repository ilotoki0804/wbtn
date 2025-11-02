from __future__ import annotations

from dataclasses import dataclass
import datetime
import typing
from pathlib import Path

from .._base import (
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
        length, = self.webtoon.execute("SELECT count() FROM extra_files")
        return length

    def add_path(self, path: Path, conversion: ConversionType | None, purpose: str | None = None) -> ExtraFile:
        return self._add(path, purpose, conversion=conversion)

    def add_data(self, path: Path, data: ValueType, purpose: str | None = None) -> ExtraFile:
        return self._add(path, purpose, data=data)

    def _add(
        self,
        path: Path,
        purpose: str | None = None,
        *,
        conversion: ConversionType | None = None,
        data: ValueType = _NOTSET,  # type: ignore
    ) -> ExtraFile:
        if data is _NOTSET:
            query, value = "?", None
        else:
            conversion, query, value = self.webtoon.value.dump_conversion_query_value(data, primitive_conversion=True)

        file_id, = self.webtoon.execute(
            f"INSERT INTO extra_files (purpose, conversion, path, data, added_at) VALUES (?, ?, ?, {query}, ?) RETURNING id",
            (purpose, conversion, self.webtoon.path.dump(path), value, time := timestamp()),
        )
        return ExtraFile.from_id(file_id, self.webtoon)

    def set(self, extra_file: ExtraFile) -> None:
        result = self.webtoon.execute(
            "UPDATE extra_files SET purpose = ?, conversion = ?, path = ?, data = ?, added_at = ? WHERE id = ? RETURNING 1",
            (extra_file.purpose, extra_file.conversion, self.webtoon.path.dump(extra_file.path), extra_file.data, extra_file.added_at.timestamp(), extra_file.id)
        )
        if result is None:
            raise KeyError(extra_file)

    def iterate(self, purpose: str | None = _NOTSET) -> typing.Iterator[ExtraFile]:  # type: ignore
        if purpose is _NOTSET:
            query = "SELECT * FROM extra_files"
            params = ()
        elif purpose is None:
            query = "SELECT * FROM extra_files WHERE purpose IS NULL"
            params = ()
        else:
            query = "SELECT * FROM extra_files WHERE purpose == ?"
            params = (purpose,)
        with self.webtoon.execute_with(query, params) as cur:
            for id, purpose, conversion, path, data, added_at in cur:
                value = self.webtoon.value.load(conversion, data)
                yield ExtraFile(id, purpose, conversion, self.webtoon.path.load_str(path), value, fromtimestamp(added_at))

    def remove(self, file: ExtraFile) -> None:
        result = self.webtoon.execute("DELETE FROM extra_files WHERE id == ? RETURNING 1", (file.id,))
        if result is None:
            raise KeyError(file)


@dataclass(slots=True)
class ExtraFile:
    id: int
    purpose: str | None
    conversion: ConversionType | None
    path: Path
    data: ValueType
    added_at: datetime.datetime

    @classmethod
    def from_id(cls, file_id: int, webtoon: WebtoonType) -> ExtraFile:
        result = webtoon.execute("SELECT * FROM extra_files WHERE id == ?", (file_id if isinstance(file_id, int) else file_id.id,))
        if result is None:
            raise KeyError(file_id)
        id, purpose, conversion, path, data, added_at = result
        value = webtoon.value.load(conversion, data)
        return ExtraFile(id, purpose, conversion, webtoon.path.load_str(path), value, fromtimestamp(added_at))
