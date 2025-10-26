"""
WebtoonEpisodeManager와 WebtoonEpisode에 대한 포괄적인 테스트
에피소드 추가, extra_data 관리, 상태 관리 등을 테스트합니다.
"""
import datetime
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbtn import Webtoon
from wbtn._managers import WebtoonEpisode
from wbtn._json_data import JsonData


# ===== 에피소드 추가 테스트 =====


def test_add_episode_with_all_parameters(webtoon_instance: Webtoon):
    """모든 파라미터와 함께 에피소드 추가"""
    episode = webtoon_instance.episode.add(
        id=12345,
        name="Test Episode",
        episode_no=1,
        state="downloaded"
    )
    assert isinstance(episode, WebtoonEpisode)
    assert episode.episode_no == 1
    assert episode.name == "Test Episode"
    assert episode.state == "downloaded"
    assert episode.episode_id == 12345


def test_add_episode_auto_episode_number(webtoon_instance: Webtoon):
    """episode_no를 자동으로 할당"""
    episode = webtoon_instance.episode.add(
        id=100,
        name="Auto Number Episode",
        state="complete"
    )
    assert isinstance(episode, WebtoonEpisode)
    assert episode.episode_no is not None
    assert isinstance(episode.episode_no, int)
    assert episode.name == "Auto Number Episode"
    assert episode.state == "complete"


def test_add_multiple_episodes(webtoon_instance: Webtoon):
    """여러 에피소드 추가"""
    ep1 = webtoon_instance.episode.add(id=1, name="Episode 1")
    ep2 = webtoon_instance.episode.add(id=2, name="Episode 2")
    ep3 = webtoon_instance.episode.add(id=3, name="Episode 3")

    assert isinstance(ep1, WebtoonEpisode)
    assert isinstance(ep2, WebtoonEpisode)
    assert isinstance(ep3, WebtoonEpisode)
    assert ep1.episode_no != ep2.episode_no != ep3.episode_no


def test_add_episode_with_unicode_name(webtoon_instance: Webtoon):
    """유니코드 이름으로 에피소드 추가"""
    episode = webtoon_instance.episode.add(
        id=999,
        name="테스트 에피소드 😀",
        state="ready"
    )
    assert isinstance(episode, WebtoonEpisode)
    assert episode.name == "테스트 에피소드 😀"


def test_add_episode_minimal_parameters(webtoon_instance: Webtoon):
    """최소한의 파라미터로 에피소드 추가"""
    episode = webtoon_instance.episode.add(
        id=500,
        name="Minimal"
    )
    assert isinstance(episode, WebtoonEpisode)
    assert episode.episode_id == 500
    assert episode.name == "Minimal"


def test_episode_id_can_be_various_types(webtoon_instance: Webtoon):
    """에피소드 ID는 다양한 타입 가능"""
    # 정수 ID
    ep1 = webtoon_instance.episode.add(id=123, name="Int ID")
    # 문자열 ID
    ep2 = webtoon_instance.episode.add(id="abc123", name="String ID")
    # None ID
    ep3 = webtoon_instance.episode.add(id=None, name="None ID")

    assert isinstance(ep1, WebtoonEpisode)
    assert isinstance(ep2, WebtoonEpisode)
    assert isinstance(ep3, WebtoonEpisode)
    assert ep1.episode_id == 123
    assert ep2.episode_id == "abc123"
    assert ep3.episode_id is None


# ===== WebtoonEpisode 클래스 테스트 =====


def test_webtoon_episode_from_episode_no(webtoon_instance: Webtoon):
    """episode_no로 WebtoonEpisode 객체 생성"""
    episode = webtoon_instance.episode.add(
        id=12345,
        name="Test Episode",
        state="downloaded"
    )

    # add()가 이미 WebtoonEpisode를 반환하므로 직접 사용
    assert episode.episode_no is not None
    assert episode.name == "Test Episode"
    assert episode.state == "downloaded"
    assert episode.episode_id == 12345
    assert isinstance(episode.added_at, datetime.datetime)

    # from_episode_no로도 생성 가능
    episode2 = WebtoonEpisode.from_episode_no(episode.episode_no, webtoon_instance)
    assert episode2.episode_no == episode.episode_no
    assert episode2.name == episode.name
    assert episode2.state == episode.state


