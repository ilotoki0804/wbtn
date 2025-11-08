"""
WebtoonInfoManager에 대한 포괄적인 테스트
MutableMapping 인터페이스, system key 보호, conversion 처리 등을 테스트합니다.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbtn import Webtoon
from wbtn._json_data import JsonData


# ===== MutableMapping 인터페이스 테스트 =====


def test_info_len(webtoon_instance: Webtoon):
    """len() 연산자로 항목 수 확인"""
    initial_len = len(webtoon_instance.info)
    webtoon_instance.info["new_key"] = "value"
    assert len(webtoon_instance.info) == initial_len + 1


def test_info_getitem(webtoon_instance: Webtoon):
    """__getitem__으로 값 가져오기"""
    webtoon_instance.info["test_key"] = "test_value"
    assert webtoon_instance.info["test_key"] == "test_value"


def test_info_setitem(webtoon_instance: Webtoon):
    """__setitem__으로 값 설정"""
    webtoon_instance.info["new_key"] = "new_value"
    assert webtoon_instance.info.get("new_key") == "new_value"


def test_info_delitem(webtoon_instance: Webtoon):
    """__delitem__으로 값 삭제"""
    webtoon_instance.info["deletable"] = "value"
    del webtoon_instance.info["deletable"]
    assert "deletable" not in webtoon_instance.info


def test_info_contains(webtoon_instance: Webtoon):
    """'in' 연산자로 키 존재 확인"""
    webtoon_instance.info["exists"] = "yes"
    assert "exists" in webtoon_instance.info
    assert "does_not_exist" not in webtoon_instance.info


def test_info_iter(webtoon_instance: Webtoon):
    """iterator로 키 순회"""
    webtoon_instance.info["key1"] = "val1"
    webtoon_instance.info["key2"] = "val2"

    keys = list(webtoon_instance.info)
    assert "key1" in keys
    assert "key2" in keys


def test_info_items(webtoon_instance: Webtoon):
    """items()로 (키, 값) 쌍 순회"""
    webtoon_instance.info["item_key"] = "item_value"

    items = dict(webtoon_instance.info.items())
    assert items["item_key"] == "item_value"


def test_info_values(webtoon_instance: Webtoon):
    """values()로 값들 순회"""
    webtoon_instance.info["val_key"] = "val_value"

    values = list(webtoon_instance.info.values())
    assert "val_value" in values


def test_info_keys(webtoon_instance: Webtoon):
    """keys()로 키들 순회"""
    webtoon_instance.info["key_test"] = "value"

    keys = list(webtoon_instance.info.keys())
    assert "key_test" in keys


# ===== get 및 set 메서드 테스트 =====


def test_get_existing_key(webtoon_instance: Webtoon):
    """존재하는 키를 get으로 가져오기"""
    webtoon_instance.info.set("existing", "value")
    result = webtoon_instance.info.get("existing")
    assert result == "value"


def test_get_nonexistent_key_with_default(webtoon_instance: Webtoon):
    """존재하지 않는 키를 get하면 기본값 반환"""
    result = webtoon_instance.info.get("nonexistent", "default")
    assert result == "default"


def test_get_nonexistent_key_without_default_raises(webtoon_instance: Webtoon):
    """존재하지 않는 키를 기본값 없이 get하면 None 반환"""
    assert webtoon_instance.info.get("nonexistent") is None


def test_set_new_value(webtoon_instance: Webtoon):
    """새 값 설정"""
    webtoon_instance.info.set("new", "value")
    assert webtoon_instance.info.get("new") == "value"


def test_set_overwrites_existing_value(webtoon_instance: Webtoon):
    """기존 값을 덮어쓰기"""
    webtoon_instance.info.set("overwrite", "old")
    webtoon_instance.info.set("overwrite", "new")
    assert webtoon_instance.info.get("overwrite") == "new"


def test_setdefault_sets_if_not_exists(webtoon_instance: Webtoon):
    """setdefault는 키가 없을 때만 설정"""
    webtoon_instance.info.setdefault("default_key", "default_value")
    assert webtoon_instance.info.get("default_key") == "default_value"


def test_setdefault_does_not_overwrite(webtoon_instance: Webtoon):
    """setdefault는 기존 값을 덮어쓰지 않음"""
    webtoon_instance.info.set("existing_default", "original")
    webtoon_instance.info.setdefault("existing_default", "new")
    assert webtoon_instance.info.get("existing_default") == "original"


# ===== delete 및 pop 메서드 테스트 =====


def test_delete_existing_key(webtoon_instance: Webtoon):
    """존재하는 키 삭제"""
    webtoon_instance.info.set("delete_me", "value")
    webtoon_instance.info.delete("delete_me")
    assert "delete_me" not in webtoon_instance.info


def test_delete_nonexistent_key_raises(webtoon_instance: Webtoon):
    """존재하지 않는 키 삭제 시 KeyError"""
    with pytest.raises(KeyError):
        webtoon_instance.info.delete("does_not_exist")


def test_pop_existing_key_returns_value(webtoon_instance: Webtoon):
    """pop으로 키를 삭제하고 값 반환"""
    webtoon_instance.info.set("pop_me", "pop_value")
    result = webtoon_instance.info.pop("pop_me")
    assert result == "pop_value"
    assert "pop_me" not in webtoon_instance.info


def test_pop_nonexistent_key_with_default(webtoon_instance: Webtoon):
    """pop에서 존재하지 않는 키를 기본값과 함께 사용"""
    result = webtoon_instance.info.pop("nonexistent", "default")
    assert result == "default"


def test_pop_nonexistent_key_without_default_raises(webtoon_instance: Webtoon):
    """pop에서 존재하지 않는 키를 기본값 없이 사용 시 KeyError"""
    with pytest.raises(KeyError):
        webtoon_instance.info.pop("nonexistent")


def test_clear_removes_all_non_system_keys(webtoon_instance: Webtoon):
    """clear()는 시스템 키를 제외한 모든 키 삭제"""
    webtoon_instance.info["user_key1"] = "value1"
    webtoon_instance.info["user_key2"] = "value2"

    webtoon_instance.info.clear()

    assert "user_key1" not in webtoon_instance.info
    assert "user_key2" not in webtoon_instance.info
    # 시스템 키는 유지됨
    assert "sys_agent" in webtoon_instance.info


def test_clear_with_delete_system_removes_all(webtoon_instance: Webtoon):
    """clear(delete_system=True)는 시스템 키도 삭제"""
    webtoon_instance.info["user_key"] = "value"

    webtoon_instance.info.clear(system=True)

    assert "user_key" not in webtoon_instance.info
    assert "sys_agent" not in webtoon_instance.info


# ===== system key 보호 테스트 =====


def test_cannot_delete_system_key_by_default(webtoon_instance: Webtoon):
    """기본적으로 시스템 키는 삭제할 수 없음"""
    with pytest.raises(KeyError, match="Cannot modify or delete"):
        webtoon_instance.info.delete("sys_agent")


def test_can_delete_system_key_with_flag(webtoon_instance: Webtoon):
    """delete_system=True 플래그로 시스템 키 삭제 가능"""
    webtoon_instance.info.delete("sys_agent", system=True)
    assert "sys_agent" not in webtoon_instance.info


def test_cannot_pop_system_key_by_default(webtoon_instance: Webtoon):
    """기본적으로 시스템 키는 pop할 수 없음"""
    with pytest.raises(KeyError, match="Cannot modify or delete"):
        webtoon_instance.info.pop("sys_agent_version")


def test_can_pop_system_key_with_flag(webtoon_instance: Webtoon):
    """delete_system=True 플래그로 시스템 키 pop 가능"""
    value = webtoon_instance.info.pop("sys_agent_version", system=True)
    assert value is not None
    assert "sys_agent_version" not in webtoon_instance.info


def test_can_overwrite_system_key(webtoon_instance: Webtoon):
    """시스템 키는 system=True로 덮어쓰기 가능"""
    original = webtoon_instance.info["sys_agent"]
    webtoon_instance.info.set("sys_agent", "modified", system=True)
    assert webtoon_instance.info["sys_agent"] == "modified"
    assert webtoon_instance.info["sys_agent"] != original


# ===== conversion 처리 테스트 =====


def test_store_and_retrieve_string(webtoon_instance: Webtoon):
    """문자열 저장 및 조회"""
    webtoon_instance.info["string_key"] = "string value"
    result = webtoon_instance.info["string_key"]
    assert result == "string value"
    assert isinstance(result, str)


def test_store_and_retrieve_integer(webtoon_instance: Webtoon):
    """정수 저장 및 조회"""
    webtoon_instance.info["int_key"] = 42
    result = webtoon_instance.info["int_key"]
    assert result == 42
    assert isinstance(result, int)


def test_store_and_retrieve_float(webtoon_instance: Webtoon):
    """부동소수점 저장 및 조회"""
    webtoon_instance.info["float_key"] = 3.14159
    result = webtoon_instance.info["float_key"]
    assert result == 3.14159
    assert isinstance(result, float)


def test_store_and_retrieve_bool(webtoon_instance: Webtoon):
    """불린 저장 및 조회"""
    webtoon_instance.info["bool_key"] = True
    result = webtoon_instance.info["bool_key"]
    assert result is True
    assert isinstance(result, bool)


def test_store_and_retrieve_bytes(webtoon_instance: Webtoon):
    """bytes 저장 및 조회"""
    test_bytes = b"binary data"
    webtoon_instance.info["bytes_key"] = test_bytes
    result = webtoon_instance.info["bytes_key"]
    assert result == test_bytes
    assert isinstance(result, bytes)


def test_store_and_retrieve_none(webtoon_instance: Webtoon):
    """None 저장 및 조회"""
    webtoon_instance.info["none_key"] = None
    result = webtoon_instance.info["none_key"]
    assert result is None


def test_store_and_retrieve_json_data(webtoon_instance: Webtoon):
    """JsonData 저장 및 조회"""
    json_data = JsonData(data={"nested": {"value": [1, 2, 3]}})
    webtoon_instance.info["json_key"] = json_data
    result = webtoon_instance.info["json_key"]

    assert isinstance(result, JsonData)
    assert result.load() == {"nested": {"value": [1, 2, 3]}}


def test_get_conversion_for_stored_value(webtoon_instance: Webtoon):
    """저장된 값의 conversion type 확인"""
    webtoon_instance.info["test"] = "string"
    conversion = webtoon_instance.info.get_conversion("test")
    assert conversion is None  # primitive_conversion=False이므로 str은 conversion이 None


def test_get_conversion_for_json_value(webtoon_instance: Webtoon):
    """JsonData의 conversion type 확인"""
    webtoon_instance.info["json_test"] = JsonData(data=[1, 2, 3])
    conversion = webtoon_instance.info.get_conversion("json_test")
    assert conversion in ("json", "jsonb")


def test_get_conversion_for_nonexistent_key_raises(webtoon_instance: Webtoon):
    """존재하지 않는 키의 conversion 조회 시 KeyError"""
    with pytest.raises(KeyError):
        webtoon_instance.info.get_conversion("nonexistent")


# ===== 복합 데이터 타입 테스트 =====


def test_store_complex_json_structure(webtoon_instance: Webtoon):
    """복잡한 JSON 구조 저장"""
    complex_data = JsonData(data={
        "title": "Test Webtoon",
        "authors": ["Author1", "Author2"],
        "metadata": {
            "chapters": 10,
            "rating": 4.5,
            "tags": ["action", "comedy"]
        }
    })
    webtoon_instance.info["complex"] = complex_data
    result = webtoon_instance.info["complex"]
    assert isinstance(result, JsonData)
    loaded = result.load()

    assert loaded["title"] == "Test Webtoon"
    assert loaded["authors"] == ["Author1", "Author2"]
    assert loaded["metadata"]["chapters"] == 10


def test_unicode_values(webtoon_instance: Webtoon):
    """유니코드 값 처리"""
    webtoon_instance.info["korean"] = "한글 제목"
    webtoon_instance.info["japanese"] = "日本語"
    webtoon_instance.info["emoji"] = "🎉📚"

    assert webtoon_instance.info["korean"] == "한글 제목"
    assert webtoon_instance.info["japanese"] == "日本語"
    assert webtoon_instance.info["emoji"] == "🎉📚"


# ===== 동시성 및 트랜잭션 테스트 =====


def test_multiple_operations_in_sequence(webtoon_instance: Webtoon):
    """연속된 여러 작업"""
    webtoon_instance.info["key1"] = "value1"
    webtoon_instance.info["key2"] = "value2"
    webtoon_instance.info["key1"] = "updated1"
    del webtoon_instance.info["key2"]

    assert webtoon_instance.info["key1"] == "updated1"
    assert "key2" not in webtoon_instance.info


def test_persist_across_connections(tmp_path: Path):
    """연결 간 데이터 지속성"""
    db_path = tmp_path / "persist.wbtn"

    # 첫 번째 연결에서 데이터 저장
    with Webtoon(db_path) as webtoon:
        webtoon.info["persistent"] = "data"
        webtoon.info["number"] = 12345

    # 두 번째 연결에서 데이터 확인
    with Webtoon(db_path) as webtoon:
        assert webtoon.info["persistent"] == "data"
        assert webtoon.info["number"] == 12345


# ===== 엣지 케이스 테스트 =====


def test_empty_string_key(webtoon_instance: Webtoon):
    """빈 문자열 키 사용"""
    webtoon_instance.info[""] = "empty key"
    assert webtoon_instance.info[""] == "empty key"


def test_very_long_key(webtoon_instance: Webtoon):
    """매우 긴 키 사용"""
    long_key = "k" * 1000
    webtoon_instance.info[long_key] = "long key value"
    assert webtoon_instance.info[long_key] == "long key value"


def test_very_long_value(webtoon_instance: Webtoon):
    """매우 긴 값 저장"""
    long_value = "v" * 10000
    webtoon_instance.info["long_value"] = long_value
    result = webtoon_instance.info["long_value"]
    assert result == long_value


def test_special_characters_in_key(webtoon_instance: Webtoon):
    """특수 문자가 포함된 키"""
    special_keys = ["key with spaces", "key/with/slashes", "key\\backslash", "key\ttab"]
    for key in special_keys:
        webtoon_instance.info[key] = f"value for {key}"
        assert webtoon_instance.info[key] == f"value for {key}"
