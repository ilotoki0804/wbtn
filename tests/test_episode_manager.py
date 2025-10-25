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
    episode_no = webtoon_instance.episode.add(
        id=12345,
        name="Test Episode",
        episode_no=1,
        state="downloaded"
    )
    assert episode_no == 1


def test_add_episode_auto_episode_number(webtoon_instance: Webtoon):
    """episode_no를 자동으로 할당"""
    episode_no = webtoon_instance.episode.add(
        id=100,
        name="Auto Number Episode",
        state="complete"
    )
    assert episode_no is not None
    assert isinstance(episode_no, int)


def test_add_multiple_episodes(webtoon_instance: Webtoon):
    """여러 에피소드 추가"""
    ep1 = webtoon_instance.episode.add(id=1, name="Episode 1")
    ep2 = webtoon_instance.episode.add(id=2, name="Episode 2")
    ep3 = webtoon_instance.episode.add(id=3, name="Episode 3")

    assert ep1 != ep2 != ep3


def test_add_episode_with_unicode_name(webtoon_instance: Webtoon):
    """유니코드 이름으로 에피소드 추가"""
    episode_no = webtoon_instance.episode.add(
        id=999,
        name="테스트 에피소드 😀",
        state="ready"
    )
    assert episode_no is not None


def test_add_episode_minimal_parameters(webtoon_instance: Webtoon):
    """최소한의 파라미터로 에피소드 추가"""
    episode_no = webtoon_instance.episode.add(
        id=500,
        name="Minimal"
    )
    assert episode_no is not None


def test_episode_id_can_be_various_types(webtoon_instance: Webtoon):
    """에피소드 ID는 다양한 타입 가능"""
    # 정수 ID
    ep1 = webtoon_instance.episode.add(id=123, name="Int ID")
    # 문자열 ID
    ep2 = webtoon_instance.episode.add(id="abc123", name="String ID")
    # None ID (?)
    ep3 = webtoon_instance.episode.add(id=None, name="None ID")

    assert ep1 is not None
    assert ep2 is not None
    assert ep3 is not None


# ===== WebtoonEpisode 클래스 테스트 =====


def test_webtoon_episode_from_episode_no(webtoon_instance: Webtoon):
    """episode_no로 WebtoonEpisode 객체 생성"""
    episode_no = webtoon_instance.episode.add(
        id=12345,
        name="Test Episode",
        state="downloaded"
    )

    with webtoon_instance.connection.cursor() as cur:
        episode = WebtoonEpisode.from_episode_no(episode_no, cur)

    assert episode.episode_no == episode_no
    assert episode.name == "Test Episode"
    assert episode.state == "downloaded"
    assert episode.episode_id == 12345
    assert isinstance(episode.added_at, datetime.datetime)


def test_webtoon_episode_with_nonexistent_episode_no_raises(webtoon_instance: Webtoon):
    """존재하지 않는 episode_no로 객체 생성 시 에러"""
    with webtoon_instance.connection.cursor() as cur:
        with pytest.raises(ValueError, match="does not exist"):
            WebtoonEpisode.from_episode_no(99999, cur)


def test_webtoon_episode_added_at_timestamp(webtoon_instance: Webtoon):
    """added_at이 올바른 타임스탬프인지 확인"""
    before_time = datetime.datetime.now()
    episode_no = webtoon_instance.episode.add(id=777, name="Time Test")
    after_time = datetime.datetime.now()

    with webtoon_instance.connection.cursor() as cur:
        episode = WebtoonEpisode.from_episode_no(episode_no, cur)

    assert before_time <= episode.added_at <= after_time


# ===== extra_data 추가 및 조회 테스트 =====


def test_add_extra_data_string(webtoon_instance: Webtoon):
    """문자열 extra_data 추가"""
    episode_no = webtoon_instance.episode.add(id=1, name="Extra Test")
    webtoon_instance.episode.add_extra_data(episode_no, "description", "This is a description")

    result = webtoon_instance.episode.extra_data(episode_no, "description")
    assert result == "This is a description"


def test_add_extra_data_integer(webtoon_instance: Webtoon):
    """정수 extra_data 추가"""
    episode_no = webtoon_instance.episode.add(id=2, name="Int Extra")
    webtoon_instance.episode.add_extra_data(episode_no, "views", 10000)

    result = webtoon_instance.episode.extra_data(episode_no, "views")
    assert result == 10000


