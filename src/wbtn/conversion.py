import typing
from ._base import PrimitiveType, ConversionType, ValueType
from ._json_data import JsonData

__all__ = (
    "dump_bytes_value",
    "load_bytes_value",
    "load_value",
    "get_conversion_query_value",
    "get_primitive_conversion",
)

_NOTSET = object()


def dump_bytes_value(value: ValueType) -> bytes:
    value = _dump_bytes_value(value)
    if isinstance(value, str):
        return value.encode("utf-8")
    else:
        return value


def _dump_bytes_value(value: ValueType) -> str | bytes:
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
        case bytes() | bytearray() | memoryview():
            return value
        case int() | float():
            return str(value)
        case _:
            raise ValueError(f"Invalid type to convert: {type(value).__name__!r}")


@typing.overload
def load_bytes_value(conversion: typing.Literal["str"], raw_bytes: bytes, *, primitive_conversion: bool = True) -> str: ...
@typing.overload
def load_bytes_value(conversion: typing.Literal["bytes"], raw_bytes: bytes, *, primitive_conversion: bool = True) -> bytes: ...
@typing.overload
def load_bytes_value(conversion: typing.Literal["bool"], raw_bytes: bytes, *, primitive_conversion: bool = True) -> bool: ...
@typing.overload
def load_bytes_value(conversion: typing.Literal["int"], raw_bytes: bytes, *, primitive_conversion: typing.Literal[True] = True) -> int: ...
@typing.overload
def load_bytes_value(conversion: typing.Literal["float"], raw_bytes: bytes, *, primitive_conversion: typing.Literal[True] = True) -> float: ...
@typing.overload
def load_bytes_value(conversion: typing.Literal["int", "float", "bool"], raw_bytes: bytes, *, primitive_conversion: typing.Literal[False] = ...) -> bytes: ...
@typing.overload
def load_bytes_value(conversion: typing.Literal["int"], raw_bytes: bytes, *, primitive_conversion: bool = True) -> int | bytes: ...
@typing.overload
def load_bytes_value(conversion: typing.Literal["float"], raw_bytes: bytes, *, primitive_conversion: bool = True) -> float | bytes: ...
@typing.overload
def load_bytes_value(conversion: None, raw_bytes: bytes, *, primitive_conversion: bool = True) -> typing.Never: ...
@typing.overload
def load_bytes_value(conversion: ConversionType, raw_bytes: bytes, *, primitive_conversion: bool = True) -> PrimitiveType: ...
def load_bytes_value(conversion: ConversionType, raw_bytes: bytes, *, primitive_conversion: bool = True) -> PrimitiveType:
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
        case _ if not primitive_conversion:
            return raw_bytes
        case "int":
            return int(raw_bytes)
        case "float":
            return float(raw_bytes)
        case _:
            raise ValueError(f"Invalid conversion: {conversion!r}")


def load_value(conversion: ConversionType, original_value: PrimitiveType, *, check_primitive_conversion: bool = False) -> ValueType:
    match conversion, original_value:
        case None, _:
            return original_value
        case "null", _:
            return None
        case "json" | "jsonb", str() | bytes():
            return JsonData.from_raw(original_value)  # type: ignore
        case "bool", int():
            return bool(original_value)
        case _ if not check_primitive_conversion:
            return original_value
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


def get_conversion_query_value(value: ValueType, conversion: ConversionType = _NOTSET, *, primitive_conversion: bool = False) -> tuple[ConversionType, typing.LiteralString, PrimitiveType]:  # type: ignore
    if not_set := conversion is _NOTSET:
        conversion = _get_conversion(value, primitive_conversion=primitive_conversion)
    return conversion, _get_query(conversion, cast_primitive=not not_set), _dump_value(value)


def _dump_value(value: ValueType) -> str | PrimitiveType:
    if isinstance(value, JsonData):
        return value.dump()
    else:
        return value


def get_primitive_conversion(value) -> ConversionType:
    return _get_conversion(value, primitive_conversion=True)


def _get_conversion(value: ValueType, *, primitive_conversion: bool = False) -> ConversionType:
    match value:
        case JsonData(conversion="json"):
            return "json"
        case JsonData(conversion="jsonb"):
            return "json"
        # primitive conversion에 해당하긴 하지만 저장 시 변형되기에 예외적으로 conversion을 포함함
        case bool():
            return "bool"
        case None:
            return "null"
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


def _get_query(conversion: ConversionType, *, cast_primitive: bool = False) -> typing.LiteralString:
    match conversion:
        case None:
            return "?"
        case "json":
            return "json(?)"
        case "jsonb":
            return "jsonb(?)"
        case "null":
            return "?"
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
