import typing
from ._base import PrimitiveType, ConversionType
from ._json_data import JsonData

ValueType = PrimitiveType | JsonData

__all__ = (
    "load_value",
    "get_conversion_query_value",
)

_NOTSET = object()


def load_value(conversion: ConversionType, original_value: PrimitiveType) -> ValueType:
    match conversion:
        case None:
            return original_value
        case "json" | "jsonb":
            return JsonData.from_raw(original_value)  # type: ignore
        case _:
            raise ValueError(f"Unknown conversion: {conversion}")


def get_conversion_query_value(value: ValueType, conversion: ConversionType = _NOTSET) -> tuple[ConversionType, typing.LiteralString, PrimitiveType]:  # type: ignore
    if conversion is _NOTSET:
        return *_get_conversion_and_query(value), _dump_value(value)
    else:
        return conversion, _get_query(conversion), _dump_value(value)


def _dump_value(value: ValueType) -> str | PrimitiveType:
    if isinstance(value, JsonData):
        return value.dump()
    else:
        return value


def _get_conversion_and_query(value: ValueType) -> tuple[ConversionType, typing.LiteralString]:
    match value:
        case JsonData(conversion="json"):
            return "json", "json(?)"
        case JsonData(conversion="jsonb"):
            return "json", "jsonb(?)"
        case _:
            return None, "?"
            # raise ValueError(f"Unknown conversion: {conversion}")


def _get_query(conversion: ConversionType) -> typing.LiteralString:
    match conversion:
        case "json":
            return "json(?)"
        case "jsonb":
            return "jsonb(?)"
        case None:
            return "?"
        case _:
            raise ValueError(f"Unknown conversion: {conversion}")
