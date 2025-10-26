from __future__ import annotations

from dataclasses import dataclass
import datetime
import typing
from pathlib import Path

from .._base import (
    ConversionType,
    EpisodeState,
    PrimitiveType,
    ValueType,
    fromtimestamp,
    timestamp,
)
from ._episode import WebtoonEpisode
from .._json_data import JsonData
from .._base import WebtoonType

__all__ = ("WebtoonMediaManger", "WebtoonMediaData", "WebtoonMedia")


class WebtoonMediaManger:
    __slots__ = "webtoon",

    def __init__(self, webtoon: WebtoonType):
        self.webtoon = webtoon

    def add_path_or_data(
        self,
        path: Path,
        data: PrimitiveType | JsonData,
        episode: WebtoonEpisode,
        media_no: int,
        purpose: str,
        conversion: ConversionType = None,
        *,
        state: EpisodeState = None,
        media_type: str | None = None,
        media_name: str | None = None,
        mkdir: bool = True,
    ) -> WebtoonMedia:
        if self.webtoon.path.self_contained:
            return self.add(
                data,
                episode=episode,
                media_no=media_no,
                purpose=purpose,
                state=state,
                media_type=media_type,
                media_name=media_name,
            )
        else:
            if mkdir:
                path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.webtoon.value.dump_bytes(data))
            try:
                result = self.add(
                    path,
                    episode=episode,
                    media_no=media_no,
                    purpose=purpose,
                    conversion=conversion or self.webtoon.value.get_primitive_conversion(data),
                    state=state,
                    media_type=media_type,
                    media_name=media_name,
                )
            except BaseException:
                path.unlink()
                raise
            else:
                return result

    @typing.overload
    def add(  # NOTE: WebtoonMedia를 값으로 받도록 하는 것도 좋을 수 있을 것 같다
        self,
        path: Path,
        /,
        episode: WebtoonEpisode,
        media_no: int,
        purpose: str,
        conversion: ConversionType = None,
        *,
        state: EpisodeState = None,
        media_type: str | None = None,
        media_name: str | None = None,
    ) -> WebtoonMedia: ...
    @typing.overload
    def add(
        self,
        data: PrimitiveType | JsonData,
        /,
        episode: WebtoonEpisode,
        media_no: int,
        purpose: str,
        *,
        state: EpisodeState = None,
        media_type: str | None = None,
        media_name: str | None = None,
    ) -> WebtoonMedia: ...
    def add(
        self,
        path_or_data: Path | PrimitiveType | JsonData,
        /,
        episode: WebtoonEpisode,
        # number는 '한 컷'을 의미하고, image 외에 comment, styles, meta 등 다양한 정보를 포함시킬 수 있다.
        media_no: int,
        # image, text 등 실제 구성 요소와 thumbnail, comment, styles, meta 등 실제 구성 요소는 아닌 데이터가 혼합되어 있을 수 있다.
        purpose: str,
        conversion: ConversionType | None = None,
        *,
        state: EpisodeState = None,
        media_type: str | None = None,
        media_name: str | None = None,
    ) -> WebtoonMedia:
        with self.webtoon.connection.cursor() as cur:
            if isinstance(path_or_data, Path):
                path = self.webtoon.path.dump(path_or_data)
                data = None
            else:
                path = None
                data = path_or_data
                if conversion:
                    raise ValueError("conversion cannot be provided directly through conversion parameter.")

            conversion, query, data = self.webtoon.value.dump_conversion_query_value(data, conversion)

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
                (episode.episode_no, media_no, purpose, state, media_type, media_name, conversion, path, data, current_time)
            ).fetchone()
            return WebtoonMedia.from_media_id(media_id, self.webtoon)

    def remove(self, media: WebtoonMedia) -> None:
        result = self.webtoon.execute("DELETE FROM media WHERE id == ? RETURNING TRUE", (media.media_id(),))
        if result is None:
            raise KeyError(media)

    def set(self, media: WebtoonMediaData) -> None:
        # path가 있으면 conversion도 있어야 함
        if media.path is not None and media.conversion is None:
            raise ValueError("conversion is required when path is provided.")
        if media.path is not None and media.data is not None:
            raise ValueError("Only data or path should be provided.")

        conversion, query, data = self.webtoon.value.dump_conversion_query_value(media.data)
        result = self.webtoon.execute(f"""
            UPDATE media
            SET
                episode_no = ?,
                media_no = ?,
                purpose = ?,
                state = ?,
                media_type = ?,
                name = ?,
                conversion = ?,
                path = ?,
                data = {query},
                added_at = ?
            WHERE id == ?
            RETURNING TRUE
        """, (
            media.episode_no,
            media.media_no,
            media.purpose,
            media.state,
            media.media_type,
            media.name,
            media.conversion or conversion,
            self.webtoon.path.dump(media.path),
            data,
            media.added_at.timestamp(),
            media.media_id,
        ))
        if result is None:
            raise KeyError(media)

    def _load(self, media_id: int) -> WebtoonMediaData:
        result = self.webtoon.execute(
            """
            SELECT id, episode_no, media_no, purpose, state, media_type, name, conversion, path, data, added_at
            FROM media
            WHERE id == ?
            """,
            (media_id,)
        )
        if result is None:
            raise ValueError(f"Can't find media that have media_id == {media_id}.")
        media_id, episode_no, media_no, purpose, state, media_type, name, conversion, path, data, added_at = result
        return WebtoonMediaData(
            media_id=media_id,
            episode_no=episode_no,
            media_no=media_no,
            purpose=purpose,
            state=state,
            media_type=media_type,
            name=name,
            conversion=conversion,
            path=path and self.webtoon.path.load(path),
            data=self.webtoon.value.load(conversion, data),
            added_at=fromtimestamp(added_at),
        )

    def iterate(
        self,
        episode: WebtoonEpisode | None,
        purpose: str | None = None,
        state: EpisodeState = None,
    ) -> typing.Iterator[WebtoonMedia]:
        with self.webtoon.connection.cursor() as cur:
            for media_id, in cur.execute(
                """
                SELECT id
                FROM media
                WHERE (?1 IS NULL OR episode_no == ?1) AND (?2 IS NULL OR purpose == ?2) AND (?3 IS NULL OR state == ?3)
                """,
                (episode.episode_no if episode else None, purpose, state)
            ):
                yield WebtoonMedia.from_media_id(media_id, self.webtoon)

    def load_data(self, media: WebtoonMedia, store_data: bool = False) -> ValueType:
        data = media.load()
        if data.path is None:
            return data.data
        result = self.webtoon.value.load_bytes(data.conversion, data.path.read_bytes())
        if store_data:
            data.path = None
            data.conversion = None
            data.data = result
            self.set(data)
        return result

    def dump_path(self, media: WebtoonMedia, path: Path, *, replace_path: bool = False):
        data = media.load()
        if data.path is not None:
            return data.path
        else:
            if data.conversion:
                conversion = data.conversion
            else:
                conversion = self.webtoon.value.get_primitive_conversion(data.data)

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.webtoon.value.dump_bytes(data.data))
            data.data, data.path, data.conversion = None, path, conversion
            self.set(data)


