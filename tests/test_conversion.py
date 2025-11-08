"""
WebtoonValue 클래스에 대한 포괄적인 테스트
값 변환(conversion), dump/load, 타입 처리 등을 테스트합니다.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbtn import Webtoon
from wbtn._json_data import JsonData


# ===== 기본 인스턴스화 및 dump_conversion_query_value 테스트 =====


def test_webtoon_value_initialization(webtoon_instance: Webtoon):
    """WebtoonValue 인스턴스 생성"""
    assert webtoon_instance.value.webtoon is webtoon_instance


def test_dump_conversion_query_value_with_none():
    """None 값에 대한 dump_conversion_query_value"""
    with Webtoon(":memory:") as webtoon:
        conversion, query, dumped = webtoon.value.dump_conversion_query_value(None, primitive_conversion=True)
        conversion, query, dumped = webtoon.value.dump_conversion_query_value(None, primitive_conversion=True)

        assert conversion == "null"
        assert query == "?"
        assert dumped is None


def test_dump_conversion_query_value_with_string():
    """문자열 값에 대한 dump_conversion_query_value"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        test_string = "hello world"
        conversion, query, dumped = webtoon.value.dump_conversion_query_value(test_string, primitive_conversion=True)

        assert conversion == "str"
        assert query == "?"
        assert dumped == test_string


def test_dump_conversion_query_value_with_integer():
    """정수 값에 대한 dump_conversion_query_value"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        test_int = 42
        conversion, query, dumped = webtoon.value.dump_conversion_query_value(test_int, primitive_conversion=True)

        assert conversion == "int"
        assert query == "?"
        assert dumped == test_int


def test_dump_conversion_query_value_with_float():
    """실수 값에 대한 dump_conversion_query_value"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        test_float = 3.14159
        conversion, query, dumped = webtoon.value.dump_conversion_query_value(test_float, primitive_conversion=True)

        assert conversion == "float"
        assert query == "?"
        assert dumped == test_float


def test_dump_conversion_query_value_with_boolean_true():
    """True 값에 대한 dump_conversion_query_value"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        conversion, query, dumped = webtoon.value.dump_conversion_query_value(True, primitive_conversion=True)

        assert conversion == "bool"
        assert query == "?"
        assert dumped is True


def test_dump_conversion_query_value_with_boolean_false():
    """False 값에 대한 dump_conversion_query_value"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        conversion, query, dumped = webtoon.value.dump_conversion_query_value(False, primitive_conversion=True)

        assert conversion == "bool"
        assert query == "?"
        assert dumped is False


def test_dump_conversion_query_value_with_bytes():
    """바이트 값에 대한 dump_conversion_query_value"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        test_bytes = b"binary data"
        conversion, query, dumped = webtoon.value.dump_conversion_query_value(test_bytes, primitive_conversion=True)

        assert conversion == "bytes"
        assert query == "?"
        assert dumped == test_bytes


def test_dump_conversion_query_value_with_json_data():
    """JsonData 값에 대한 dump_conversion_query_value"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        json_obj = JsonData(data={"key": "value"}, conversion="json")
        conversion, query, dumped = webtoon.value.dump_conversion_query_value(json_obj, primitive_conversion=True)

        assert conversion == "json"
        assert query == "json(?)"
        assert dumped == '{"key":"value"}'


def test_dump_conversion_query_value_with_jsonb_data():
    """JsonData(jsonb) 값에 대한 dump_conversion_query_value"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        json_obj = JsonData(data=[1, 2, 3], conversion="jsonb")
        conversion, query, dumped = webtoon.value.dump_conversion_query_value(json_obj, primitive_conversion=True)

        assert conversion == "jsonb"
        assert query == "jsonb(?)"
        assert dumped == '[1,2,3]'


def test_dump_conversion_query_value_with_path(tmp_path: Path):
    """Path 값에 대한 dump_conversion_query_value"""
    db_path = tmp_path / "test.wbtn"
    test_file = tmp_path / "file.txt"
    test_file.touch()

    with Webtoon(db_path) as webtoon:
        # Use webtoon.value directly
        conversion, query, dumped = webtoon.value.dump_conversion_query_value(test_file, primitive_conversion=True)

        assert conversion == "path"
        assert query == "?"
        assert isinstance(dumped, str)
        assert dumped == "file.txt"


def test_dump_conversion_query_value_with_explicit_conversion():
    """명시적으로 conversion을 지정한 경우"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        test_int = 100
        conversion, query, dumped = webtoon.value.dump_conversion_query_value(
            test_int,
            conversion="int",
            primitive_conversion=True
        )

        assert conversion == "int"
        assert query == "CAST(? AS INTEGER)"
        assert dumped == test_int