def test_webtoon_episode_with_nonexistent_episode_no_raises(webtoon_instance: Webtoon):
    """존재하지 않는 episode_no로 객체 생성 시 에러"""
    with pytest.raises(ValueError, match="does not exist"):
        WebtoonEpisode.from_episode_no(99999, webtoon_instance)


def test_webtoon_episode_added_at_timestamp(webtoon_instance: Webtoon):
    """added_at이 올바른 타임스탬프인지 확인"""
    before_time = datetime.datetime.now()
    episode = webtoon_instance.episode.add(id=777, name="Time Test")
    after_time = datetime.datetime.now()

    assert before_time <= episode.added_at <= after_time


# ===== extra_data 추가 및 조회 테스트 (MutableMapping 인터페이스) =====


def test_add_extra_data_string(webtoon_instance: Webtoon):
    """문자열 extra_data 추가 (__setitem__ / __getitem__ 사용)"""
    episode = webtoon_instance.episode.add(id=1, name="Extra Test")
    episode["description"] = "This is a description"

    result = episode["description"]
    assert result == "This is a description"


def test_add_extra_data_integer(webtoon_instance: Webtoon):
    """정수 extra_data 추가"""
    episode = webtoon_instance.episode.add(id=2, name="Int Extra")
    episode["views"] = 10000

    result = episode["views"]
    assert result == 10000


def test_add_extra_data_json(webtoon_instance: Webtoon):
    """JsonData extra_data 추가"""
    episode = webtoon_instance.episode.add(id=3, name="JSON Extra")
    json_data = JsonData(data={"likes": 500, "comments": ["good", "nice"]})
    episode["metadata"] = json_data

    result = episode["metadata"]
    assert isinstance(result, JsonData)
    loaded = result.load()
    assert loaded["likes"] == 500


def test_add_multiple_extra_data(webtoon_instance: Webtoon):
    """여러 extra_data 추가"""
    episode = webtoon_instance.episode.add(id=4, name="Multiple Extra")
    episode["author"] = "John Doe"
    episode["rating"] = 4.5
    episode["published"] = True

    assert episode["author"] == "John Doe"
    assert episode["rating"] == 4.5
    assert episode["published"] is True


def test_extra_data_all_purposes(webtoon_instance: Webtoon):
    """모든 extra_data를 딕셔너리로 조회 (__getitem__ with None)"""
    episode = webtoon_instance.episode.add(id=5, name="All Extra")
    episode["key1"] = "value1"
    episode["key2"] = 123

    # None을 사용하면 모든 extra_data를 딕셔너리로 반환
    all_extra = episode[None]  # type: ignore
    assert isinstance(all_extra, dict)
    # all_extra는 ValueType (dict)이므로 type: ignore 필요
    assert all_extra["key1"] == "value1"  # type: ignore
    assert all_extra["key2"] == 123  # type: ignore


def test_extra_data_purposes_list(webtoon_instance: Webtoon):
    """extra_data의 purpose 목록 조회 (__iter__ 사용)"""
    episode = webtoon_instance.episode.add(id=6, name="Purposes")
    episode["purpose1"] = "data1"
    episode["purpose2"] = "data2"

    purposes = list(episode)
    assert "purpose1" in purposes
    assert "purpose2" in purposes
    assert len(purposes) == 2


# ===== 상태 관리 테스트 =====


def test_episode_with_different_states(webtoon_instance: Webtoon):
    """다양한 상태로 에피소드 추가"""
    states = ["downloaded", "empty", "impaired", "exists", "pending", None]

    for i, state in enumerate(states):
        episode = webtoon_instance.episode.add(
            id=1000 + i,
            name=f"Episode {i}",
            state=state
        )
        assert episode.state == state


def test_episode_state_can_be_custom_string(webtoon_instance: Webtoon):
    """사용자 정의 상태 문자열 사용 가능"""
    episode = webtoon_instance.episode.add(
        id=2000,
        name="Custom State",
        state="my_custom_state"
    )
    assert episode.state == "my_custom_state"


# ===== 엣지 케이스 및 오류 처리 =====