@dataclass(slots=True)
class WebtoonMediaData:
    media_id: int
    episode_no: int
    media_no: int
    purpose: str | None
    media_type: str
    name: str
    state: EpisodeState
    conversion: ConversionType
    path: Path | None
    data: ValueType
    added_at: datetime.datetime
    _webtoon: WebtoonType | None = None


class WebtoonMedia:
    @typing.overload
    def __init__(self, *, media_id: int, webtoon: WebtoonType) -> None: ...
    @typing.overload
    def __init__(self, *, media: WebtoonMediaData) -> None: ...
    def __init__(self, *, media_id: int | None = None, webtoon: WebtoonType | None = None, media: WebtoonMediaData | None = None) -> None:
        if not (media is None) ^ (media_id is None):
            raise ValueError("Only one of media or media_id and webtoon can be provided.")
        if media is None and (media_id is None) ^ (webtoon is None):
            raise ValueError("media_id must be provided with webtoon.")
        self._media_id = media_id
        self._webtoon = webtoon
        self._media = media

    @classmethod
    def from_media_id(cls, media_id: int, webtoon: WebtoonType) -> typing.Self:
        return cls(media_id=media_id, webtoon=webtoon)

    @classmethod
    def from_media(cls, media: WebtoonMediaData) -> typing.Self:
        return cls(media=media)

    def load(self, store_media: bool = False) -> WebtoonMediaData:
        if self._media_id is None:
            return self._media  # type: ignore
        else:
            media = self._webtoon.media._load(self._media_id)  # type: ignore
            if store_media:
                self._media_id, self._media = None, media
            return media

    def media_id(self, store_id: bool = False) -> int:
        if self._media_id is None:
            media_id = self._media.media_id  # type: ignore
            if store_id:
                self._media_id, self._media = media_id, None
            return media_id
        else:
            return self._media_id

    @property
    def loaded(self) -> bool:
        return self._media_id is None

    @property
    def stored(self) -> int | WebtoonMediaData:
        return self._media if self._media_id is None else self._media_id  # type: ignore