def test_dump_conversion_query_value_with_primitive_conversion_false():
    """primitive_conversion=False인 경우"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        test_string = "test"
        conversion, query, dumped = webtoon.value.dump_conversion_query_value(
            test_string,
            primitive_conversion=False
        )

        assert conversion is None
        assert query == "?"
        assert dumped == test_string


# ===== get_primitive_conversion 테스트 =====


def test_get_primitive_conversion_with_none():
    """None의 primitive conversion"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        conversion = webtoon.value.get_primitive_conversion(None)
        assert conversion == "null"


def test_get_primitive_conversion_with_string():
    """문자열의 primitive conversion"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        conversion = webtoon.value.get_primitive_conversion("test")
        assert conversion == "str"


def test_get_primitive_conversion_with_integer():
    """정수의 primitive conversion"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        conversion = webtoon.value.get_primitive_conversion(123)
        assert conversion == "int"


def test_get_primitive_conversion_with_float():
    """실수의 primitive conversion"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        conversion = webtoon.value.get_primitive_conversion(1.5)
        assert conversion == "float"


def test_get_primitive_conversion_with_boolean():
    """불린의 primitive conversion"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        conversion = webtoon.value.get_primitive_conversion(True)
        assert conversion == "bool"


def test_get_primitive_conversion_with_bytes():
    """바이트의 primitive conversion"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        conversion = webtoon.value.get_primitive_conversion(b"data")
        assert conversion == "bytes"


def test_get_primitive_conversion_with_path():
    """Path의 primitive conversion"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        conversion = webtoon.value.get_primitive_conversion(Path("/tmp/test"))
        assert conversion == "path"


def test_get_primitive_conversion_with_json_data():
    """JsonData의 primitive conversion"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        json_obj = JsonData(data={}, conversion="json")
        conversion = webtoon.value.get_primitive_conversion(json_obj)
        assert conversion == "json"


def test_get_primitive_conversion_with_jsonb_data():
    """JsonData(jsonb)의 primitive conversion"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        json_obj = JsonData(data=[], conversion="jsonb")
        conversion = webtoon.value.get_primitive_conversion(json_obj)
        assert conversion == "jsonb"


def test_get_primitive_conversion_with_invalid_type():
    """유효하지 않은 타입의 primitive conversion"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        with pytest.raises(ValueError, match="Invalid type to convert"):
            webtoon.value.get_primitive_conversion(object())


# ===== dump_bytes 테스트 =====


def test_dump_bytes_with_none():
    """None을 바이트로 dump"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.dump_bytes(None)
        assert result == b""


def test_dump_bytes_with_true():
    """True를 바이트로 dump"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.dump_bytes(True)
        assert result == b"1"


def test_dump_bytes_with_false():
    """False를 바이트로 dump"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.dump_bytes(False)
        assert result == b"0"


def test_dump_bytes_with_string():
    """문자열을 바이트로 dump"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.dump_bytes("hello")
        assert result == b"hello"


def test_dump_bytes_with_string_with_unicode():
    """유니코드 문자열을 바이트로 dump"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.dump_bytes("안녕하세요")
        # Note: direct byte literal comparison for Korean text
        expected = b"\xec\x95\x88\xeb\x85\x95\xed\x95\x98\xec\x84\xb8\xec\x9a\x94"
        assert result == expected


def test_dump_bytes_with_integer():
    """정수를 바이트로 dump"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.dump_bytes(42)
        assert result == b"42"


def test_dump_bytes_with_float():
    """실수를 바이트로 dump"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.dump_bytes(3.14)
        assert result == b"3.14"