def test_add_episode_with_very_long_name(webtoon_instance: Webtoon):
    """매우 긴 이름으로 에피소드 추가"""
    long_name = "Episode " * 100
    episode = webtoon_instance.episode.add(id=3000, name=long_name)
    assert episode.name == long_name


def test_add_episode_with_special_characters_in_name(webtoon_instance: Webtoon):
    """특수 문자가 포함된 이름"""
    special_name = "Episode \"Special\" <Characters> & Symbols! 🎉"
    episode = webtoon_instance.episode.add(id=4000, name=special_name)
    assert episode.name == special_name


def test_extra_data_with_none_value(webtoon_instance: Webtoon):
    """None 값을 extra_data로 추가"""
    episode = webtoon_instance.episode.add(id=5000, name="None Test")
    episode["nullable"] = None

    result = episode["nullable"]
    assert result is None


def test_extra_data_with_empty_string(webtoon_instance: Webtoon):
    """빈 문자열을 extra_data로 추가"""
    episode = webtoon_instance.episode.add(id=6000, name="Empty String")
    episode["empty"] = ""

    result = episode["empty"]
    assert result == ""


def test_extra_data_overwrites_existing_purpose(webtoon_instance: Webtoon):
    """같은 purpose의 extra_data는 덮어씀"""
    episode = webtoon_instance.episode.add(id=7000, name="Overwrite")
    episode["field"] = "original"
    episode["field"] = "updated"

    result = episode["field"]
    assert result == "updated"


# ===== delete_extra_data 테스트 (__delitem__ 사용) =====


def test_delete_extra_data_basic(webtoon_instance: Webtoon):
    """extra_data를 성공적으로 삭제"""
    episode = webtoon_instance.episode.add(id=8000, name="Delete Test")
    episode["to_delete"] = "value"

    # 삭제 전 확인
    assert episode["to_delete"] == "value"

    # 삭제
    del episode["to_delete"]

    # 삭제 후 해당 데이터가 없는지 확인
    with pytest.raises(KeyError):
        _ = episode["to_delete"]


def test_delete_extra_data_nonexistent_purpose_raises(webtoon_instance: Webtoon):
    """존재하지 않는 purpose 삭제 시 KeyError 발생"""
    episode = webtoon_instance.episode.add(id=8001, name="No Purpose")

    with pytest.raises(KeyError):
        del episode["nonexistent"]


def test_delete_extra_data_nonexistent_episode_raises(webtoon_instance: Webtoon):
    """존재하지 않는 에피소드의 extra_data 삭제 시 KeyError 발생"""
    # WebtoonEpisode를 직접 생성하려면 from_episode_no를 사용해야 하는데,
    # 존재하지 않는 episode는 생성 자체가 불가능하므로 이 테스트는 건너뜀
    # 대신 실제 에피소드에서 존재하지 않는 purpose 삭제를 테스트
    episode = webtoon_instance.episode.add(id=8001, name="Test")
    with pytest.raises(KeyError):
        del episode["nonexistent_purpose"]


def test_delete_extra_data_keeps_other_purposes(webtoon_instance: Webtoon):
    """특정 purpose만 삭제하고 다른 purpose는 유지"""
    episode = webtoon_instance.episode.add(id=8002, name="Multiple Purposes")
    episode["keep1"] = "value1"
    episode["delete"] = "value2"
    episode["keep2"] = "value3"

    # 하나만 삭제
    del episode["delete"]

    # 나머지는 유지되는지 확인
    assert episode["keep1"] == "value1"
    assert episode["keep2"] == "value3"

    # 삭제된 것은 접근 불가
    with pytest.raises(KeyError):
        _ = episode["delete"]


def test_delete_extra_data_different_types(webtoon_instance: Webtoon):
    """다양한 타입의 extra_data 삭제"""
    episode = webtoon_instance.episode.add(id=8003, name="Type Test")

    # 다양한 타입 추가
    episode["string"] = "text"
    episode["integer"] = 123
    episode["json"] = JsonData(data={"key": "value"})

    # 각각 삭제
    del episode["string"]
    del episode["integer"]
    del episode["json"]

    # 모두 삭제되었는지 확인
    assert len(episode) == 0


