from __future__ import annotations

from dataclasses import dataclass
import datetime
import typing
from pathlib import Path

from .._base import (
    GET_VALUE,
    ConversionType,
    PrimitiveType,
    ValueType,
    fromtimestamp,
    timestamp,
)
from ._episode import WebtoonEpisode
from .._json_data import JsonData
from .._base import WebtoonType

__all__ = ("WebtoonContentManger", "WebtoonContentData", "WebtoonContent")


class WebtoonContentManger:
    __slots__ = "webtoon",

    def __init__(self, webtoon: WebtoonType):
        self.webtoon = webtoon

    def add_path_or_data(
        self,
        episode: WebtoonEpisode,
        content_no: int,
        kind: str,
        *,
        data: ValueType,
        conversion: ConversionType | None = None,
        path: Path,
        mkdir: bool = True,
    ) -> WebtoonContent:
        if self.webtoon.path.self_contained:
            return self.add(
                episode,
                content_no,
                kind,
                data=data,
                conversion=conversion,
            )
        else:
            if mkdir:
                path.parent.mkdir(parents=True, exist_ok=True)
            conversion = conversion or self.webtoon.value.get_primitive_conversion(data)
            result = self.add(
                episode,
                content_no,
                kind,
                conversion=conversion,
                path=path,
            )
            path.write_bytes(self.webtoon.value.dump_bytes(data))
            return result

    @typing.overload
    def add(
        self,
        episode: WebtoonEpisode,
        content_no: int,
        kind: str,
        *,
        conversion: ConversionType,
        path: Path,
    ) -> WebtoonContent: ...
    @typing.overload
    def add(
        self,
        episode: WebtoonEpisode,
        content_no: int,
        kind: str,
        *,
        data: ValueType | None = None,
        conversion: ConversionType | None = None,
    ) -> WebtoonContent: ...
    # media_no: '한 컷'을 의미하고, image 외에 comment, styles, meta 등 다양한 정보를 포함시킬 수 있다.
    # kind: image, text 등 실제 구성 요소와 thumbnail, comment, styles, meta 등 실제 구성 요소는 아닌 데이터가 혼합되어 있을 수 있다.
    def add(
        self,
        episode: WebtoonEpisode,
        content_no: int,
        kind: str,
        *,
        data: ValueType | None = None,
        conversion: ConversionType | None = None,
        path: Path | None = None,
    ) -> WebtoonContent:
        if path:
            if conversion is None:
                raise ValueError("Conversion must be provided with path.")
            if data is not None:
                raise ValueError("Data and path must not be given at the same time.")

        conversion, query, value = self.webtoon.value.dump_conversion_query_value(data, conversion, primitive_conversion=True)
        path_str = self.webtoon.path.dump(path)
        content_id, = self.webtoon.execute(
            f"""INSERT INTO Content (
                episode_no,
                content_no,
                kind,
                value,
                conversion,
                path,
                added_at
            ) VALUES (?, ?, ?, {query}, ?, ?, ?) RETURNING content_id""",
            (episode.episode_no, content_no, kind, value, conversion, path_str, timestamp())
        )
        return WebtoonContent.from_content_id(content_id, self.webtoon)

    def remove(self, content: WebtoonContent) -> None:
        result = self.webtoon.execute("DELETE FROM Content WHERE content_id == ? RETURNING TRUE", (content.content_id(),))
        if result is None:
            raise KeyError(content)

    def set(self, content: WebtoonContentData) -> None:
        # path가 있으면 conversion도 있어야 함
        if content.path is not None and content.conversion is None:
            raise ValueError("conversion is required when path is provided.")
        if content.path is not None and content.data is not None:
            raise ValueError("Only data or path should be provided.")

        conversion, query, value = self.webtoon.value.dump_conversion_query_value(content.data, primitive_conversion=True)
        result = self.webtoon.execute(f"""
            UPDATE Content
            SET
                episode_no = ?,
                content_no = ?,
                kind = ?,
                value = {query},
                conversion = ?,
                path = ?,
                added_at = ?
            WHERE content_id == ?
            RETURNING TRUE
        """, (
            content.episode_no,
            content.content_no,
            content.kind,
            value,
            content.conversion or conversion,
            self.webtoon.path.dump(content.path),
            content.added_at.timestamp(),
            content.content_id,
        ))
        if result is None:
            raise KeyError(content)

    def _load(self, content_id: int) -> WebtoonContentData:
        result = self.webtoon.execute(
            f"""
            SELECT content_id, episode_no, content_no, kind, {GET_VALUE}, conversion, path, added_at
            FROM Content
            WHERE content_id == ?
            """,
            (content_id,)
        )
        if result is None:
            raise ValueError(f"Can't find content that have content_id == {content_id}.")
        content_id, episode_no, content_no, kind, data, conversion, path, added_at = result
        return WebtoonContentData(
            content_id=content_id,
            episode_no=episode_no,
            content_no=content_no,
            kind=kind,
            conversion=conversion,
            path=self.webtoon.path.load(path),
            data=self.webtoon.value.load(conversion, data),
            added_at=fromtimestamp(added_at),
        )

    def iterate(
        self,
        episode: WebtoonEpisode | None,
        kind: str | None = None,
    ) -> typing.Iterator[WebtoonContent]:
        with self.webtoon.execute_with(
            """
            SELECT content_id
            FROM Content
            WHERE (?1 IS NULL OR episode_no == ?1) AND (?2 IS NULL OR kind == ?2)
            """,
            (episode.episode_no if episode else None, kind)
        ) as cur:
            for content_id, in cur:
                yield WebtoonContent.from_content_id(content_id, self.webtoon)

    def load_data(self, content: WebtoonContent, store_data: bool = False) -> ValueType:
        data = content.load()
        if data.path is None:
            return data.data
        result = self.webtoon.value.load_bytes(data.conversion, data.path.read_bytes())
        if store_data:
            data.path = None
            data.conversion = None
            data.data = result
            self.set(data)
        return result

    def dump_path(self, content: WebtoonContent, path: Path, *, replace_path: bool = False):
        data = content.load()
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
class WebtoonContentData:
    content_id: int
    episode_no: int
    content_no: int
    kind: str | None
    data: ValueType
    conversion: ConversionType | None
    path: Path | None
    added_at: datetime.datetime
    _webtoon: WebtoonType | None = None