def test_dump_bytes_with_bytes():
    """바이트를 바이트로 dump (그대로 반환)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        test_bytes = b"binary data"
        result = webtoon.value.dump_bytes(test_bytes)
        assert result == test_bytes


def test_dump_bytes_with_json_data():
    """JsonData를 바이트로 dump"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        json_obj = JsonData(data={"test": "data"})
        result = webtoon.value.dump_bytes(json_obj)
        assert result == b'{"test":"data"}'


def test_dump_bytes_with_invalid_type():
    """유효하지 않은 타입을 바이트로 dump"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        with pytest.raises(ValueError, match="Invalid type to convert"):
            webtoon.value.dump_bytes(object())  # type: ignore


# ===== load 테스트 =====


def test_load_with_none_conversion():
    """conversion이 None인 경우 원본 값 반환"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.load(None, "test")
        assert result == "test"


def test_load_with_null_conversion():
    """null conversion은 항상 None 반환"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.load("null", "any value")
        assert result is None


def test_load_with_value_none_returns_none():
    """원본 값이 None이면 conversion 상관없이 None 반환"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.load("str", None)
        assert result is None


def test_load_str_conversion():
    """str conversion으로 문자열 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.load("str", "test string")
        assert result == "test string"
        assert isinstance(result, str)


def test_load_int_conversion():
    """int conversion으로 정수 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.load("int", 42)
        assert result == 42
        assert isinstance(result, int)


def test_load_float_conversion():
    """float conversion으로 실수 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.load("float", 3.14)
        assert result == 3.14
        assert isinstance(result, float)


def test_load_bool_conversion_from_int():
    """int 값을 bool conversion으로 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result_true = webtoon.value.load("bool", 1)
        result_false = webtoon.value.load("bool", 0)

        assert result_true is True
        assert result_false is False


def test_load_bytes_conversion():
    """bytes conversion으로 바이트 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        test_bytes = b"binary"
        result = webtoon.value.load("bytes", test_bytes)
        assert result == test_bytes
        assert isinstance(result, bytes)


def test_load_json_conversion_from_string():
    """json conversion으로 문자열에서 JsonData 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        json_string = '{"key":"value"}'
        result = webtoon.value.load("json", json_string)

        assert isinstance(result, JsonData)
        assert result.load() == {"key": "value"}


def test_load_json_conversion_from_bytes():
    """json conversion으로 바이트에서 JsonData 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        json_bytes = b'[1,2,3]'
        result = webtoon.value.load("json", json_bytes)

        assert isinstance(result, JsonData)
        assert result.load() == [1, 2, 3]


def test_load_jsonb_conversion_from_string():
    """jsonb conversion으로 문자열에서 JsonData 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        json_string = '{"num":42}'
        result = webtoon.value.load("jsonb", json_string)

        assert isinstance(result, JsonData)
        assert result.load() == {"num": 42}


def test_load_jsonb_conversion_from_bytes():
    """jsonb conversion으로 바이트에서 JsonData 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        json_bytes = b'{"test":true}'
        result = webtoon.value.load("jsonb", json_bytes)

        assert isinstance(result, JsonData)
        assert result.load() == {"test": True}


def test_load_with_invalid_conversion():
    """유효하지 않은 conversion으로 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        with pytest.raises(ValueError, match="Invalid type .* for conversion or unknown conversion"):
            webtoon.value.load("unknown", "value")  # type: ignore


def test_load_with_mismatched_type_and_conversion():
    """conversion과 타입이 맞지 않는 경우"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        with pytest.raises(ValueError, match="Invalid type .* for conversion"):
            webtoon.value.load("str", 123)  # str conversion인데 int 값


# ===== load_bytes 테스트 =====


def test_load_bytes_without_conversion_raises_error():
    """conversion 없이 load_bytes 호출하면 에러"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        with pytest.raises(ValueError, match="Conversion value is not provided"):
            webtoon.value.load_bytes(None, b"data")


def test_load_bytes_with_null_conversion():
    """null conversion으로 바이트 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.load_bytes("null", b"any data")
        assert result is None


def test_load_bytes_str_conversion():
    """str conversion으로 바이트에서 문자열 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.load_bytes("str", b"hello")
        assert result == "hello"
        assert isinstance(result, str)