def test_add_extra_data_json(webtoon_instance: Webtoon):
    """JsonData extra_data 추가"""
    episode_no = webtoon_instance.episode.add(id=3, name="JSON Extra")
    json_data = JsonData(data={"likes": 500, "comments": ["good", "nice"]})
    webtoon_instance.episode.add_extra_data(episode_no, "metadata", json_data)

    result = webtoon_instance.episode.extra_data(episode_no, "metadata")
    assert isinstance(result, JsonData)
    loaded = result.load()
    assert loaded["likes"] == 500


def test_add_multiple_extra_data(webtoon_instance: Webtoon):
    """여러 extra_data 추가"""
    episode_no = webtoon_instance.episode.add(id=4, name="Multiple Extra")
    webtoon_instance.episode.add_extra_data(episode_no, "author", "John Doe")
    webtoon_instance.episode.add_extra_data(episode_no, "rating", 4.5)
    webtoon_instance.episode.add_extra_data(episode_no, "published", True)

    assert webtoon_instance.episode.extra_data(episode_no, "author") == "John Doe"
    assert webtoon_instance.episode.extra_data(episode_no, "rating") == 4.5
    assert webtoon_instance.episode.extra_data(episode_no, "published") is True


def test_extra_data_all_purposes(webtoon_instance: Webtoon):
    """모든 extra_data를 딕셔너리로 조회"""
    episode_no = webtoon_instance.episode.add(id=5, name="All Extra")
    webtoon_instance.episode.add_extra_data(episode_no, "key1", "value1")
    webtoon_instance.episode.add_extra_data(episode_no, "key2", 123)

    all_extra = webtoon_instance.episode.extra_data(episode_no, purpose=None)
    assert isinstance(all_extra, dict)
    assert all_extra["key1"] == "value1"
    assert all_extra["key2"] == 123


def test_extra_data_purposes_list(webtoon_instance: Webtoon):
    """extra_data의 purpose 목록 조회"""
    episode_no = webtoon_instance.episode.add(id=6, name="Purposes")
    webtoon_instance.episode.add_extra_data(episode_no, "purpose1", "data1")
    webtoon_instance.episode.add_extra_data(episode_no, "purpose2", "data2")

    purposes = webtoon_instance.episode.extra_data_purposes(episode_no)
    # purposes는 리스트 of 튜플일 수 있음
    purpose_list = [p if isinstance(p, str) else p[0] for p in purposes]
    assert "purpose1" in purpose_list
    assert "purpose2" in purpose_list


# ===== 상태 관리 테스트 =====


def test_episode_with_different_states(webtoon_instance: Webtoon):
    """다양한 상태로 에피소드 추가"""
    states = ["downloaded", "empty", "impaired", "exists", "pending", None]

    for i, state in enumerate(states):
        episode_no = webtoon_instance.episode.add(
            id=1000 + i,
            name=f"Episode {i}",
            state=state
        )
        with webtoon_instance.connection.cursor() as cur:
            episode = WebtoonEpisode.from_episode_no(episode_no, cur)
        assert episode.state == state


def test_episode_state_can_be_custom_string(webtoon_instance: Webtoon):
    """사용자 정의 상태 문자열 사용 가능"""
    episode_no = webtoon_instance.episode.add(
        id=2000,
        name="Custom State",
        state="my_custom_state"
    )

    with webtoon_instance.connection.cursor() as cur:
        episode = WebtoonEpisode.from_episode_no(episode_no, cur)

    assert episode.state == "my_custom_state"


# ===== 엣지 케이스 및 오류 처리 =====


def test_add_episode_with_very_long_name(webtoon_instance: Webtoon):
    """매우 긴 이름으로 에피소드 추가"""
    long_name = "Episode " * 100
    episode_no = webtoon_instance.episode.add(id=3000, name=long_name)

    with webtoon_instance.connection.cursor() as cur:
        episode = WebtoonEpisode.from_episode_no(episode_no, cur)

    assert episode.name == long_name


def test_add_episode_with_special_characters_in_name(webtoon_instance: Webtoon):
    """특수 문자가 포함된 이름"""
    special_name = "Episode \"Special\" <Characters> & Symbols! 🎉"
    episode_no = webtoon_instance.episode.add(id=4000, name=special_name)

    with webtoon_instance.connection.cursor() as cur:
        episode = WebtoonEpisode.from_episode_no(episode_no, cur)

    assert episode.name == special_name