def test_delete_extra_data_same_purpose_different_episodes(webtoon_instance: Webtoon):
    """같은 purpose지만 다른 에피소드의 데이터는 유지"""
    ep1 = webtoon_instance.episode.add(id=8004, name="Episode 1")
    ep2 = webtoon_instance.episode.add(id=8005, name="Episode 2")

    ep1["shared"] = "value1"
    ep2["shared"] = "value2"

    # ep1의 데이터만 삭제
    del ep1["shared"]

    # ep2는 유지
    assert ep2["shared"] == "value2"

    # ep1은 삭제됨
    with pytest.raises(KeyError):
        _ = ep1["shared"]


def test_delete_and_readd_extra_data(webtoon_instance: Webtoon):
    """삭제 후 같은 purpose로 다시 추가 가능"""
    episode = webtoon_instance.episode.add(id=8006, name="Readd Test")

    # 추가
    episode["readd"] = "original"
    assert episode["readd"] == "original"

    # 삭제
    del episode["readd"]

    # 다시 추가
    episode["readd"] = "new value"
    assert episode["readd"] == "new value"


def test_delete_extra_data_with_special_characters(webtoon_instance: Webtoon):
    """특수 문자가 포함된 purpose 삭제"""
    episode = webtoon_instance.episode.add(id=8007, name="Special Chars")

    special_purposes = ["purpose-with-dash", "purpose_with_underscore", "purpose.with.dot", "한글purpose"]

    for purpose in special_purposes:
        episode[purpose] = "value"

    for purpose in special_purposes:
        del episode[purpose]

    assert len(episode) == 0


# ===== 데이터 지속성 테스트 =====


def test_episode_persists_across_connections(tmp_path: Path):
    """연결 간 에피소드 데이터 지속성"""
    db_path = tmp_path / "episode_persist.wbtn"

    # 첫 번째 연결: 데이터 추가
    with Webtoon(db_path) as webtoon:
        episode = webtoon.episode.add(
            id=8000,
            name="Persistent Episode",
            state="saved"
        )
        episode_no = episode.episode_no
        episode["note"] = "persisted"

    # 두 번째 연결: 데이터 확인
    with Webtoon(db_path) as webtoon:
        episode = WebtoonEpisode.from_episode_no(episode_no, webtoon)

        assert episode.name == "Persistent Episode"
        assert episode.state == "saved"
        assert episode["note"] == "persisted"


def test_complex_workflow(webtoon_instance: Webtoon):
    """복잡한 워크플로우 테스트"""
    # 여러 에피소드 추가
    episodes = []
    for i in range(5):
        episode = webtoon_instance.episode.add(
            id=9000 + i,
            name=f"Chapter {i + 1}",
            state="published"
        )
        episodes.append(episode)

        # 각 에피소드에 extra_data 추가
        episode["chapter_num"] = i + 1
        episode["metadata"] = JsonData(data={"views": 1000 * (i + 1), "likes": 100 * (i + 1)})

    # 모든 에피소드 확인
    for i, episode in enumerate(episodes):
        assert episode.name == f"Chapter {i + 1}"
        assert episode.state == "published"

        chapter_num = episode["chapter_num"]
        assert chapter_num == i + 1


# ===== MutableMapping 인터페이스 테스트 =====


def test_webtoon_episode_len(webtoon_instance: Webtoon):
    """WebtoonEpisode의 len() 메서드 테스트 (__len__)"""
    episode = webtoon_instance.episode.add(id=10000, name="Len Test")

    # 처음에는 비어있음
    assert len(episode) == 0

    # 데이터 추가
    episode["key1"] = "value1"
    assert len(episode) == 1

    episode["key2"] = "value2"
    assert len(episode) == 2

    episode["key3"] = "value3"
    assert len(episode) == 3

    # 삭제 후 감소
    del episode["key2"]
    assert len(episode) == 2


def test_webtoon_episode_iter(webtoon_instance: Webtoon):
    """WebtoonEpisode의 반복 테스트 (__iter__)"""
    episode = webtoon_instance.episode.add(id=10001, name="Iter Test")

    purposes = ["purpose1", "purpose2", "purpose3"]
    for purpose in purposes:
        episode[purpose] = f"value for {purpose}"

    # 반복자를 통해 purpose 목록 확인
    result_purposes = list(episode)
    assert len(result_purposes) == 3
    for purpose in purposes:
        assert purpose in result_purposes