def test_load_bytes_str_conversion_with_unicode():
    """str conversion으로 유니코드 바이트 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        # UTF-8 encoded bytes for "한글"
        korean_bytes = b"\xed\x95\x9c\xea\xb8\x80"
        result = webtoon.value.load_bytes("str", korean_bytes)
        assert result == "한글"


def test_load_bytes_bytes_conversion():
    """bytes conversion으로 바이트 그대로 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        test_bytes = b"binary data"
        result = webtoon.value.load_bytes("bytes", test_bytes)
        assert result == test_bytes


def test_load_bytes_bool_conversion_true():
    """bool conversion으로 true 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.load_bytes("bool", b"1")
        assert result is True


def test_load_bytes_bool_conversion_false():
    """bool conversion으로 false 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.load_bytes("bool", b"0")
        assert result is False


def test_load_bytes_bool_conversion_with_empty_bytes():
    """빈 바이트는 False로 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.load_bytes("bool", b"")
        assert result is False


def test_load_bytes_bool_conversion_with_non_zero():
    """0이 아닌 바이트는 True로 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.load_bytes("bool", b"anything")
        assert result is True


def test_load_bytes_int_conversion():
    """int conversion으로 바이트에서 정수 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.load_bytes("int", b"42", primitive_conversion=True)
        assert result == 42
        assert isinstance(result, int)


def test_load_bytes_int_conversion_negative():
    """int conversion으로 음수 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.load_bytes("int", b"-100", primitive_conversion=True)
        assert result == -100


def test_load_bytes_float_conversion():
    """float conversion으로 바이트에서 실수 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.load_bytes("float", b"3.14159", primitive_conversion=True)
        assert isinstance(result, float)
        assert abs(result - 3.14159) < 0.00001  # type: ignore


def test_load_bytes_float_conversion_scientific_notation():
    """float conversion으로 과학적 표기법 로드"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.load_bytes("float", b"1.5e-10", primitive_conversion=True)
        assert isinstance(result, float)
        assert abs(result - 1.5e-10) < 1e-20  # type: ignore


def test_load_bytes_path_conversion(tmp_path: Path):
    """path conversion으로 바이트에서 Path 로드"""
    db_path = tmp_path / "test.wbtn"
    test_file = tmp_path / "test.txt"
    test_file.touch()

    with Webtoon(db_path) as webtoon:
        # Use webtoon.value directly
        result = webtoon.value.load_bytes("path", b"test.txt")

        assert isinstance(result, Path)
        assert result == test_file


def test_load_bytes_with_primitive_conversion_false():
    """primitive_conversion=False일 때 바이트 그대로 반환"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        test_bytes = b"123"
        result = webtoon.value.load_bytes("int", test_bytes, primitive_conversion=False)
        assert result == test_bytes


def test_load_bytes_with_invalid_conversion():
    """유효하지 않은 conversion으로 load_bytes"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        with pytest.raises(ValueError, match="Invalid conversion"):
            webtoon.value.load_bytes("unknown", b"data", primitive_conversion=True)  # type: ignore


# ===== _dump_str_bytes 내부 메서드 테스트 =====


def test_dump_str_bytes_with_none():
    """None을 dump하면 빈 문자열"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._dump_str_bytes(None)
        assert result == ""


def test_dump_str_bytes_with_true():
    """True를 dump하면 "1" """
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._dump_str_bytes(True)
        assert result == "1"


def test_dump_str_bytes_with_false():
    """False를 dump하면 "0" """
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._dump_str_bytes(False)
        assert result == "0"


def test_dump_str_bytes_with_json_data():
    """JsonData를 dump"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        json_obj = JsonData(data={"a": 1})
        result = webtoon.value._dump_str_bytes(json_obj)
        assert result == '{"a":1}'


def test_dump_str_bytes_with_string():
    """문자열은 그대로 반환"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._dump_str_bytes("test")
        assert result == "test"


def test_dump_str_bytes_with_bytes():
    """바이트는 그대로 반환"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        test_bytes = b"data"
        result = webtoon.value._dump_str_bytes(test_bytes)
        assert result == test_bytes


def test_dump_str_bytes_with_int():
    """정수를 문자열로 변환"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._dump_str_bytes(123)
        assert result == "123"


def test_dump_str_bytes_with_float():
    """실수를 문자열로 변환"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._dump_str_bytes(3.14)
        assert result == "3.14"


