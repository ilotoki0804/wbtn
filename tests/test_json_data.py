"""
JsonData 클래스에 대한 포괄적인 테스트
JSON 데이터 래핑, dump/load, equality 비교 등을 테스트합니다.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbtn._json_data import JsonData


# ===== 기본 생성 및 초기화 테스트 =====


def test_create_json_data_from_data():
    """data 파라미터로 JsonData 생성"""
    json_data = JsonData(data={"key": "value"})
    assert json_data.loaded is True
    assert json_data.stored == {"key": "value"}


def test_create_json_data_from_raw():
    """raw 파라미터로 JsonData 생성"""
    json_data = JsonData(raw='{"key":"value"}')
    assert json_data.loaded is False
    assert json_data.stored == '{"key":"value"}'


def test_create_with_both_data_and_raw_raises_error():
    """data와 raw를 동시에 제공하면 ValueError 발생"""
    with pytest.raises(ValueError, match="Only data or raw should be provided"):
        JsonData(data={"key": "value"}, raw='{"key":"value"}')  # type: ignore


def test_create_with_json_conversion():
    """json conversion type으로 생성"""
    json_data = JsonData(data=[], conversion="json")
    assert json_data.conversion == "json"


def test_create_with_jsonb_conversion():
    """jsonb conversion type으로 생성"""
    json_data = JsonData(data=[], conversion="jsonb")
    assert json_data.conversion == "jsonb"


def test_from_data_classmethod():
    """from_data classmethod로 생성"""
    json_data = JsonData.from_data({"test": 123})
    assert json_data.loaded is True
    assert json_data.load() == {"test": 123}


def test_from_data_with_conversion():
    """from_data에 conversion 파라미터 전달"""
    json_data = JsonData.from_data([1, 2, 3], conversion="jsonb")
    assert json_data.conversion == "jsonb"


def test_from_raw_classmethod():
    """from_raw classmethod로 생성"""
    json_data = JsonData.from_raw('{"num":42}')
    assert json_data.loaded is False
    assert json_data.load() == {"num": 42}


def test_from_raw_with_conversion():
    """from_raw에 conversion 파라미터 전달"""
    json_data = JsonData.from_raw('[]', conversion="jsonb")
    assert json_data.conversion == "jsonb"


# ===== dump 메서드 테스트 =====


def test_dump_from_data_returns_json_string():
    """data에서 dump하면 JSON 문자열 반환"""
    json_data = JsonData(data={"key": "value"})
    result = json_data.dump()
    assert result == '{"key":"value"}'
    assert isinstance(result, str)


def test_dump_from_raw_returns_original_string():
    """raw에서 dump하면 원본 문자열 반환"""
    original = '{"key": "value", "number": 123}'
    json_data = JsonData(raw=original)
    result = json_data.dump()
    assert result == original


def test_dump_with_store_raw_caches_result():
    """store_raw=True로 dump하면 결과를 캐싱"""
    json_data = JsonData(data={"test": "data"})
    assert json_data.loaded is True

    result = json_data.dump(store_raw=True)

    assert json_data.loaded is False
    assert json_data.stored == result


def test_dump_complex_nested_structure():
    """복잡한 중첩 구조 dump"""
    complex_data = {
        "array": [1, 2, {"nested": True}],
        "object": {"deep": {"value": None}},
        "unicode": "한글 テスト"
    }
    json_data = JsonData(data=complex_data)
    result = json_data.dump()
    assert "한글" in result
    assert "nested" in result


def test_dump_preserves_json_format():
    """JSON 형식이 일관되게 유지됨 (no spaces, ensure_ascii=False)"""
    json_data = JsonData(data={"a": 1, "b": 2})
    result = json_data.dump()
    # 공백 없이 인코딩됨
    assert result == '{"a":1,"b":2}'


# ===== load 메서드 테스트 =====


def test_load_from_data_returns_original():
    """data에서 load하면 원본 반환"""
    original = {"test": [1, 2, 3]}
    json_data = JsonData(data=original)
    result = json_data.load()
    assert result == original


def test_load_from_raw_parses_json():
    """raw에서 load하면 JSON 파싱"""
    json_data = JsonData(raw='{"parsed": true, "number": 42}')
    result = json_data.load()
    assert result == {"parsed": True, "number": 42}


def test_load_with_copy_creates_deepcopy():
    """copy=True로 load하면 깊은 복사본 반환"""
    original = {"nested": {"list": [1, 2, 3]}}
    json_data = JsonData(data=original)
    result = json_data.load(copy=True)

    # 내용은 같지만 다른 객체
    assert result == original
    assert result is not original
    result["nested"]["list"].append(4)
    assert original["nested"]["list"] == [1, 2, 3]


def test_load_without_copy_returns_same_object():
    """copy=False로 load하면 같은 객체 반환"""
    original = {"data": "test"}
    json_data = JsonData(data=original)
    result = json_data.load(copy=False)
    assert result is original


def test_load_with_store_data_caches_result():
    """store_data=True로 load하면 결과를 캐싱"""
    json_data = JsonData(raw='{"cached": "value"}')
    assert json_data.loaded is False

    result = json_data.load(store_data=True)

    assert json_data.loaded is True
    assert json_data.stored == result


def test_load_various_json_types():
    """다양한 JSON 타입 load"""
    # Array
    assert JsonData(raw='[1, 2, 3]').load() == [1, 2, 3]
    # String
    assert JsonData(raw='"text"').load() == "text"
    # Number
    assert JsonData(raw='42').load() == 42
    # Boolean
    assert JsonData(raw='true').load() is True
    # Null
    assert JsonData(raw='null').load() is None


# ===== equality 비교 테스트 =====


def test_equality_same_raw_strings():
    """같은 raw 문자열을 가진 JsonData는 같음"""
    json1 = JsonData(raw='{"a":1}')
    json2 = JsonData(raw='{"a":1}')
    assert json1 == json2


def test_equality_same_data():
    """같은 data를 가진 JsonData는 같음"""
    json1 = JsonData(data={"a": 1, "b": 2})
    json2 = JsonData(data={"a": 1, "b": 2})
    assert json1 == json2


def test_equality_different_format_same_content():
    """포맷은 다르지만 내용이 같으면 같음"""
    json1 = JsonData(raw='{"a":1,"b":2}')
    json2 = JsonData(raw='{"b": 2, "a": 1}')  # 키 순서 다름, 공백 있음
    assert json1 == json2


def test_equality_data_vs_raw_same_content():
    """data와 raw가 같은 내용이면 같음"""
    json1 = JsonData(data={"test": True})
    json2 = JsonData(raw='{"test":true}')
    assert json1 == json2


def test_inequality_different_content():
    """내용이 다르면 다름"""
    json1 = JsonData(data={"a": 1})
    json2 = JsonData(data={"a": 2})
    assert json1 != json2


def test_equality_nested_structures():
    """중첩된 구조도 올바르게 비교"""
    json1 = JsonData(data={"nested": {"array": [1, 2, 3]}})
    json2 = JsonData(data={"nested": {"array": [1, 2, 3]}})
    assert json1 == json2


# ===== stored/loaded 상태 테스트 =====


def test_loaded_property_with_data():
    """data로 생성하면 loaded=True"""
    json_data = JsonData(data={})
    assert json_data.loaded is True


def test_loaded_property_with_raw():
    """raw로 생성하면 loaded=False"""
    json_data = JsonData(raw='{}')
    assert json_data.loaded is False


def test_stored_returns_data_when_loaded():
    """loaded 상태에서 stored는 data 반환"""
    data = {"key": "value"}
    json_data = JsonData(data=data)
    assert json_data.stored is data


def test_stored_returns_raw_when_not_loaded():
    """non-loaded 상태에서 stored는 raw 반환"""
    raw = '{"key":"value"}'
    json_data = JsonData(raw=raw)
    assert json_data.stored is raw


def test_state_transition_dump_with_store():
    """dump(store_raw=True)로 loaded → non-loaded 전환"""
    json_data = JsonData(data={"test": 1})
    assert json_data.loaded is True

    json_data.dump(store_raw=True)
    assert json_data.loaded is False


def test_state_transition_load_with_store():
    """load(store_data=True)로 non-loaded → loaded 전환"""
    json_data = JsonData(raw='{"test":1}')
    assert json_data.loaded is False

    json_data.load(store_data=True)
    assert json_data.loaded is True


# ===== 엣지 케이스 및 특수 케이스 테스트 =====


def test_empty_object():
    """빈 객체 처리"""
    json_data = JsonData(data={})
    assert json_data.dump() == '{}'
    assert json_data.load() == {}


def test_empty_array():
    """빈 배열 처리"""
    json_data = JsonData(data=[])
    assert json_data.dump() == '[]'
    assert json_data.load() == []


def test_unicode_content():
    """유니코드 문자 처리 (ensure_ascii=False)"""
    unicode_data = {"korean": "한글", "japanese": "日本語", "emoji": "🎉"}
    json_data = JsonData(data=unicode_data)
    dumped = json_data.dump()
    assert "한글" in dumped  # ensure_ascii=False이므로 유니코드 그대로
    assert "日本語" in dumped
    assert "🎉" in dumped


def test_large_nested_structure():
    """큰 중첩 구조 처리"""
    large_data = {
        f"key_{i}": {
            "nested": list(range(10)),
            "more": {"deep": f"value_{i}"}
        }
        for i in range(100)
    }
    json_data = JsonData(data=large_data)
    dumped = json_data.dump()
    loaded = JsonData(raw=dumped).load()
    assert loaded == large_data


def test_special_characters_in_strings():
    """특수 문자 처리"""
    special_data = {
        "quotes": 'He said "Hello"',
        "backslash": "path\\to\\file",
        "newline": "line1\nline2",
        "tab": "col1\tcol2"
    }
    json_data = JsonData(data=special_data)
    dumped = json_data.dump()
    loaded = JsonData(raw=dumped).load()
    assert loaded == special_data


def test_numeric_edge_cases():
    """숫자 엣지 케이스"""
    numeric_data = {
        "zero": 0,
        "negative": -123,
        "float": 3.14159,
        "scientific": 1.23e-10,
        "large": 10**100
    }
    json_data = JsonData(data=numeric_data)
    dumped = json_data.dump()
    loaded = JsonData(raw=dumped).load()
    assert loaded == numeric_data


def test_null_values():
    """null 값 처리"""
    data_with_null = {"value": None, "list": [None, 1, None]}
    json_data = JsonData(data=data_with_null)
    dumped = json_data.dump()
    assert "null" in dumped
    loaded = JsonData(raw=dumped).load()
    assert loaded == data_with_null


def test_boolean_values():
    """불린 값 처리"""
    bool_data = {"true_val": True, "false_val": False, "mixed": [True, False, True]}
    json_data = JsonData(data=bool_data)
    dumped = json_data.dump()
    loaded = JsonData(raw=dumped).load()
    assert loaded == bool_data


def test_mixed_type_array():
    """혼합 타입 배열"""
    mixed_array = [1, "string", True, None, {"obj": "value"}, [1, 2, 3]]
    json_data = JsonData(data=mixed_array)
    dumped = json_data.dump()
    loaded = JsonData(raw=dumped).load()
    assert loaded == mixed_array


def test_conversion_type_preservation():
    """conversion type이 보존됨"""
    json_data = JsonData(data={}, conversion="jsonb")
    assert json_data.conversion == "jsonb"
    # dump/load 후에도 conversion type 유지
    json_data.dump(store_raw=True)
    assert json_data.conversion == "jsonb"