def test_extra_data_with_none_value(webtoon_instance: Webtoon):
    """None 값을 extra_data로 추가"""
    episode_no = webtoon_instance.episode.add(id=5000, name="None Test")
    webtoon_instance.episode.add_extra_data(episode_no, "nullable", None)

    result = webtoon_instance.episode.extra_data(episode_no, "nullable")
    assert result is None


def test_extra_data_with_empty_string(webtoon_instance: Webtoon):
    """빈 문자열을 extra_data로 추가"""
    episode_no = webtoon_instance.episode.add(id=6000, name="Empty String")
    webtoon_instance.episode.add_extra_data(episode_no, "empty", "")

    result = webtoon_instance.episode.extra_data(episode_no, "empty")
    assert result == ""


def test_extra_data_overwrites_existing_purpose(webtoon_instance: Webtoon):
    """같은 purpose의 extra_data는 덮어씀"""
    episode_no = webtoon_instance.episode.add(id=7000, name="Overwrite")
    webtoon_instance.episode.add_extra_data(episode_no, "field", "original")
    webtoon_instance.episode.add_extra_data(episode_no, "field", "updated")

    result = webtoon_instance.episode.extra_data(episode_no, "field")
    assert result == "updated"


# ===== delete_extra_data 테스트 =====


def test_delete_extra_data_basic(webtoon_instance: Webtoon):
    """extra_data를 성공적으로 삭제"""
    episode_no = webtoon_instance.episode.add(id=8000, name="Delete Test")
    webtoon_instance.episode.add_extra_data(episode_no, "to_delete", "value")

    # 삭제 전 확인
    assert webtoon_instance.episode.extra_data(episode_no, "to_delete") == "value"

    # 삭제
    webtoon_instance.episode.delete_extra_data(episode_no, "to_delete")

    # 삭제 후 해당 데이터가 없는지 확인
    with pytest.raises(Exception):  # 데이터가 없으면 에러 발생
        webtoon_instance.episode.extra_data(episode_no, "to_delete")


def test_delete_extra_data_nonexistent_purpose_raises(webtoon_instance: Webtoon):
    """존재하지 않는 purpose 삭제 시 KeyError 발생"""
    episode_no = webtoon_instance.episode.add(id=8001, name="No Purpose")

    with pytest.raises(KeyError) as exc_info:
        webtoon_instance.episode.delete_extra_data(episode_no, "nonexistent")

    assert (episode_no, "nonexistent") == exc_info.value.args[0]


def test_delete_extra_data_nonexistent_episode_raises(webtoon_instance: Webtoon):
    """존재하지 않는 에피소드의 extra_data 삭제 시 KeyError 발생"""
    with pytest.raises(KeyError) as exc_info:
        webtoon_instance.episode.delete_extra_data(99999, "purpose")

    assert (99999, "purpose") == exc_info.value.args[0]


def test_delete_extra_data_keeps_other_purposes(webtoon_instance: Webtoon):
    """특정 purpose만 삭제하고 다른 purpose는 유지"""
    episode_no = webtoon_instance.episode.add(id=8002, name="Multiple Purposes")
    webtoon_instance.episode.add_extra_data(episode_no, "keep1", "value1")
    webtoon_instance.episode.add_extra_data(episode_no, "delete", "value2")
    webtoon_instance.episode.add_extra_data(episode_no, "keep2", "value3")

    # 하나만 삭제
    webtoon_instance.episode.delete_extra_data(episode_no, "delete")

    # 나머지는 유지되는지 확인
    assert webtoon_instance.episode.extra_data(episode_no, "keep1") == "value1"
    assert webtoon_instance.episode.extra_data(episode_no, "keep2") == "value3"

    # 삭제된 것은 접근 불가
    with pytest.raises(Exception):
        webtoon_instance.episode.extra_data(episode_no, "delete")


def test_delete_extra_data_different_types(webtoon_instance: Webtoon):
    """다양한 타입의 extra_data 삭제"""
    episode_no = webtoon_instance.episode.add(id=8003, name="Type Test")

    # 다양한 타입 추가
    webtoon_instance.episode.add_extra_data(episode_no, "string", "text")
    webtoon_instance.episode.add_extra_data(episode_no, "integer", 123)
    webtoon_instance.episode.add_extra_data(episode_no, "json", JsonData(data={"key": "value"}))

    # 각각 삭제
    webtoon_instance.episode.delete_extra_data(episode_no, "string")
    webtoon_instance.episode.delete_extra_data(episode_no, "integer")
    webtoon_instance.episode.delete_extra_data(episode_no, "json")

    # 모두 삭제되었는지 확인
    all_data = webtoon_instance.episode.extra_data(episode_no, purpose=None)
    assert isinstance(all_data, dict)
    assert len(all_data) == 0