def test_dump_str_bytes_with_invalid_type():
    """유효하지 않은 타입으로 dump"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        with pytest.raises(ValueError, match="Invalid type to convert"):
            webtoon.value._dump_str_bytes(object())  # type: ignore


# ===== _get_conversion 내부 메서드 테스트 =====


def test_get_conversion_with_none():
    """None의 conversion"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_conversion(None, primitive_conversion=True)
        assert result == "null"


def test_get_conversion_with_json_data_json():
    """JsonData(json)의 conversion"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        json_obj = JsonData(data={}, conversion="json")
        result = webtoon.value._get_conversion(json_obj, primitive_conversion=True)
        assert result == "json"


def test_get_conversion_with_json_data_jsonb():
    """JsonData(jsonb)의 conversion"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        json_obj = JsonData(data=[], conversion="jsonb")
        result = webtoon.value._get_conversion(json_obj, primitive_conversion=True)
        assert result == "jsonb"


def test_get_conversion_with_path():
    """Path의 conversion"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_conversion(Path("/tmp"), primitive_conversion=True)
        assert result == "path"


def test_get_conversion_with_bool():
    """bool의 conversion"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_conversion(True, primitive_conversion=True)
        assert result == "bool"


def test_get_conversion_with_str_primitive():
    """str의 conversion (primitive_conversion=True)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_conversion("test", primitive_conversion=True)
        assert result == "str"


def test_get_conversion_with_str_non_primitive():
    """str의 conversion (primitive_conversion=False)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_conversion("test", primitive_conversion=False)
        assert result is None


def test_get_conversion_with_bytes_primitive():
    """bytes의 conversion (primitive_conversion=True)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_conversion(b"data", primitive_conversion=True)
        assert result == "bytes"


def test_get_conversion_with_bytes_non_primitive():
    """bytes의 conversion (primitive_conversion=False)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_conversion(b"data", primitive_conversion=False)
        assert result is None


def test_get_conversion_with_int_primitive():
    """int의 conversion (primitive_conversion=True)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_conversion(42, primitive_conversion=True)
        assert result == "int"


def test_get_conversion_with_int_non_primitive():
    """int의 conversion (primitive_conversion=False)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_conversion(42, primitive_conversion=False)
        assert result is None


def test_get_conversion_with_float_primitive():
    """float의 conversion (primitive_conversion=True)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_conversion(3.14, primitive_conversion=True)
        assert result == "float"


def test_get_conversion_with_float_non_primitive():
    """float의 conversion (primitive_conversion=False)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_conversion(3.14, primitive_conversion=False)
        assert result is None


def test_get_conversion_with_invalid_type():
    """유효하지 않은 타입의 conversion (primitive_conversion=True)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        with pytest.raises(ValueError, match="Invalid type to convert"):
            webtoon.value._get_conversion(object(), primitive_conversion=True)  # type: ignore


# ===== _get_query 내부 메서드 테스트 =====


def test_get_query_with_none_conversion():
    """None conversion의 쿼리"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_query(None)
        assert result == "?"


def test_get_query_with_null_conversion():
    """null conversion의 쿼리"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_query("null")
        assert result == "?"


def test_get_query_with_path_conversion():
    """path conversion의 쿼리"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_query("path")
        assert result == "?"


def test_get_query_with_json_conversion():
    """json conversion의 쿼리"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_query("json")
        assert result == "json(?)"


def test_get_query_with_jsonb_conversion():
    """jsonb conversion의 쿼리"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_query("jsonb")
        assert result == "jsonb(?)"


def test_get_query_with_str_without_cast():
    """str conversion 쿼리 (cast_primitive=False)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_query("str", cast_primitive=False)
        assert result == "?"


def test_get_query_with_str_with_cast():
    """str conversion 쿼리 (cast_primitive=True)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_query("str", cast_primitive=True)
        assert result == "CAST(? AS TEXT)"


