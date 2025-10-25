"""
conversion 모듈에 대한 포괄적인 테스트
타입 변환, JSON/JSONB 처리, 에러 케이스 등을 테스트합니다.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbtn.conversion import (
    dump_bytes_value,
    get_conversion_query_value,
    get_primitive_conversion,
    load_bytes_value,
    load_value,
)
from wbtn._json_data import JsonData


# ===== dump_bytes_value 테스트 =====


def test_dump_none_returns_empty_bytes():
    """None은 빈 bytes로 변환되어야 함"""
    result = dump_bytes_value(None)
    assert result == b""


def test_dump_true_returns_one():
    """True는 b'1'로 변환되어야 함"""
    result = dump_bytes_value(True)
    assert result == b"1"


def test_dump_false_returns_zero():
    """False는 b'0'으로 변환되어야 함"""
    result = dump_bytes_value(False)
    assert result == b"0"


def test_dump_string_returns_utf8_encoded_bytes():
    """문자열은 UTF-8로 인코딩된 bytes로 변환되어야 함"""
    test_string = "안녕하세요"
    result = dump_bytes_value(test_string)
    assert result == test_string.encode("utf-8")


def test_dump_bytes_returns_as_is():
    """bytes는 그대로 반환되어야 함"""
    test_bytes = b"test data"
    result = dump_bytes_value(test_bytes)
    assert result == test_bytes


def test_dump_bytearray_returns_as_is():
    """bytearray도 그대로 반환되어야 함"""
    test_bytearray = bytearray(b"test data")
    result = dump_bytes_value(test_bytearray)
    assert result == test_bytearray


def test_dump_memoryview_returns_as_is():
    """memoryview도 그대로 반환되어야 함"""
    test_memoryview = memoryview(b"test data")
    result = dump_bytes_value(test_memoryview)
    assert result == test_memoryview


def test_dump_integer_returns_string_representation():
    """정수는 문자열 표현의 bytes로 변환되어야 함"""
    result = dump_bytes_value(42)
    assert result == b"42"


def test_dump_negative_integer():
    """음수도 올바르게 변환되어야 함"""
    result = dump_bytes_value(-123)
    assert result == b"-123"


def test_dump_float_returns_string_representation():
    """부동소수점은 문자열 표현의 bytes로 변환되어야 함"""
    result = dump_bytes_value(3.14159)
    assert result == b"3.14159"


def test_dump_negative_float():
    """음수 부동소수점도 올바르게 변환되어야 함"""
    result = dump_bytes_value(-2.718)
    assert result == b"-2.718"


def test_dump_json_data_returns_dumped_json():
    """JsonData는 JSON 문자열의 bytes로 변환되어야 함"""
    json_data = JsonData(data={"key": "value"})
    result = dump_bytes_value(json_data)
    assert result == b'{"key":"value"}'


def test_dump_complex_json_data():
    """복잡한 JSON 데이터도 올바르게 변환되어야 함"""
    json_data = JsonData(data={"nested": {"array": [1, 2, 3], "bool": True}})
    result = dump_bytes_value(json_data)
    # JSON 인코딩 결과 확인
    assert b"nested" in result
    assert b"array" in result


def test_dump_invalid_type_raises_value_error():
    """지원하지 않는 타입은 ValueError를 발생시켜야 함"""
    with pytest.raises(ValueError, match="Invalid type to convert"):
        dump_bytes_value(object())  # type: ignore


def test_dump_list_raises_value_error():
    """리스트는 JsonData로 감싸지 않으면 ValueError를 발생시켜야 함"""
    with pytest.raises(ValueError):
        dump_bytes_value([1, 2, 3])  # type: ignore


def test_dump_dict_raises_value_error():
    """딕셔너리는 JsonData로 감싸지 않으면 ValueError를 발생시켜야 함"""
    with pytest.raises(ValueError):
        dump_bytes_value({"key": "value"})  # type: ignore


# ===== load_bytes_value 테스트 =====


def test_load_string_conversion():
    """'str' conversion으로 UTF-8 디코딩"""
    result = load_bytes_value("str", b"hello")
    assert result == "hello"


def test_load_string_with_unicode():
    """유니코드 문자열 디코딩"""
    korean_text = "안녕하세요"
    result = load_bytes_value("str", korean_text.encode("utf-8"))
    assert result == korean_text


def test_load_bytes_conversion():
    """'bytes' conversion은 bytes로 반환"""
    test_bytes = b"123"
    result = load_bytes_value("bytes", test_bytes)
    assert result == b"123"


def test_load_integer_conversion_with_primitive():
    """'int' conversion으로 정수 변환"""
    result = load_bytes_value("int", b"42", primitive_conversion=True)
    assert result == 42
    assert isinstance(result, int)


def test_load_negative_integer():
    """음수 정수 변환"""
    result = load_bytes_value("int", b"-123", primitive_conversion=True)
    assert result == -123


def test_load_integer_without_primitive_returns_bytes():
    """primitive_conversion=False이면 bytes 반환"""
    result = load_bytes_value("int", b"42", primitive_conversion=False)
    assert result == b"42"


def test_load_float_conversion_with_primitive():
    """'float' conversion으로 부동소수점 변환"""
    result = load_bytes_value("float", b"3.14", primitive_conversion=True)
    assert result == 3.14
    assert isinstance(result, float)


def test_load_float_without_primitive_returns_bytes():
    """primitive_conversion=False이면 bytes 반환"""
    result = load_bytes_value("float", b"2.718", primitive_conversion=False)
    assert result == b"2.718"


def test_load_bool_conversion_with_one():
    """'1'은 True로 변환"""
    result = load_bytes_value("bool", b"1", primitive_conversion=True)
    assert result is True


def test_load_bool_conversion_with_zero():
    """'0'은 False로 변환"""
    result = load_bytes_value("bool", b"0", primitive_conversion=True)
    assert result is False


def test_load_bool_conversion_with_non_zero_string():
    """'0'이 아닌 문자열은 True로 변환"""
    assert load_bytes_value("bool", b"true") is True
    assert load_bytes_value("bool", b"false") is True  # "false"도 비어있지 않으므로 True
    assert load_bytes_value("bool", b"any") is True


def test_load_bool_without_primitive_returns_true():
    """primitive_conversion=False여도 bool은 변환됨 (bool은 항상 변환)"""
    result = load_bytes_value("bool", b"1", primitive_conversion=False)
    assert result is True


def test_load_bool_with_empty_bytes_returns_false():
    """bool에서 빈 bytes는 False로 변환"""
    assert load_bytes_value("bool", b"") is False


def test_load_none_conversion_raises_value_error():
    """conversion이 None이면 ValueError 발생"""
    with pytest.raises(ValueError, match="Conversion value is not provided"):
        load_bytes_value(None, b"test")


def test_load_invalid_conversion_raises_value_error():
    """지원하지 않는 conversion은 ValueError 발생"""
    with pytest.raises(ValueError, match="Invalid conversion"):
        load_bytes_value("invalid_type", b"test")  # type: ignore


def test_load_int_with_invalid_format_raises_value_error():
    """정수가 아닌 형식은 ValueError 발생"""
    with pytest.raises(ValueError):
        load_bytes_value("int", b"not a number", primitive_conversion=True)


def test_load_float_with_invalid_format_raises_value_error():
    """부동소수점이 아닌 형식은 ValueError 발생"""
    with pytest.raises(ValueError):
        load_bytes_value("float", b"not a float", primitive_conversion=True)


# ===== load_value 테스트 =====


def test_load_with_none_conversion_returns_original():
    """conversion이 None이면 원본 값 반환"""
    original = "test value"
    result = load_value(None, original)
    assert result is original


def test_load_with_null_conversion_returns_none():
    """'null' conversion은 항상 None 반환"""
    result = load_value("null", "any value")
    assert result is None


# ===== null conversion 테스트 =====


def test_load_bytes_value_null_conversion_returns_none():
    """load_bytes_value에서 'null' conversion은 None 반환"""
    result = load_bytes_value("null", b"any data")
    assert result is None


def test_load_bytes_value_null_with_empty_bytes():
    """'null' conversion은 빈 bytes에도 None 반환"""
    result = load_bytes_value("null", b"")
    assert result is None


def test_load_bytes_value_null_with_various_inputs():
    """'null' conversion은 어떤 입력에도 None 반환"""
    test_inputs = [b"0", b"1", b"true", b"false", b"123", b"text"]
    for input_bytes in test_inputs:
        result = load_bytes_value("null", input_bytes)
        assert result is None, f"Failed for input: {input_bytes}"


def test_load_value_null_with_string():
    """load_value에서 'null' conversion은 문자열 입력에도 None 반환"""
    result = load_value("null", "any string")
    assert result is None


def test_load_value_null_with_integer():
    """load_value에서 'null' conversion은 정수 입력에도 None 반환"""
    result = load_value("null", 12345)
    assert result is None


def test_load_value_null_with_float():
    """load_value에서 'null' conversion은 부동소수점 입력에도 None 반환"""
    result = load_value("null", 3.14)
    assert result is None


def test_load_value_null_with_bool():
    """load_value에서 'null' conversion은 불린 입력에도 None 반환"""
    assert load_value("null", True) is None
    assert load_value("null", False) is None


def test_load_value_null_with_bytes():
    """load_value에서 'null' conversion은 bytes 입력에도 None 반환"""
    result = load_value("null", b"test bytes")
    assert result is None


def test_load_value_null_with_none():
    """load_value에서 'null' conversion은 None 입력에도 None 반환"""
    result = load_value("null", None)
    assert result is None


def test_get_primitive_conversion_for_none():
    """None 값의 primitive conversion은 'null'"""
    result = get_primitive_conversion(None)
    assert result == "null"


def test_get_conversion_query_value_for_none():
    """None 값에 대한 query value 생성"""
    conversion, query, value = get_conversion_query_value(None)
    assert conversion == "null"
    assert query == "?"
    assert value is None


def test_get_conversion_query_value_null_with_explicit_conversion():
    """명시적으로 'null' conversion을 지정한 경우"""
    conversion, query, value = get_conversion_query_value("any value", conversion="null")
    assert conversion == "null"
    assert query == "?"
    assert value == "any value"


def test_null_conversion_with_primitive_conversion_false():
    """primitive_conversion=False여도 None은 'null' conversion"""
    conversion, query, value = get_conversion_query_value(None, primitive_conversion=False)
    assert conversion == "null"


def test_dump_and_load_none_roundtrip():
    """None 값의 dump/load 라운드트립"""
    # None을 dump
    dumped = dump_bytes_value(None)
    assert dumped == b""

    # 'null' conversion으로 load
    loaded = load_bytes_value("null", dumped)
    assert loaded is None


def test_load_json_conversion_returns_json_data():
    """'json' conversion은 JsonData 객체 반환"""
    json_string = '{"key":"value"}'
    result = load_value("json", json_string)
    assert isinstance(result, JsonData)
    assert result.load() == {"key": "value"}


def test_load_jsonb_conversion_returns_json_data():
    """'jsonb' conversion도 JsonData 객체 반환"""
    json_string = '{"array":[1,2,3]}'
    result = load_value("jsonb", json_string)
    assert isinstance(result, JsonData)
    assert result.load() == {"array": [1, 2, 3]}


def test_load_json_with_bytes_input():
    """bytes 입력도 JsonData로 변환"""
    json_bytes = b'{"test":true}'
    result = load_value("json", json_bytes)
    assert isinstance(result, JsonData)


def test_load_str_conversion_without_check():
    """check_primitive_conversion=False이면 원본 반환"""
    result = load_value("str", "test", check_primitive_conversion=False)
    assert result == "test"


def test_load_str_conversion_with_check():
    """check_primitive_conversion=True이고 타입이 맞으면 원본 반환"""
    result = load_value("str", "test", check_primitive_conversion=True)
    assert result == "test"


def test_load_int_conversion_with_matching_type():
    """정수 타입이 맞으면 원본 반환"""
    result = load_value("int", 42, check_primitive_conversion=True)
    assert result == 42


def test_load_float_conversion_with_matching_type():
    """부동소수점 타입이 맞으면 원본 반환"""
    result = load_value("float", 3.14, check_primitive_conversion=True)
    assert result == 3.14


def test_load_bool_conversion_with_int():
    """'bool' conversion은 int를 bool로 변환"""
    assert load_value("bool", 1, check_primitive_conversion=True) is True
    assert load_value("bool", 0, check_primitive_conversion=True) is False


def test_load_bytes_conversion_with_matching_type():
    """bytes 타입이 맞으면 원본 반환"""
    test_bytes = b"data"
    result = load_value("bytes", test_bytes, check_primitive_conversion=True)
    assert result == test_bytes


def test_load_mismatched_type_raises_value_error():
    """타입이 맞지 않으면 ValueError 발생"""
    with pytest.raises(ValueError, match="Invalid type"):
        load_value("int", "not an int", check_primitive_conversion=True)


def test_load_unknown_conversion_raises_value_error():
    """알 수 없는 conversion은 ValueError 발생"""
    with pytest.raises(ValueError, match="unknown conversion"):
        load_value("unknown_conv", "value", check_primitive_conversion=True)  # type: ignore


def test_load_value_bool_with_non_integer():
    """bool conversion에 정수가 아닌 타입 전달 시 원본 반환 (check=False)"""
    result = load_value("bool", "string", check_primitive_conversion=False)
    assert result == "string"


# ===== get_conversion_query_value 테스트 =====


def test_get_conversion_for_string_without_primitive():
    """문자열, primitive_conversion=False"""
    conversion, query, value = get_conversion_query_value("test", primitive_conversion=False)
    assert conversion is None
    assert query == "?"
    assert value == "test"


def test_get_conversion_for_string_with_primitive():
    """문자열, primitive_conversion=True"""
    conversion, query, value = get_conversion_query_value("test", primitive_conversion=True)
    assert conversion == "str"
    assert query == "?"
    assert value == "test"


def test_get_conversion_for_integer_with_primitive():
    """정수, primitive_conversion=True"""
    conversion, query, value = get_conversion_query_value(42, primitive_conversion=True)
    assert conversion == "int"
    assert query == "?"
    assert value == 42


def test_get_conversion_for_float_with_primitive():
    """부동소수점, primitive_conversion=True"""
    conversion, query, value = get_conversion_query_value(3.14, primitive_conversion=True)
    assert conversion == "float"
    assert query == "?"
    assert value == 3.14


def test_get_conversion_for_bool_with_primitive():
    """불린, primitive_conversion=True"""
    conversion, query, value = get_conversion_query_value(True, primitive_conversion=True)
    assert conversion == "bool"
    assert query == "?"
    assert value is True


def test_get_conversion_for_bytes_with_primitive():
    """bytes, primitive_conversion=True"""
    test_bytes = b"data"
    conversion, query, value = get_conversion_query_value(test_bytes, primitive_conversion=True)
    assert conversion == "bytes"
    assert query == "?"
    assert value == test_bytes


def test_get_conversion_for_json_data():
    """JsonData with 'json' conversion"""
    json_data = JsonData(data={"key": "value"}, conversion="json")
    conversion, query, value = get_conversion_query_value(json_data)
    assert conversion == "json"
    assert query == "json(?)"
    assert value == '{"key":"value"}'


def test_get_conversion_for_jsonb_data():
    """JsonData with 'jsonb' conversion"""
    json_data = JsonData(data={"key": "value"}, conversion="jsonb")
    conversion, query, value = get_conversion_query_value(json_data)
    assert conversion == "json"  # Note: spec에서 'json'으로 반환됨
    assert query == "json(?)"


def test_get_conversion_query_with_jsonb_explicit():
    """명시적으로 jsonb conversion을 지정한 경우"""
    json_data = JsonData(data={"test": 123}, conversion="jsonb")
    conversion, query, value = get_conversion_query_value(json_data, conversion="jsonb")
    assert conversion == "jsonb"
    assert query == "jsonb(?)"
    assert isinstance(value, str)
    assert "test" in value  # type: ignore


def test_explicit_conversion_parameter():
    """명시적 conversion 파라미터 제공"""
    conversion, query, value = get_conversion_query_value("test", conversion="str", primitive_conversion=True)
    assert conversion == "str"
    assert query == "CAST(? AS TEXT)"


def test_explicit_conversion_with_cast_for_int():
    """명시적 int conversion은 CAST 쿼리 생성"""
    conversion, query, value = get_conversion_query_value(42, conversion="int")
    assert conversion == "int"
    assert query == "CAST(? AS INTEGER)"
    assert value == 42


def test_explicit_conversion_with_cast_for_float():
    """명시적 float conversion은 CAST 쿼리 생성"""
    conversion, query, value = get_conversion_query_value(3.14, conversion="float")
    assert conversion == "float"
    assert query == "CAST(? AS REAL)"
    assert value == 3.14


def test_explicit_conversion_with_cast_for_bool():
    """명시적 bool conversion은 CAST 쿼리 생성"""
    conversion, query, value = get_conversion_query_value(True, conversion="bool")
    assert conversion == "bool"
    assert query == "CAST(? AS INTEGER)"
    assert value is True


def test_explicit_conversion_with_cast_for_bytes():
    """명시적 bytes conversion은 CAST 쿼리 생성"""
    conversion, query, value = get_conversion_query_value(b"data", conversion="bytes")
    assert conversion == "bytes"
    assert query == "CAST(? AS BLOB)"
    assert value == b"data"


# ===== get_primitive_conversion 테스트 =====


def test_primitive_conversion_for_string():
    """문자열의 primitive conversion은 'str'"""
    result = get_primitive_conversion("test")
    assert result == "str"


def test_primitive_conversion_for_integer():
    """정수의 primitive conversion은 'int'"""
    result = get_primitive_conversion(42)
    assert result == "int"


def test_primitive_conversion_for_float():
    """부동소수점의 primitive conversion은 'float'"""
    result = get_primitive_conversion(3.14)
    assert result == "float"


def test_primitive_conversion_for_bool():
    """불린의 primitive conversion은 'bool'"""
    result = get_primitive_conversion(True)
    assert result == "bool"


def test_primitive_conversion_for_bytes():
    """bytes의 primitive conversion은 'bytes'"""
    result = get_primitive_conversion(b"data")
    assert result == "bytes"


def test_primitive_conversion_for_json_data():
    """JsonData의 primitive conversion은 해당 conversion type"""
    json_data = JsonData(data={}, conversion="json")
    result = get_primitive_conversion(json_data)
    assert result == "json"


def test_primitive_conversion_for_invalid_type_raises():
    """지원하지 않는 타입은 ValueError 발생"""
    with pytest.raises(ValueError, match="Invalid type to convert"):
        get_primitive_conversion(object())  # type: ignore


# ===== 엣지 케이스 및 경계 조건 테스트 =====


def test_very_large_integer():
    """매우 큰 정수 처리"""
    large_int = 10**100
    result = dump_bytes_value(large_int)
    assert result == str(large_int).encode()


def test_very_small_float():
    """매우 작은 부동소수점 처리"""
    small_float = 1e-100
    result = dump_bytes_value(small_float)
    assert b"e-" in result or b"E-" in result


def test_empty_string():
    """빈 문자열 처리"""
    result = dump_bytes_value("")
    assert result == b""


def test_zero_values():
    """0 값들 처리"""
    assert dump_bytes_value(0) == b"0"
    assert dump_bytes_value(0.0) == b"0.0"


def test_special_float_values():
    """특수 부동소수점 값 처리"""
    import math
    assert b"inf" in dump_bytes_value(math.inf).lower()
    assert b"nan" in dump_bytes_value(math.nan).lower()


def test_unicode_edge_cases():
    """유니코드 엣지 케이스"""
    # 이모지
    emoji = "😀🎉"
    result = dump_bytes_value(emoji)
    assert load_bytes_value("str", result) == emoji

    # 다양한 언어
    multilang = "Hello 안녕 こんにちは مرحبا"
    result = dump_bytes_value(multilang)
    assert load_bytes_value("str", result) == multilang


# ===== 라운드트립 테스트 =====


def test_string_roundtrip():
    """문자열의 dump/load 라운드트립"""
    original = "test string 한글 😀"
    dumped = dump_bytes_value(original)
    loaded = load_bytes_value("str", dumped)
    assert loaded == original


def test_integer_roundtrip():
    """정수의 dump/load 라운드트립"""
    original = 12345
    dumped = dump_bytes_value(original)
    loaded = load_bytes_value("int", dumped, primitive_conversion=True)
    assert loaded == original


def test_negative_integer_roundtrip():
    """음수 정수의 dump/load 라운드트립"""
    original = -9876
    dumped = dump_bytes_value(original)
    loaded = load_bytes_value("int", dumped, primitive_conversion=True)
    assert loaded == original


def test_float_roundtrip():
    """부동소수점의 dump/load 라운드트립"""
    original = 3.14159
    dumped = dump_bytes_value(original)
    loaded = load_bytes_value("float", dumped, primitive_conversion=True)
    assert loaded == original


def test_bool_true_roundtrip():
    """True의 dump/load 라운드트립"""
    original = True
    dumped = dump_bytes_value(original)
    loaded = load_bytes_value("bool", dumped)
    assert loaded is original


def test_bool_false_roundtrip():
    """False의 dump/load 라운드트립"""
    original = False
    dumped = dump_bytes_value(original)
    loaded = load_bytes_value("bool", dumped)
    assert loaded is original


def test_bytes_roundtrip():
    """bytes의 dump/load 라운드트립"""
    original = b"binary\x00\xff\xfe data"
    dumped = dump_bytes_value(original)
    loaded = load_bytes_value("bytes", dumped)
    assert loaded == original


def test_json_data_roundtrip():
    """JsonData의 dump/load 라운드트립"""
    original_data = {"key": "value", "nested": {"array": [1, 2, 3]}}
    json_obj = JsonData(data=original_data)
    dumped = dump_bytes_value(json_obj)
    loaded = load_value("json", dumped.decode("utf-8"))
    assert isinstance(loaded, JsonData)
    assert loaded.load() == original_data


def test_none_roundtrip():
    """None의 dump/load 라운드트립"""
    original = None
    dumped = dump_bytes_value(original)
    loaded = load_bytes_value("null", dumped)
    assert loaded is original


def test_large_integer_roundtrip():
    """매우 큰 정수의 라운드트립"""
    original = 10**50
    dumped = dump_bytes_value(original)
    loaded = load_bytes_value("int", dumped, primitive_conversion=True)
    assert loaded == original


def test_empty_string_roundtrip():
    """빈 문자열의 라운드트립"""
    original = ""
    dumped = dump_bytes_value(original)
    loaded = load_bytes_value("str", dumped)
    assert loaded == original
