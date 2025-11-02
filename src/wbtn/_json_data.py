from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import typing

from ._base import ConversionType, JsonType, PrimitiveType, ValueType, WebtoonType

__all__ = ("JsonData",)

if typing.TYPE_CHECKING:
    ResultType = typing.TypeVar("ResultType", covariant=True, default="typing.Any")
else:
    ResultType = typing.TypeVar("T", covariant=True)

_json_encoder = json.JSONEncoder(ensure_ascii=False, separators=(",", ":"))


def _json_dump(data: JsonType) -> str:
    return _json_encoder.encode(data)


class JsonData(typing.Generic[ResultType]):
    @typing.overload
    def __init__(
        self,
        *,
        raw: str | None = None,
        conversion: typing.Literal["json", "jsonb"] = "json",
    ): ...
    @typing.overload
    def __init__(
        self,
        *,
        data: ResultType | None = None,
        conversion: typing.Literal["json", "jsonb"] = "json",
    ): ...
    def __init__(
        self,
        *,
        data: ResultType | None = None,
        raw: str | None = None,
        conversion: typing.Literal["json", "jsonb"] = "json",
    ):
        if data is not None and raw is not None:
            raise ValueError("Only data or raw should be provided.")
        self._data = data
        self._raw = raw
        self.conversion = conversion

    def __eq__(self, other: JsonData) -> bool:
        # 두 개 모두 raw 상태인데 문자열이 정확하게 같다면 둘이 같은 것이 보장될 수 있음.
        # 약간의 효율성을 위한 코드이지 없어도 문제는 없음
        if not self.loaded and not other.loaded and self.stored == self.stored:
            return True
        # raw의 모습은 비록 같은 데이터라도 같을 수도 있음
        # indentation이 다르거나 같은 딕셔너리 내에서 키 순서가 다르거나 하는 등...
        # 따라서 둘 모두 로드한 뒤 비교할 수밖에 없음.
        return self.load() == other.load()

    @classmethod
    def from_data(cls, data: ResultType, conversion: typing.Literal["json", "jsonb"] = "json") -> typing.Self:  # type: ignore # 이 경우에는 바로 클래스를 만들러 가는 길이기 때문에 파라미터에 ResultType이 들어가도 괜찮음
        return cls(data=data, conversion=conversion)

    @classmethod
    def from_raw(cls, raw: str, conversion: typing.Literal["json", "jsonb"] = "json") -> typing.Self:
        return cls(raw=raw, conversion=conversion)

    def dump(self, *, store_raw: bool = False) -> str:
        if self._raw is None:
            # 캐싱을 하는 것 자체는 좋은데 이러면 제공한 데이터가 받은 쪽에서 변경되었을 때 parity가 박살남...
            # 따라서 캐싱을 하는 것은 무리가 있고, 하나의 데이터가 저장되면 나머지 데이터는 purge해야 함
            result = _json_dump(self._data)
            if store_raw:
                self._raw, self._data = result, None
            return result
        else:
            return self._raw

    def load(self, copy: bool = False, *, store_data: bool = False) -> ResultType:
        if self._raw is None:
            if copy:
                return deepcopy(self._data)  # type: ignore
            else:
                return self._data  # type: ignore
        else:
            result = json.loads(self._raw)
            if store_data:
                self._raw, self._data = None, result
            return result

    @property
    def loaded(self) -> bool:
        return self._raw is None

    @property
    def stored(self) -> str | ResultType:
        return self._data if self._raw is None else self._raw  # type: ignore


# sqlite3.register_adapter(JsonData, JsonData.load)


class WebtoonData:
    # 각각 path, data, conversion에 해당
    webtoon: WebtoonType
    is_bytes_raw: bool
    _raw: tuple[PrimitiveType, ConversionType | None, str | None] | None
    _parsed: tuple[ValueType, ConversionType | None, Path | None] | None
    __match_args__ = "path", "value", "conversion"

    def __init__(self, webtoon: WebtoonType, *, _raw=None, _parsed=None, is_bytes_raw: bool | None = None):
        raise NotImplementedError  # todo
        if (_raw is None) + (_parsed is None) != 1:
            raise ValueError("Only one of values (among raw, parsed) should be provided.")
        self.webtoon = webtoon
        self.is_bytes_raw = is_bytes_raw if is_bytes_raw is not None else _parsed[0] is not None if _raw is None else _raw[0] is None  # type: ignore
        self._raw = _raw
        self._parsed = _parsed

    @classmethod
    def from_raw(cls, webtoon: WebtoonType, raw_value: PrimitiveType, conversion: ConversionType | None, raw_path: str | None = None):
        return cls(webtoon, _raw=(raw_value, conversion, raw_path), is_bytes_raw=False)

    @classmethod
    def from_bytes_raw(cls, webtoon: WebtoonType, raw_value: bytes, conversion: ConversionType | None, raw_path: str | None):
        return cls(webtoon, _raw=(raw_value, conversion, raw_path), is_bytes_raw=True)

    @classmethod
    def from_parsed(cls, webtoon: WebtoonType, value: ValueError, conversion: ConversionType | None, path: Path | None = None, *, is_bytes_raw: bool | None = None):
        return cls(webtoon, _parsed=(path, value, conversion), is_bytes_raw=is_bytes_raw)

    def parse(self, store_parsed: bool = True):
        match self._raw, self._parsed, self.is_bytes_raw:
            case _, parsed, _ if parsed:
                return parsed
            case (value, conversion, path), _, False:
                value = self.webtoon.value.load(conversion, value)
                path = self.webtoon.path.load(path)
                result = value, conversion, path
                if store_parsed:
                    self._raw, self._parsed = None, result
                return result
            case (value, conversion, path), _, True:
                assert isinstance(value, bytes), "The value of bytes raw must be bytes."
                value = self.webtoon.value.load_bytes(conversion, value)
                path = self.webtoon.path.load(path)
                result = value, conversion, path
                if store_parsed:
                    self._raw, self._parsed = None, result
                return result
            case _:
                raise ValueError("Invalid set of values.")

    def dump(self, store_dumped: bool = False):
        match self._raw, self._parsed, self.is_bytes_raw:
            case raw, _, _ if raw:
                return raw
            case _, (value, conversion, path), False:
                conversion, query, value = self.webtoon.value.dump_conversion_query_value(
                    value, conversion, primitive_conversion=path is not None)
                path = self.webtoon.path.dump(path)
                result = value, conversion, path
                if store_dumped:
                    self._raw, self._parsed = result, None
                return result
            case _, (value, conversion, path), True:
                conversion = conversion or self.webtoon.value._get_conversion(
                    value, primitive_conversion=path is not None)
                value = self.webtoon.value.dump_bytes(value)
                path = self.webtoon.path.dump(path)
                result = value, conversion, path
                if store_dumped:
                    self._raw, self._parsed = result, None
                return result
            case _:
                raise ValueError("Invalid set of values.")

    @property
    def path(self) -> Path | None:
        value, conversion, path = self.parse()
        return path

    @property
    def value(self) -> ValueType:
        value, conversion, path = self.parse()
        return value

    @property
    def conversion(self) -> ConversionType | None:
        value, conversion, path = self.parse()
        return conversion
