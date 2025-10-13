from __future__ import annotations

from dataclasses import dataclass
import datetime
import sqlite3
import typing
from contextlib import contextmanager
from pathlib import Path

from fieldenum import Variant, fieldenum

from ._base import (
    ConnectionMode,
    ConversionType,
    EpisodeState,
    JournalModes,
    PrimitiveType,
    fromtimestamp,
    timestamp,
)
from ._webtoon_connection import WebtoonConnectionManager
from ._json_data import JsonData
from .conversion import load_value, get_conversion_query_value

if typing.TYPE_CHECKING:
    from _typeshed import StrOrBytesPath as Pathlike

__all__ = (
    "Webtoon",
    "WebtoonMedia",
)

_NOTSET = object()
GET_VALUE: typing.LiteralString = "CASE conversion WHEN 'jsonb' THEN json(value) WHEN 'json' THEN json(value) ELSE value END"
T = typing.TypeVar("T")
ValueType = PrimitiveType | JsonData


class WebtoonInfoManager(typing.MutableMapping[str, ValueType]):
    __slots__ = "webtoon"

    def __init__(self, webtoon: Webtoon) -> None:
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
        value = load_value(conversion, value)
        return value

    def items(self) -> typing.Iterator[tuple[str, ValueType]]:
        with self.webtoon.connection.cursor() as cur:
            for name, conversion, value in cur.execute(f"SELECT name, conversion, {GET_VALUE} FROM info"):
                value = load_value(conversion, value)
                yield name, value

    def values(self) -> typing.Iterator[ValueType]:
        with self.webtoon.connection.cursor() as cur:
            for conversion, value in cur.execute(f"SELECT conversion, {GET_VALUE} FROM info"):
                value = load_value(conversion, value)
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
        value = load_value(conversion, value)
        return value

    def set(self, name: str, value: ValueType) -> None:
        conversion, query, value = get_conversion_query_value(value)
        with self.webtoon.connection.cursor() as cur:
            cur.execute(f"INSERT OR REPLACE INTO info VALUES (?, ?, {query})", (name, conversion, value))

    def setdefault(self, name: str, value: ValueType) -> None:
        conversion, query, value = get_conversion_query_value(value)
        with self.webtoon.connection.cursor() as cur:
            try:
                cur.execute(f"INSERT INTO info VALUES (?, ?, {query})", (name, conversion, value))
            except sqlite3.IntegrityError:  # 이미 값이 있을 경우
                pass

    def get_conversion(self, name: str) -> ConversionType:
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


class WebtoonEpisodeManager:
    __slots__ = "webtoon",

    def __init__(self, webtoon: Webtoon):
        self.webtoon = webtoon

    # TODO: state 어떻게 할 것인지 결정하기!!
    def add(self, id: PrimitiveType, name: str, *, episode_no: int | None = None, state: EpisodeState | None = None) -> int:
        with self.webtoon.connection.cursor() as cur:
            real_episode_no, = cur.execute(
                """INSERT INTO episodes (episode_no, state, name, id, added_at) VALUES (?, ?, ?, ?, ?) RETURNING episode_no""",
                (episode_no, state, name, id, timestamp())
            ).fetchone()
        return real_episode_no

    def add_extra_data(self, episode_no: int, purpose: str, value: PrimitiveType | JsonData):
        conversion, query, value = get_conversion_query_value(value)
        with self.webtoon.connection.cursor() as cur:
            cur.execute(
                f"""INSERT INTO episodes_extra (episode_no, purpose, conversion, value) VALUES (?1, ?2, ?3, {query.replace("?", "?4")})""",
                (episode_no, purpose, conversion, value)
            )


