from __future__ import annotations

from dataclasses import dataclass
import datetime
import sqlite3
import typing

from .._base import (
    PrimitiveType,
    ValueType,
    fromtimestamp,
    timestamp,
)
from .._json_data import JsonData
from .._base import WebtoonType

__all__ = ("WebtoonEpisodeManager", "WebtoonEpisode")


class WebtoonEpisodeManager:
    __slots__ = "webtoon",

    def __init__(self, webtoon: WebtoonType) -> None:
        self.webtoon = webtoon

    def add(self, episode_no: int | None = None) -> WebtoonEpisode:
        """episode_no가 None일 경우 자동으로 가장 마지막으로 추가된 에피소드의 다음 에피소드로 저장됩니다."""
        real_episode_no, = self.webtoon.execute(
            """INSERT INTO Episode (episode_no, added_at) VALUES (?, ?) RETURNING episode_no""",
            (episode_no, timestamp())
        )
        return WebtoonEpisode.from_episode_no(real_episode_no, self.webtoon)

    # TODO: episode를 더하는 것뿐 아니라 제거, 수정할 수 있도록 하기


@dataclass(slots=True)
class WebtoonEpisode(typing.MutableMapping[str, ValueType]):
    episode_no: int
    added_at: datetime.datetime
    _webtoon: WebtoonType | None = None

    @classmethod
    def from_episode_no(cls, episode_no: int, webtoon: WebtoonType) -> typing.Self:
        result = webtoon.execute("SELECT added_at FROM Episode WHERE episode_no == ?", (episode_no,))
        if result is None:
            raise ValueError(f"An episode #{episode_no} does not exist.")
        added_at, = result
        return cls(
            episode_no,
            fromtimestamp(added_at),
            webtoon,
        )

    def __getitem__(self, kind: str) -> ValueType:
        result = self.webtoon.execute("SELECT conversion, value FROM EpisodeInfo WHERE episode_no == ? AND kind == ?", (self.episode_no, kind))
        if result is None:
            raise KeyError(kind)
        conversion, value = result
        return self.webtoon.value.load(conversion, value)

    def __setitem__(self, kind: str, value: ValueType) -> None:
        conversion, query, value = self.webtoon.value.dump_conversion_query_value(value, primitive_conversion=False)
        try:
            self.webtoon.execute(
                f"""INSERT OR REPLACE INTO EpisodeInfo (episode_no, kind, conversion, value) VALUES (?, ?, ?, {query})""",
                (self.episode_no, kind, conversion, value)
            )
        except sqlite3.OperationalError:
            raise KeyError(kind)

    def __delitem__(self, kind: str) -> None:
        result = self.webtoon.execute("DELETE FROM EpisodeInfo WHERE episode_no = ? AND kind = ? RETURNING TRUE", (self.episode_no, kind))
        if result is None:
            raise KeyError(kind)

    def __iter__(self) -> typing.Iterator[str]:
        with self.webtoon.execute_with("SELECT kind FROM EpisodeInfo WHERE episode_no == ?", (self.episode_no,)) as cur:
            for kind, in cur:
                yield kind

    def __len__(self) -> int:
        count, = self.webtoon.execute("SELECT count() FROM EpisodeInfo WHERE episode_no == ?", (self.episode_no,))
        return count

    @property
    def webtoon(self) -> WebtoonType:
        webtoon = self._webtoon
        if webtoon is None:
            raise ValueError("Webtoon is not included.")
        return webtoon
