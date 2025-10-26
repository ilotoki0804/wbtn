from pathlib import Path
import typing
from .._base import PrimitiveType, ConversionType, ValueType, WebtoonType
from .._json_data import JsonData

__all__ = (
    "WebtoonValue",
)

_NOTSET = object()


class WebtoonValue:
    def __init__(self, webtoon: WebtoonType) -> None:
        self.webtoon = webtoon

    def dump_conversion_query_value(
        self,
        value: ValueType,
        conversion: ConversionType = None,
        *,
        primitive_conversion: bool = True,
    ) -> tuple[ConversionType, typing.LiteralString, PrimitiveType]:
        if conversion is None:
            conversion = self._get_conversion(value, primitive_conversion=primitive_conversion)
            query = self._get_query(conversion, cast_primitive=False)
        else:
            query = self._get_query(conversion, cast_primitive=True)
        return conversion, query, self._dump(value)

    def get_primitive_conversion(self, value) -> ConversionType:
        return self._get_conversion(value, primitive_conversion=True)

    def dump_bytes(self, value: ValueType) -> bytes:
        value = self._dump_str_bytes(value)
        return value.encode("utf-8") if isinstance(value, str) else value

    def load(self, conversion: ConversionType, original_value: PrimitiveType) -> ValueType:
        match conversion, original_value:
            case None, _:
                return original_value
            case "null", _:
                return None
            case _, None:
                return None
            case "json" | "jsonb", str() | bytes():
                return JsonData.from_raw(original_value)  # type: ignore
            case "bool", int():
                return bool(original_value)
            case "str", str():
                return original_value
            case "int", int():
                return original_value
            case "float", float():
                return original_value
            case "bytes", bytes():
                return original_value
            case _:
                raise ValueError(f"Invalid type {type(original_value).__name__!r} for conversion or unknown conversion {conversion!r}")

    def load_bytes(self, conversion: ConversionType, raw_bytes: bytes, *, primitive_conversion: bool = True) -> ValueType:
        match conversion:
            case None:
                raise ValueError("Conversion value is not provided")
            case "null":
                return None
            case "str":
                return raw_bytes.decode("utf-8")
            case "bytes":
                return raw_bytes
            case "bool":
                return raw_bytes != b"0" and bool(raw_bytes)
            case "path":
                return self.webtoon.path.load_str(raw_bytes.decode("utf-8"))
            case _ if not primitive_conversion:
                return raw_bytes
            case "int":
                return int(raw_bytes)
            case "float":
                return float(raw_bytes)
            case _:
                raise ValueError(f"Invalid conversion: {conversion!r}")

    def _dump_str_bytes(self, value: ValueType) -> str | bytes:
        match value:
            case None:
                return ""
            case True:
                return "1"
            case False:
                return "0"
            case JsonData():
                return value.dump()
            case str():
                return value
            case bytes():
                return value
            case int() | float():
                return str(value)
            case _:
                raise ValueError(f"Invalid type to convert: {type(value).__name__!r}")

    def _get_conversion(self, value: ValueType, *, primitive_conversion: bool = False) -> ConversionType:
        match value:
            case None:
                return "null"
            case JsonData(conversion="json"):
                return "json"
            case JsonData(conversion="jsonb"):
                return "json"
            case Path():
                return "path"
            case bool():
                return "bool"
            case _ if not primitive_conversion:
                return None
            case str():
                return "str"
            case bytes():
                return "bytes"
            case int():
                return "int"
            case float():
                return "float"
            case _:
                raise ValueError(f"Invalid type to convert: {type(value).__name__}")

    def _get_query(self, conversion: ConversionType, *, cast_primitive: bool = False) -> typing.LiteralString:
        # cast_primitive는 redundant한 conversion이니 굳이 하지 않아도 됨.
        # 해야 하는 경우는 conversion의 값과 primitive의 type이 정확하기 일치하는지 확인하고 싶을 때.
        # 그러나 이미 conversion이 주어지지 않는 경우 _get_conversion 단계에서 체크가 이루어지니 필요가 없고,
        # 만약 필요하다면 conversion과 data가 같이 주어지는 경우, data가 conversion과 일치하는 것을 보증하기 위해
        # cast_primitive를 사용해야 할 수 있다.
        match conversion:
            case None | "null" | "path":
                return "?"
            case "json":
                return "json(?)"
            case "jsonb":
                return "jsonb(?)"
            case _ if not cast_primitive:
                return "?"
            case "str":
                return "CAST(? AS TEXT)"
            case "bytes":
                return "CAST(? AS BLOB)"
            case "int":
                return "CAST(? AS INTEGER)"
            case "float":
                return "CAST(? AS REAL)"
            case "bool":
                return "CAST(? AS INTEGER)"
            case _:
                raise ValueError(f"Unknown conversion: {conversion}")

    def _dump(self, value: ValueType) -> str | PrimitiveType:
        if isinstance(value, JsonData):
            return value.dump()
        elif isinstance(value, Path):
            return self.webtoon.path.dump_str(value)
        else:
            return value