class WebtoonMediaManger:
    __slots__ = "webtoon",

    def __init__(self, webtoon: Webtoon):
        self.webtoon = webtoon

    @typing.overload
    def add(
        self,
        path: Path,
        /,
        episode_no: int,
        media_no: int,
        purpose: str,
        conversion: ConversionType = None,
        *,
        state=None,
        media_type: str | None = None,
        media_name: str | None = None,
        lazy_load: bool = True,
    ) -> WebtoonMedia: ...
    @typing.overload
    def add(
        self,
        data: PrimitiveType | JsonData,
        /,
        episode_no: int,
        media_no: int,
        purpose: str,
        *,
        state=None,
        media_type: str | None = None,
        media_name: str | None = None,
        lazy_load: bool = True,
    ) -> WebtoonMedia: ...
    def add(
        self,
        path_or_data: Path | PrimitiveType | JsonData,
        /,
        episode_no: int,
        # number는 '한 컷'을 의미하고, image 외에 comment, styles, meta 등 다양한 정보를 포함시킬 수 있다.
        media_no: int,
        # image, text 등 실제 구성 요소와 thumbnail, comment, styles, meta 등 실제 구성 요소는 아닌 데이터가 혼합되어 있을 수 있다.
        purpose: str,
        conversion: ConversionType | None = None,
        *,
        state=None,
        media_type: str | None = None,
        media_name: str | None = None,
        lazy_load: bool = True,
    ) -> WebtoonMedia:
        with self.webtoon.connection.cursor() as cur:
            if isinstance(path_or_data, Path):
                path = str(path_or_data)
                data = None
                if path_or_data.is_absolute():
                    if not self.webtoon.info.get("sys_allow_absolute_path"):
                        raise ValueError("The file does not accept absolute path for the path value.")
                else:
                    if not self.webtoon.info.get("sys_allow_relative_path"):
                        raise ValueError("The file does not accept relative path for the path value.")
            else:
                path = None
                data = path_or_data
                if conversion:
                    raise ValueError("conversion cannot be provided directly through conversion parameter.")

            # 다행히도 json() 함수와 jsonb() 함수 모두 NULL을 받았을 때 NULL을 리턴해서
            # path가 주어진 상황에서도 문제 없이 처리 가능함.
            if conversion:
                conversion, query, data = get_conversion_query_value(data, conversion)
            else:
                conversion, query, data = get_conversion_query_value(data)

            current_time = timestamp()
            media_id, = cur.execute(
                f"""INSERT INTO media (
                    episode_no,
                    media_no,
                    purpose,
                    state,
                    media_type,
                    name,
                    conversion,
                    path,
                    data,
                    added_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, {query}, ?) RETURNING id""",
                (episode_no, media_no, purpose, state, media_type, media_name, conversion, path, data, current_time)
            ).fetchone()
            return WebtoonMedia.media_from_id(media_id, self.webtoon, is_lazy=lazy_load)

    def get_matched_media(
        self,
        episode_no: int | None,
        purpose: str | None = None,
        state: str | None = None,
        *,
        lazy_load: bool = False,
    ) -> typing.Iterator[WebtoonMediaManger]:
        with self.webtoon.connection.cursor() as cur:
            for media_id, in cur.execute(
                """
                SELECT id
                FROM media
                WHERE (?1 IS NULL OR episode_no == ?1) AND (?2 IS NULL OR purpose == ?2) AND (?3 IS NULL OR state == ?3)
                """,
                (episode_no, purpose, state)
            ):
                yield WebtoonMedia.media_from_id(media_id, self.webtoon, is_lazy=lazy_load)


class Webtoon:
    __slots__ = "connection", "info", "episode", "media"

    def __init__(
        self,
        path: Pathlike,
        *,
        journal_mode: JournalModes | None = None,
        connection_mode: ConnectionMode = "c",
    ) -> None:
        self.connection = WebtoonConnectionManager(
            path=path,
            journal_mode=journal_mode,
            connection_mode=connection_mode,
        )
        self.info = WebtoonInfoManager(self)
        self.episode = WebtoonEpisodeManager(self)
        self.media = WebtoonMediaManger(self)

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self.connection.__exit__(exc_type, exc_value, traceback)

    def connect(self):
        self.connection.__enter__()
        return self

    def migrate(
        self,
        new_path: str,
        *,
        replace: bool = False,
        # 파일을 지울 거면 그냥 os.rename쓰면 되지 뭐하러 migrate를 써?
        # 아 물론 다른 Connection이 있거나 journal 파일 누락으로 인한 손상을 막고 싶다면 유용할 수 있음.
        # delete_old_file: bool = False,
    ) -> typing.Self:
        # OperationalError: output file already exists가 발생할 수 있음.
        self.execute("VACUUM INTO ?", (str(new_path),))
        self.connection.__exit__(None, None, None)
        original_bypass = self.connection.bypass_integrity_check
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

        webtoon.connection.bypass_integrity_check = True
        webtoon.connection._configure_pragma_only = True
        webtoon.connect()
        webtoon.connection.bypass_integrity_check = original_bypass
        del webtoon.connection._configure_pragma_only
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


