from __future__ import annotations

from dataclasses import dataclass
import datetime
import sqlite3
import typing

from .._base import (
    EpisodeState,
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

    def add(self, id: PrimitiveType, name: str, *, episode_no: int | None = None, state: EpisodeState | None = None) -> WebtoonEpisode:
        real_episode_no, = self.webtoon.execute(
            """INSERT INTO episodes (episode_no, state, name, id, added_at) VALUES (?, ?, ?, ?, ?) RETURNING episode_no""",
            (episode_no, state, name, id, timestamp())
        )
        return WebtoonEpisode.from_episode_no(real_episode_no, self.webtoon)


@dataclass(slots=True)
class WebtoonEpisode(typing.MutableMapping[str, ValueType]):
    episode_no: int
    name: str
    state: EpisodeState
    episode_id: PrimitiveType
    added_at: datetime.datetime
    _webtoon: WebtoonType | None = None

    @classmethod
    def from_episode_no(cls, episode_no: int, webtoon: WebtoonType) -> typing.Self:
        result = webtoon.execute("SELECT name, state, id, added_at FROM episodes WHERE episode_no == ?", (episode_no,))
        if result is None:
            raise ValueError(f"An episode having {episode_no = } does not exist.")
        name, state, episode_id, added_at = result
        return cls(
            episode_no,
            name,
            state,
            episode_id,
            fromtimestamp(added_at),
            webtoon,
        )

    def __getitem__(self, purpose: str) -> ValueType:
        if purpose is None:
            # 옛날 코드의 잔재라 없애려면 없애도 될 듯
            with self.webtoon.execute_with("SELECT purpose, conversion, value FROM episodes_extra WHERE episode_no == ?", (self.episode_no,)) as cur:
                return {
                    purpose: self.webtoon.value.load(conversion, value)
                    for purpose, conversion, value
                    in cur
                }
        else:
            result = self.webtoon.execute("SELECT conversion, value FROM episodes_extra WHERE episode_no == ? AND purpose == ?", (self.episode_no, purpose))
            if result is None:
                raise KeyError(purpose)
            conversion, value = result
            return self.webtoon.value.load(conversion, value)

    def __setitem__(self, purpose: str, value: ValueType) -> None:
        conversion, query, value = self.webtoon.value.dump_conversion_query_value(value, primitive_conversion=False)
        try:
            self.webtoon.execute(
                f"""INSERT OR REPLACE INTO episodes_extra (episode_no, purpose, conversion, value) VALUES (?1, ?2, ?3, {query.replace("?", "?4")})""",
                (self.episode_no, purpose, conversion, value)
            )
        except sqlite3.OperationalError:
            raise KeyError(purpose)

    def __delitem__(self, purpose: str) -> None:
        result = self.webtoon.execute("DELETE FROM episodes_extra WHERE episode_no = ? AND purpose = ? RETURNING TRUE", (self.episode_no, purpose))
        if result is None:
            raise KeyError(purpose)

    def __iter__(self) -> typing.Iterator[str]:
        with self.webtoon.execute_with("SELECT purpose FROM episodes_extra WHERE episode_no == ?", (self.episode_no,)) as cur:
            for purpose, in cur:
                yield purpose

    def __len__(self) -> int:
        count, = self.webtoon.execute("SELECT count() FROM episodes_extra WHERE episode_no == ?", (self.episode_no,))
        return count

    @property
    def webtoon(self) -> WebtoonType:
        webtoon = self._webtoon
        if webtoon is None:
            raise ValueError("Webtoon is not included.")
        return webtoon
