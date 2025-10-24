from __future__ import annotations

from dataclasses import dataclass
import datetime
import typing
from pathlib import Path

from .._base import (
    fromtimestamp,
    timestamp,
)
from .._base import WebtoonType

_NOTSET = object()

__all__ = ("WebtoonExtraFileManager", "ExtraFile")


class WebtoonExtraFileManager:
    __slots__ = "webtoon",

    def __init__(self, webtoon: WebtoonType):
        self.webtoon = webtoon

    def __iter__(self):
        return self.iterate()

    def __len__(self):
        length, = self.webtoon.execute("SELECT count() FROM extra_files")
        return length

    def add(self, path: Path, purpose: str | None = None, data: bytes | None = None):
        self.webtoon.execute(
            "INSERT INTO extra_files (purpose, path, data, added_at) VALUES (?, ?, ?, ?)",
            (purpose, self.webtoon.path.dump(path), data, timestamp()),
        )

    def get(self, id: int | ExtraFile) -> ExtraFile:
        result = self.webtoon.execute("SELECT * FROM extra_files WHERE id == ?", (id if isinstance(id, int) else id.id,))
        if result is None:
            raise KeyError(id)
        id_, purpose, path, data, added_at = result
        return ExtraFile(id_, purpose, self.webtoon.path.load_str(path), data, fromtimestamp(added_at))

    def set(self, extra_file: ExtraFile):
        result = self.webtoon.execute(
            "UPDATE extra_files SET purpose = ?, path = ?, data = ?, added_at = ? WHERE id = ? RETURNING 1",
            (extra_file.purpose, self.webtoon.path.dump(extra_file.path), extra_file.data, extra_file.added_at.timestamp(), extra_file.id)
        )
        if result is None:
            raise KeyError(extra_file)

    def iterate(self, purpose: str | None = _NOTSET) -> typing.Iterator[ExtraFile]:  # type: ignore
        if purpose is _NOTSET:
            query = "SELECT * FROM extra_files"
            params = ()
        else:
            query = "SELECT * FROM extra_files WHERE purpose == ?"
            params = (purpose,)
        with self.webtoon.execute_with(query, params) as cur:
            for id, purpose, path, data, added_at in cur:
                yield ExtraFile(id, purpose, self.webtoon.path.load_str(path), data, fromtimestamp(added_at))

    def remove(self, id: int | ExtraFile):
        result = self.webtoon.execute("DELETE FROM extra_files WHERE id == ? RETURNING 1", (id if isinstance(id, int) else id.id,))
        if result is None:
            raise KeyError(id)


@dataclass(slots=True)
class ExtraFile:
    id: int
    purpose: str | None
    path: Path
    data: bytes | None
    added_at: datetime.datetime