class WebtoonContent:
    @typing.overload
    def __init__(self, *, content_id: int, webtoon: WebtoonType) -> None: ...
    @typing.overload
    def __init__(self, *, content: WebtoonContentData) -> None: ...
    def __init__(self, *, content_id: int | None = None, webtoon: WebtoonType | None = None, content: WebtoonContentData | None = None) -> None:
        if not (content is None) ^ (content_id is None):
            raise ValueError("Only one of content or content_id and webtoon can be provided.")
        if content is None and (content_id is None) ^ (webtoon is None):
            raise ValueError("content_id must be provided with webtoon.")
        self._content_id = content_id
        self._webtoon = webtoon
        self._content = content

    @classmethod
    def from_content_id(cls, content_id: int, webtoon: WebtoonType) -> typing.Self:
        return cls(content_id=content_id, webtoon=webtoon)

    @classmethod
    def from_content(cls, content: WebtoonContentData) -> typing.Self:
        return cls(content=content)

    def load(self, store_content: bool = False) -> WebtoonContentData:
        if self._content_id is None:
            return self._content  # type: ignore
        else:
            media = self._webtoon.content._load(self._content_id)  # type: ignore
            if store_content:
                self._content_id, self._content = None, media
            return media

    def content_id(self, store_id: bool = False) -> int:
        if self._content_id is None:
            content_id = self._content.content_id  # type: ignore
            if store_id:
                self._content_id, self._content = content_id, None
            return content_id
        else:
            return self._content_id

    @property
    def loaded(self) -> bool:
        return self._content_id is None

    @property
    def stored(self) -> int | WebtoonContentData:
        return self._content if self._content_id is None else self._content_id  # type: ignore