def test_get_query_with_bytes_without_cast():
    """bytes conversion 쿼리 (cast_primitive=False)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_query("bytes", cast_primitive=False)
        assert result == "?"


def test_get_query_with_bytes_with_cast():
    """bytes conversion 쿼리 (cast_primitive=True)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_query("bytes", cast_primitive=True)
        assert result == "CAST(? AS BLOB)"


def test_get_query_with_int_without_cast():
    """int conversion 쿼리 (cast_primitive=False)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_query("int", cast_primitive=False)
        assert result == "?"


def test_get_query_with_int_with_cast():
    """int conversion 쿼리 (cast_primitive=True)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_query("int", cast_primitive=True)
        assert result == "CAST(? AS INTEGER)"


def test_get_query_with_float_without_cast():
    """float conversion 쿼리 (cast_primitive=False)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_query("float", cast_primitive=False)
        assert result == "?"


def test_get_query_with_float_with_cast():
    """float conversion 쿼리 (cast_primitive=True)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_query("float", cast_primitive=True)
        assert result == "CAST(? AS REAL)"


def test_get_query_with_bool_without_cast():
    """bool conversion 쿼리 (cast_primitive=False)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_query("bool", cast_primitive=False)
        assert result == "?"


def test_get_query_with_bool_with_cast():
    """bool conversion 쿼리 (cast_primitive=True)"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._get_query("bool", cast_primitive=True)
        assert result == "CAST(? AS INTEGER)"


def test_get_query_with_unknown_conversion():
    """알 수 없는 conversion의 쿼리"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        with pytest.raises(ValueError, match="Unknown conversion"):
            webtoon.value._get_query("unknown", cast_primitive=True)  # type: ignore


# ===== _dump 내부 메서드 테스트 =====


def test_dump_with_json_data():
    """JsonData를 dump"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        json_obj = JsonData(data={"key": "value"})
        result = webtoon.value._dump(json_obj)
        assert result == '{"key":"value"}'


def test_dump_with_path(tmp_path: Path):
    """Path를 dump"""
    db_path = tmp_path / "test.wbtn"
    test_file = tmp_path / "file.txt"
    test_file.touch()

    with Webtoon(db_path) as webtoon:
        # Use webtoon.value directly
        result = webtoon.value._dump(test_file)
        assert isinstance(result, str)
        assert result == "file.txt"


def test_dump_with_primitive_type():
    """primitive type은 그대로 반환"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly

        assert webtoon.value._dump("string") == "string"
        assert webtoon.value._dump(123) == 123
        assert webtoon.value._dump(3.14) == 3.14
        assert webtoon.value._dump(True) is True
        assert webtoon.value._dump(None) is None
        assert webtoon.value._dump(b"bytes") == b"bytes"


# ===== 통합 테스트 및 엣지 케이스 =====


def test_round_trip_conversion_with_string():
    """문자열 dump/load 왕복 테스트"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        original = "test string"

        conversion, query, dumped = webtoon.value.dump_conversion_query_value(original, primitive_conversion=True)
        loaded = webtoon.value.load(conversion, dumped)

        assert loaded == original


def test_round_trip_conversion_with_integer():
    """정수 dump/load 왕복 테스트"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        original = 42

        conversion, query, dumped = webtoon.value.dump_conversion_query_value(original, primitive_conversion=True)
        loaded = webtoon.value.load(conversion, dumped)

        assert loaded == original


def test_round_trip_conversion_with_json_data():
    """JsonData dump/load 왕복 테스트"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        original_data = {"test": [1, 2, 3], "nested": {"key": "value"}}
        original = JsonData(data=original_data)

        conversion, query, dumped = webtoon.value.dump_conversion_query_value(original, primitive_conversion=True)
        loaded = webtoon.value.load(conversion, dumped)

        assert isinstance(loaded, JsonData)
        assert loaded.load() == original_data


def test_round_trip_conversion_with_bytes():
    """바이트 dump/load 왕복 테스트"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        original = b"binary data \x00\x01\x02"

        conversion, query, dumped = webtoon.value.dump_conversion_query_value(original, primitive_conversion=True)
        loaded = webtoon.value.load(conversion, dumped)

        assert loaded == original


def test_round_trip_conversion_with_boolean():
    """불린 dump/load 왕복 테스트"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly

        for original in [True, False]:
            conversion, query, dumped = webtoon.value.dump_conversion_query_value(original, primitive_conversion=True)
            loaded = webtoon.value.load(conversion, dumped)
            assert loaded == original