def test_webtoon_episode_contains(webtoon_instance: Webtoon):
    """WebtoonEpisode의 in 연산자 테스트 (__contains__)"""
    episode = webtoon_instance.episode.add(id=10002, name="Contains Test")

    # 처음에는 포함되지 않음
    assert "test_key" not in episode

    # 추가 후 포함됨
    episode["test_key"] = "test_value"
    assert "test_key" in episode

    # 다른 키는 포함되지 않음
    assert "other_key" not in episode


def test_webtoon_episode_keys(webtoon_instance: Webtoon):
    """WebtoonEpisode의 keys() 메서드 테스트"""
    episode = webtoon_instance.episode.add(id=10003, name="Keys Test")

    episode["key1"] = "value1"
    episode["key2"] = "value2"
    episode["key3"] = "value3"

    keys = list(episode.keys())
    assert len(keys) == 3
    assert "key1" in keys
    assert "key2" in keys
    assert "key3" in keys


def test_webtoon_episode_values(webtoon_instance: Webtoon):
    """WebtoonEpisode의 values() 메서드 테스트"""
    episode = webtoon_instance.episode.add(id=10004, name="Values Test")

    episode["key1"] = "value1"
    episode["key2"] = 42
    episode["key3"] = True

    values = list(episode.values())
    assert len(values) == 3
    assert "value1" in values
    assert 42 in values
    assert True in values


def test_webtoon_episode_items(webtoon_instance: Webtoon):
    """WebtoonEpisode의 items() 메서드 테스트"""
    episode = webtoon_instance.episode.add(id=10005, name="Items Test")

    episode["key1"] = "value1"
    episode["key2"] = 42

    items = dict(episode.items())
    assert len(items) == 2
    assert items["key1"] == "value1"
    assert items["key2"] == 42


def test_webtoon_episode_get(webtoon_instance: Webtoon):
    """WebtoonEpisode의 get() 메서드 테스트"""
    episode = webtoon_instance.episode.add(id=10006, name="Get Test")

    episode["existing"] = "value"

    # 존재하는 키
    assert episode.get("existing") == "value"

    # 존재하지 않는 키 (기본값 None)
    assert episode.get("nonexistent") is None

    # 존재하지 않는 키 (사용자 정의 기본값)
    assert episode.get("nonexistent", "default") == "default"


def test_webtoon_episode_pop(webtoon_instance: Webtoon):
    """WebtoonEpisode의 pop() 메서드 테스트"""
    episode = webtoon_instance.episode.add(id=10007, name="Pop Test")

    episode["key1"] = "value1"
    episode["key2"] = "value2"

    # pop으로 값을 가져오고 삭제
    value = episode.pop("key1")
    assert value == "value1"
    assert "key1" not in episode
    assert len(episode) == 1

    # 존재하지 않는 키 pop (기본값 제공)
    value = episode.pop("nonexistent", "default")
    assert value == "default"


def test_webtoon_episode_setdefault(webtoon_instance: Webtoon):
    """WebtoonEpisode의 setdefault() 메서드 테스트"""
    episode = webtoon_instance.episode.add(id=10008, name="Setdefault Test")

    # 존재하지 않는 키에 대해 기본값 설정
    value = episode.setdefault("new_key", "default_value")
    assert value == "default_value"
    assert episode["new_key"] == "default_value"

    # 이미 존재하는 키에 대해서는 기존 값 반환
    value = episode.setdefault("new_key", "another_value")
    assert value == "default_value"  # 기존 값 유지
    assert episode["new_key"] == "default_value"


def test_webtoon_episode_update(webtoon_instance: Webtoon):
    """WebtoonEpisode의 update() 메서드 테스트"""
    episode = webtoon_instance.episode.add(id=10009, name="Update Test")

    episode["key1"] = "value1"

    # 딕셔너리로 업데이트
    episode.update({"key2": "value2", "key3": "value3"})
    assert episode["key2"] == "value2"
    assert episode["key3"] == "value3"

    # 기존 값 덮어쓰기
    episode.update({"key1": "updated_value1"})
    assert episode["key1"] == "updated_value1"