class MediaLazyLoader(typing.Generic[T]):
    def __init__(
        self,
        name: str,
        *,
        loader: typing.Callable[..., T] | None = None,
        serializer: typing.Callable[[T], PrimitiveType] | None = None,
    ) -> None:
        self.name = name
        self.loader = loader
        self.serializer = serializer

    def __get__(self, media, obj_type=None) -> T:
        try:
            # 이유는 잘 모르겠지만 getattr는 작동을 안 함
            webtoon = media._webtoon
        except Exception:
            raise ValueError("Realtime fetching is not possible")
        name = self.name
        if not name.isidentifier() or name.startswith("sqlite_"):
            raise ValueError(f"Invalid column name: {name!r}")
        with webtoon.connection.cursor() as cur:
            result = cur.execute(f"SELECT {name} from media where id == ?", (media.media_id,)).fetchone()
        if result is None:
            raise ValueError(f"Can't find media that have media_id == {media.media_id}.")
        data = result[0]
        if self.loader:
            data = self.loader(data)
        if media._cache_results:
            setattr(media, name, data)
        return data


@dataclass(slots=True)
class WebtoonEpisode:
    episode_no: int
    name: str
    state: PrimitiveType
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


@fieldenum
class WebtoonMedia:
    # fieldenum은 기본적으로 __dict__를 지원해주지 않기 때문에 MediaWithId에서 캐싱을 적용하려고 할 때는 직접 선언해야 함
    __slots__ = ("__dict__", "__weakref__")

    media_id: int
    # non-data descriptor여서 인스턴스에 값이 있을 경우 해당 값이 불러짐
    episode_no = MediaLazyLoader[int]("episode_no")
    media_no = MediaLazyLoader[int]("media_no")
    purpose = MediaLazyLoader[str | None]("purpose")
    state = MediaLazyLoader[typing.Any]("state")
    media_type = MediaLazyLoader[str]("media_type")
    name = MediaLazyLoader[str]("name")
    conversion = MediaLazyLoader[ConversionType]("conversion")
    path = MediaLazyLoader[str | None]("path")
    data = MediaLazyLoader[str | None]("data")
    added_at = MediaLazyLoader[datetime.datetime]("added_at", loader=fromtimestamp)

    MediaWithId = Variant(
        media_id=int,
        _webtoon=Webtoon,
        _cache_results=bool,
    ).default(_cache_results=False)
    Media = Variant(
        media_id=int,
        episode_no=int,
        media_no=int,
        purpose=str | None,
        state=typing.Any,
        name=str,
        media_type=str | None,
        conversion=ConversionType,
        path=str | None,
        data=str | None,
        added_at=datetime.datetime,
    ).default(state=None, media_type=None, conversion=None, name=None)
    MediaWithoutId = Variant(
        episode_no=int,
        media_no=int,
        purpose=str | None,
        state=typing.Any,
        name=str,
        media_type=str | None,
        conversion=ConversionType,
        path=str | None,
        data=str | None,
    ).default(state=None, media_type=None, conversion=None, name=None)

    # def apply(self, webtoon: Webtoon):
    #     """데이터가 수정되었을 경우 수정된 값을 반영합니다."""

    def replace_config(
        self,
        *,
        media_id: int | None = None,
        webtoon: Webtoon | None = None,
        cache_results: bool | None = None,
    ):
        if not isinstance(self, WebtoonMedia.MediaWithId):  # type: ignore
            raise ValueError("Only WebtoonMedia.MediaWithId can use this function.")
        return WebtoonMedia.MediaWithId(
            self.media_id if media_id is None else media_id,
            self._webtoon if webtoon is None else webtoon,  # type: ignore
            self._cache_results if cache_results is None else cache_results,  # type: ignore
        )

    @classmethod
    def media_from_id(cls, media_id: int, webtoon: Webtoon, *, is_lazy: bool = False):
        if is_lazy:
            return WebtoonMedia.MediaWithId(media_id, webtoon)

        # 아마도 한 cursor 안에서는 하나의 statement가 실행되는 동안 다른 statement가 실행되면 끊기는 것 같음.
        # 따라서 iterator가 작동하고 있는 동안에는 _cursor를 사용해서는 안 됨
        # 커서 만들고 삭제하는 데에 100ns면 되니깐 그냥 만들어서 쓰자...
        with webtoon.connection.cursor() as cur:
            result = cur.execute(
                """
                SELECT id, episode_no, media_no, purpose, state, media_type, name, conversion, path, data, added_at
                FROM media
                WHERE id == ?
                """,
                (media_id,)
            ).fetchone()
            if result is None:
                raise ValueError(f"Can't find media that have media_id == {media_id}.")
            media_id, episode_no, media_no, purpose, state, media_type, name, conversion, path, data, added_at = result
            return WebtoonMedia.Media(
                media_id=media_id,
                episode_no=episode_no,
                media_no=media_no,
                purpose=purpose,
                state=state,
                media_type=media_type,
                name=name,
                conversion=conversion,
                path=path and Path(path),
                data=data,
                added_at=fromtimestamp(added_at),
            )