def test_round_trip_bytes_conversion_with_path(tmp_path: Path):
    """Path dump/load 왕복 테스트 (dump_bytes는 Path를 직접 처리하지 않음)"""
    db_path = tmp_path / "test.wbtn"
    test_file = tmp_path / "test.txt"
    test_file.touch()

    with Webtoon(db_path) as webtoon:
        # Use webtoon.value directly

        # dump는 Path를 처리하므로 이를 사용
        dumped_str = webtoon.value.webtoon.path.dump_str(test_file)
        dumped_bytes = dumped_str.encode("utf-8")
        loaded = webtoon.value.load_bytes("path", dumped_bytes)

        assert loaded == test_file


def test_round_trip_bytes_conversion_with_unicode():
    """유니코드 문자열 dump_bytes/load_bytes 왕복 테스트"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly
        original = "안녕하세요 🎉"

        dumped = webtoon.value.dump_bytes(original)
        loaded = webtoon.value.load_bytes("str", dumped)

        assert loaded == original


def test_special_case_empty_string():
    """빈 문자열 처리"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly

        conversion, query, dumped = webtoon.value.dump_conversion_query_value("", primitive_conversion=True)
        loaded = webtoon.value.load(conversion, dumped)

        assert loaded == ""


def test_special_case_empty_bytes():
    """빈 바이트 처리"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly

        conversion, query, dumped = webtoon.value.dump_conversion_query_value(b"", primitive_conversion=True)
        loaded = webtoon.value.load(conversion, dumped)

        assert loaded == b""


def test_special_case_zero_integer():
    """0 정수 처리"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly

        conversion, query, dumped = webtoon.value.dump_conversion_query_value(0, primitive_conversion=True)
        loaded = webtoon.value.load(conversion, dumped)

        assert loaded == 0


def test_special_case_zero_float():
    """0.0 실수 처리"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly

        conversion, query, dumped = webtoon.value.dump_conversion_query_value(0.0, primitive_conversion=True)
        loaded = webtoon.value.load(conversion, dumped)

        assert loaded == 0.0


def test_special_case_negative_numbers():
    """음수 처리"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly

        for original in [-1, -100, -3.14]:
            conversion, query, dumped = webtoon.value.dump_conversion_query_value(original, primitive_conversion=True)
            loaded = webtoon.value.load(conversion, dumped)
            assert loaded == original


def test_special_case_large_numbers():
    """큰 숫자 처리"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly

        large_int = 999999999999999999
        conversion, query, dumped = webtoon.value.dump_conversion_query_value(large_int, primitive_conversion=True)
        loaded = webtoon.value.load(conversion, dumped)
        assert loaded == large_int


def test_special_case_empty_json_object():
    """빈 JSON 객체 처리"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly

        json_obj = JsonData(data={})
        conversion, query, dumped = webtoon.value.dump_conversion_query_value(json_obj, primitive_conversion=True)
        loaded = webtoon.value.load(conversion, dumped)

        assert isinstance(loaded, JsonData)
        assert loaded.load() == {}


def test_special_case_empty_json_array():
    """빈 JSON 배열 처리"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly

        json_obj = JsonData(data=[])
        conversion, query, dumped = webtoon.value.dump_conversion_query_value(json_obj, primitive_conversion=True)
        loaded = webtoon.value.load(conversion, dumped)

        assert isinstance(loaded, JsonData)
        assert loaded.load() == []


def test_special_case_complex_nested_json():
    """복잡한 중첩 JSON 처리"""
    with Webtoon(":memory:") as webtoon:
        # Use webtoon.value directly

        complex_data = {
            "array": [1, 2, {"nested": True}],
            "null_value": None,
            "bool_value": False,
            "string": "test",
            "number": 42.5
        }
        json_obj = JsonData(data=complex_data)

        conversion, query, dumped = webtoon.value.dump_conversion_query_value(json_obj, primitive_conversion=True)
        loaded = webtoon.value.load(conversion, dumped)

        assert isinstance(loaded, JsonData)
        assert loaded.load() == complex_data