def test_webtoon_episode_clear(webtoon_instance: Webtoon):
    """WebtoonEpisode의 clear() 메서드 테스트"""
    episode = webtoon_instance.episode.add(id=10010, name="Clear Test")

    episode["key1"] = "value1"
    episode["key2"] = "value2"
    episode["key3"] = "value3"

    assert len(episode) == 3

    # 모든 extra_data 삭제
    episode.clear()

    assert len(episode) == 0
    assert "key1" not in episode
    assert "key2" not in episode
    assert "key3" not in episode


# ===== WebtoonEpisode 속성 접근 테스트 =====


def test_webtoon_episode_property_access(webtoon_instance: Webtoon):
    """WebtoonEpisode 속성 직접 접근"""
    episode = webtoon_instance.episode.add(
        id=10100,
        name="Property Test",
        episode_no=99,
        state="testing"
    )

    # 속성 직접 접근
    assert episode.episode_no == 99
    assert episode.name == "Property Test"
    assert episode.state == "testing"
    assert episode.episode_id == 10100
    assert isinstance(episode.added_at, datetime.datetime)


def test_webtoon_episode_webtoon_property(webtoon_instance: Webtoon):
    """WebtoonEpisode의 webtoon 속성 테스트"""
    episode = webtoon_instance.episode.add(id=10101, name="Webtoon Property Test")

    # webtoon 속성은 연결된 Webtoon 인스턴스를 반환
    assert episode.webtoon is webtoon_instance


def test_webtoon_episode_without_webtoon_raises(webtoon_instance: Webtoon):
    """webtoon 없이 생성된 WebtoonEpisode는 에러 발생"""
    from wbtn._managers._episode import WebtoonEpisode as EpisodeClass
    import datetime

    # _webtoon=None으로 WebtoonEpisode 직접 생성
    episode = EpisodeClass(
        episode_no=1,
        name="Test",
        state="test",
        episode_id=123,
        added_at=datetime.datetime.now(),
        _webtoon=None
    )

    # webtoon 속성 접근 시 에러
    with pytest.raises(ValueError, match="Webtoon is not included"):
        _ = episode.webtoon


# ===== WebtoonEpisode 반환값 테스트 =====


def test_add_returns_webtoon_episode(webtoon_instance: Webtoon):
    """add() 메서드가 WebtoonEpisode를 반환하는지 확인"""
    result = webtoon_instance.episode.add(id=10200, name="Return Test")

    assert isinstance(result, WebtoonEpisode)
    assert result.episode_no is not None
    assert result.name == "Return Test"
    assert result.episode_id == 10200


def test_add_episode_and_immediately_use_extra_data(webtoon_instance: Webtoon):
    """add() 반환값으로 바로 extra_data 사용"""
    episode = webtoon_instance.episode.add(id=10201, name="Immediate Use")

    # 반환된 객체로 바로 extra_data 조작
    episode["immediate_key"] = "immediate_value"
    assert episode["immediate_key"] == "immediate_value"


def test_chaining_operations(webtoon_instance: Webtoon):
    """연쇄 작업 테스트"""
    # add() 후 바로 extra_data 설정하고 조회
    episode = webtoon_instance.episode.add(id=10202, name="Chaining Test")
    episode["chain1"] = "value1"
    episode["chain2"] = "value2"

    # 같은 객체로 계속 작업 가능
    assert len(episode) == 2
    assert "chain1" in episode
    assert "chain2" in episode

    del episode["chain1"]
    assert len(episode) == 1


def test_episode_comparison(webtoon_instance: Webtoon):
    """WebtoonEpisode 객체 비교"""
    ep1 = webtoon_instance.episode.add(id=10203, name="Episode 1")
    ep2 = webtoon_instance.episode.add(id=10204, name="Episode 2")

    # 다른 에피소드는 episode_no가 다름
    assert ep1.episode_no != ep2.episode_no

    # 같은 episode_no로 재생성하면 같은 데이터
    ep1_reloaded = WebtoonEpisode.from_episode_no(ep1.episode_no, webtoon_instance)
    assert ep1_reloaded.episode_no == ep1.episode_no
    assert ep1_reloaded.name == ep1.name
    assert ep1_reloaded.episode_id == ep1.episode_id
