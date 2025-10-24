from __future__ import annotations

from dataclasses import dataclass
import datetime
import sqlite3

from .._base import (
    EpisodeState,
    PrimitiveType,
    ValueType,
    fromtimestamp,
    timestamp,
)
from .._json_data import JsonData
from ..conversion import load_value, get_conversion_query_value
from .._base import WebtoonType

__all__ = ("WebtoonEpisodeManager", "WebtoonEpisode")


class WebtoonEpisodeManager:
    __slots__ = "webtoon",

    def __init__(self, webtoon: WebtoonType):
        self.webtoon = webtoon

    def add(self, id: PrimitiveType, name: str, *, episode_no: int | None = None, state: EpisodeState | None = None) -> int:
        real_episode_no, = self.webtoon.execute(
            """INSERT INTO episodes (episode_no, state, name, id, added_at) VALUES (?, ?, ?, ?, ?) RETURNING episode_no""",
            (episode_no, state, name, id, timestamp())
        )
        return real_episode_no

    def add_extra_data(self, episode_no: int, purpose: str, value: PrimitiveType | JsonData, replace: bool = True):
        conversion, query, value = get_conversion_query_value(value)
        with self.webtoon.connection.cursor() as cur:
            try:
                cur.execute(
                    f"""INSERT {"OR REPLACE" * replace} INTO episodes_extra (episode_no, purpose, conversion, value) VALUES (?1, ?2, ?3, {query.replace("?", "?4")})""",
                    (episode_no, purpose, conversion, value)
                )
            except sqlite3.OperationalError:
                raise KeyError((episode_no, purpose))

    def delete_extra_data(self, episode_no: int, purpose: str):
        result = self.webtoon.execute("DELETE FROM episodes_extra WHERE episode_no = ? AND purpose = ? RETURNING TRUE", (episode_no, purpose))
        if result is None:
            raise KeyError((episode_no, purpose))

    def extra_data_purposes(self, episode_no: int) -> list[str]:
        with self.webtoon.connection.cursor() as cur:
            return cur.execute("""SELECT purpose FROM episodes_extra WHERE episode_no == ?""", (episode_no,)).fetchall()

    def extra_data(self, episode_no: int, purpose: str | None = None) -> ValueType | dict[str, ValueType] | list[ValueType]:
        with self.webtoon.connection.cursor() as cur:
            if purpose is None:
                return {
                    purpose: load_value(conversion, value)
                    for purpose, conversion, value
                    in cur.execute("SELECT purpose, conversion, value FROM episodes_extra WHERE episode_no == ?", (episode_no,))
                }
            else:
                conversion, value = cur.execute("SELECT conversion, value FROM episodes_extra WHERE episode_no == ? AND purpose == ?", (episode_no, purpose)).fetchone()
                return load_value(conversion, value)


@dataclass(slots=True)
class WebtoonEpisode:
    episode_no: int
    name: str
    state: EpisodeState
    episode_id: PrimitiveType
    added_at: datetime.datetime

    @classmethod
    def from_episode_no(cls, episode_no: int, cursor: sqlite3.Cursor):
        result = cursor.execute("SELECT name, state, id, added_at FROM episodes WHERE episode_no == ?", (episode_no,)).fetchone()
        if result is None:
            raise ValueError(f"An episode having {episode_no = } does not exist.")
        name, state, episode_id, added_at = result
        return cls(
            episode_no,
            name,
            state,
            episode_id,
            fromtimestamp(added_at),
        )
