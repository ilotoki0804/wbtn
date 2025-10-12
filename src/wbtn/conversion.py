from ._base import PrimitiveType, ConversionType
from ._json_data import JsonData

ValueType = PrimitiveType | JsonData

__all__ = (
    "dump_value",
    "get_conversion_and_query",
    "get_query",
    "load_value",
)


def dump_value(value: ValueType) -> str | PrimitiveType:
    if isinstance(value, JsonData):
        return value.dump()
    else:
        return value


def load_value(conversion: ConversionType, original_value: PrimitiveType) -> ValueType:
    match conversion:
        case None:
            return original_value
        case "json" | "jsonb":
            return JsonData.from_raw(original_value)  # type: ignore
        case _:
            raise ValueError(f"Unknown conversion: {conversion}")


def get_conversion_and_query(value: ValueType) -> tuple[ConversionType, str]:
    match value:
        case JsonData(conversion="json"):
            return "json", "json(?)"
        case JsonData(conversion="jsonb"):
            return "json", "jsonb(?)"
        case _:
            return None, "?"
            # raise ValueError(f"Unknown conversion: {conversion}")


def get_query(conversion: ConversionType) -> str:
    match conversion:
        case "json":
            return "json(?)"
        case "jsonb":
            return "jsonb(?)"
        case None:
            return "?"
        case _:
            raise ValueError(f"Unknown conversion: {conversion}")