def test_delete_extra_data_same_purpose_different_episodes(webtoon_instance: Webtoon):
    """같은 purpose지만 다른 에피소드의 데이터는 유지"""
    ep1 = webtoon_instance.episode.add(id=8004, name="Episode 1")
    ep2 = webtoon_instance.episode.add(id=8005, name="Episode 2")

    webtoon_instance.episode.add_extra_data(ep1, "shared", "value1")
    webtoon_instance.episode.add_extra_data(ep2, "shared", "value2")

    # ep1의 데이터만 삭제
    webtoon_instance.episode.delete_extra_data(ep1, "shared")

    # ep2는 유지
    assert webtoon_instance.episode.extra_data(ep2, "shared") == "value2"

    # ep1은 삭제됨
    with pytest.raises(Exception):
        webtoon_instance.episode.extra_data(ep1, "shared")


def test_delete_and_readd_extra_data(webtoon_instance: Webtoon):
    """삭제 후 같은 purpose로 다시 추가 가능"""
    episode_no = webtoon_instance.episode.add(id=8006, name="Readd Test")

    # 추가
    webtoon_instance.episode.add_extra_data(episode_no, "readd", "original")
    assert webtoon_instance.episode.extra_data(episode_no, "readd") == "original"

    # 삭제
    webtoon_instance.episode.delete_extra_data(episode_no, "readd")

    # 다시 추가
    webtoon_instance.episode.add_extra_data(episode_no, "readd", "new value")
    assert webtoon_instance.episode.extra_data(episode_no, "readd") == "new value"


def test_delete_extra_data_with_special_characters(webtoon_instance: Webtoon):
    """특수 문자가 포함된 purpose 삭제"""
    episode_no = webtoon_instance.episode.add(id=8007, name="Special Chars")

    special_purposes = ["purpose-with-dash", "purpose_with_underscore", "purpose.with.dot", "한글purpose"]

    for purpose in special_purposes:
        webtoon_instance.episode.add_extra_data(episode_no, purpose, "value")

    for purpose in special_purposes:
        webtoon_instance.episode.delete_extra_data(episode_no, purpose)

    all_data = webtoon_instance.episode.extra_data(episode_no, purpose=None)
    assert isinstance(all_data, dict)
    assert len(all_data) == 0


# ===== 데이터 지속성 테스트 =====


def test_episode_persists_across_connections(tmp_path: Path):
    """연결 간 에피소드 데이터 지속성"""
    db_path = tmp_path / "episode_persist.wbtn"

    # 첫 번째 연결: 데이터 추가
    with Webtoon(db_path) as webtoon:
        episode_no = webtoon.episode.add(
            id=8000,
            name="Persistent Episode",
            state="saved"
        )
        webtoon.episode.add_extra_data(episode_no, "note", "persisted")

    # 두 번째 연결: 데이터 확인
    with Webtoon(db_path) as webtoon:
        with webtoon.connection.cursor() as cur:
            episode = WebtoonEpisode.from_episode_no(episode_no, cur)

        assert episode.name == "Persistent Episode"
        assert episode.state == "saved"
        assert webtoon.episode.extra_data(episode_no, "note") == "persisted"


def test_complex_workflow(webtoon_instance: Webtoon):
    """복잡한 워크플로우 테스트"""
    # 여러 에피소드 추가
    episodes = []
    for i in range(5):
        ep_no = webtoon_instance.episode.add(
            id=9000 + i,
            name=f"Chapter {i + 1}",
            state="published"
        )
        episodes.append(ep_no)

        # 각 에피소드에 extra_data 추가
        webtoon_instance.episode.add_extra_data(ep_no, "chapter_num", i + 1)
        webtoon_instance.episode.add_extra_data(
            ep_no,
            "metadata",
            JsonData(data={"views": 1000 * (i + 1), "likes": 100 * (i + 1)})
        )

    # 모든 에피소드 확인
    for i, ep_no in enumerate(episodes):
        with webtoon_instance.connection.cursor() as cur:
            episode = WebtoonEpisode.from_episode_no(ep_no, cur)

        assert episode.name == f"Chapter {i + 1}"
        assert episode.state == "published"

        chapter_num = webtoon_instance.episode.extra_data(ep_no, "chapter_num")
        assert chapter_num == i + 1
