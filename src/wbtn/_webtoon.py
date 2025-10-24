from __future__ import annotations

import copy
import os
import sqlite3
import typing
from contextlib import contextmanager, suppress

from ._base import (
    ValueType,
)
from ._managers import *
from .conversion import dump_bytes_value, get_primitive_conversion, load_bytes_value, load_value, get_conversion_query_value

if typing.TYPE_CHECKING:
    from _typeshed import StrOrBytesPath as Pathlike

__all__ = (
    "Webtoon",
    "WebtoonMedia",
)

T = typing.TypeVar("T")


class Webtoon:
    __slots__ = (
        "connection",
        "info",
        "episode",
        "media",
        "extra_file",
        "path",
    )

    def __init__(
        self,
        path: Pathlike,
        connection_settings: ConnectionSettings | None = None,
    ) -> None:
        self.connection = WebtoonConnectionManager(
            path=path,
            settings=connection_settings,
        )
        self.info = WebtoonInfoManager(self)
        self.episode = WebtoonEpisodeManager(self)
        self.media = WebtoonMediaManger(self)
        self.extra_file = WebtoonExtraFileManager(self)

        self.path = WebtoonPathManager(self)

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self.connection.__exit__(exc_type, exc_value, traceback)

    def connect(self):
        self.connection.__enter__()
        return self

    def _merge(
        self,
        path: Pathlike,
        info_merger: typing.Callable[[str, ValueType, ValueType], ValueType] | None = None,
        # episodes_extra_merger: typing.Callable[[PrimitiveType, ValueType, ValueType], ValueType] | None = None,
        # media_merger: typing.Callable[[PrimitiveType, ValueType, ValueType], ValueType] | None = None,
    ):
        raise NotImplementedError()

        with self.connection.cursor() as cur, self.connection.cursor() as updater:
            cur.execute("ATTACH DATABASE ? AS dest", os.fspath(path))
            for name, main_conversion, main_value, dest_conversion, dest_value in cur.execute("""
                SELECT mi.name, mi.conversion, mi.value, di.conversion, di.value
                FROM main.info as mi, dest.info as di
                ON mi.name == di.name
            """):
                main = load_value(main_conversion, main_value)
                dest = load_value(dest_conversion, dest_value)
                # dest가 원래 값이고 main이 새로운 값임
                value = main if info_merger is None else info_merger(name, dest, main)
                conversion, query, value = get_conversion_query_value(value)
                updater.execute(f"UPDATE dest.info SET conversion = ?, value = {query} WHERE name = ?", (conversion, value, name))

            # 웹툰 이동 시 이렇게 통째로 옮기면 path가 제대로 적용되지 않는 오류가 발생할 수 있음!!!
            # 반드시 path 변환 후 움직여야 함!!!!
            # 문제는 id와 episode_no 중 한 쪽에만 conflict가 일어났을 때인데...
            # 그럴 때는 값이 그냥 사라져 버림
            # 어쩔 수가 없는 게 다른 foreign key같은 것들이 연결이 되어 있을 수 있어서 바꾸기가 어려움 upsert 구문으로 할 수 있는 한계가 있기도 하고
            updater.execute("""
                INSERT OR REPLACE INTO dest.episodes (episode_no, name, state, id, added_at)
                SELECT episode_no, name, state, id, added_at FROM main.episodes
            """)

            updater.execute("""
                INSERT OR REPLACE INTO dest.episodes_extra (episode_no, purpose, conversion, value)
                SELECT episode_no, purpose, conversion, value FROM main.episodes_extra
            """)

            updater.execute("""
                INSERT OR REPLACE INTO dest.media (episode_no, media_no, purpose, state, media_type, name, conversion, path, data, added_at)
                SELECT episode_no, media_no, purpose, state, media_type, name, conversion, path, data, added_at FROM main.media
            """)

    def migrate(
        self,
        new_path: Pathlike,
        *,
        replace: bool = False,
        merge_if_exists: bool = False,
        merger: typing.Callable[[ValueType, ValueType], ValueType] | None = None,
        # 파일을 지울 거면 그냥 os.rename쓰면 되지 뭐하러 migrate를 써?
        # 아 물론 다른 Connection이 있거나 journal 파일 누락으로 인한 손상을 막고 싶다면 유용할 수 있음.
        # delete_old_file: bool = False,
    ) -> typing.Self:
        raise NotImplementedError

        # OperationalError: output file already exists가 발생할 수 있음.
        try:
            self.execute("VACUUM INTO ?", (os.fspath(new_path),))
        except sqlite3.OperationalError as exc:
            if "already exists" not in exc.args[0]:
                raise
            if merge_if_exists:
                self._merge(new_path, lambda _, dest, main: main if merger is None else merger(dest, main))
            else:
                raise

        self.connection.__exit__(None, None, None)
        original_settings = copy.deepcopy(self.connection.settings)
        if replace:
            connection = WebtoonConnectionManager(
                new_path,
                journal_mode=self.connection.journal_mode,  # type: ignore
                connection_mode="c",  # type: ignore  # connection mode는 강제로 설정. 이전 설정이 n이거나 한다면 데이터가 제거될 수 있음.
            )
            self.connection = connection
            webtoon = self
        else:
            webtoon = type(self)(
                new_path,
                journal_mode=self.connection.journal_mode,  # type: ignore
                connection_mode="c",  # type: ignore
            )

        webtoon.connection.settings.bypass_integrity_check = True
        webtoon.connection.settings._configure_pragma_only = True
        webtoon.connect()
        webtoon.connection.settings = original_settings
        # webtoon.connection.connection_mode =
        return webtoon

    def close(self):
        return self.connection.__exit__(None, None, None)

    @contextmanager
    def execute_with(self, query: typing.LiteralString, params: sqlite3._Parameters = ()) -> typing.Iterator[sqlite3.Cursor]:
        with self.connection.cursor() as cur:
            yield cur.execute(query, params)

    def execute(self, query: typing.LiteralString, params: sqlite3._Parameters = ()) -> typing.Any:
        with self.connection.cursor() as cur:
            return cur.execute(query, params).fetchone()
