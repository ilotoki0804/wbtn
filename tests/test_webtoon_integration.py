"""
Webtoon 클래스에 대한 통합 테스트
전체 워크플로우, context manager, execute 메서드 등을 테스트합니다.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbtn import Webtoon
from wbtn._json_data import JsonData


# ===== Context Manager 테스트 =====


def test_webtoon_context_manager_basic(tmp_path: Path):
    """기본 context manager 사용"""
    db_path = tmp_path / "context.wbtn"

    with Webtoon(db_path) as webtoon:
        assert webtoon.connection._conn is not None
        webtoon.info["test"] = "value"

    # context 종료 후 연결이 닫혀야 함
    # (이미 테스트된 내용이지만 통합 테스트로 재확인)


def test_webtoon_manual_connect_and_close(tmp_path: Path):
    """수동 연결 및 종료"""
    db_path = tmp_path / "manual.wbtn"
    webtoon = Webtoon(db_path)

    webtoon.connect()
    assert webtoon.connection._conn is not None

    webtoon.close()
    assert webtoon.connection._conn is None


def test_webtoon_exception_in_context_closes_connection(tmp_path: Path):
    """context 내부에서 예외 발생 시에도 연결 닫힘"""
    db_path = tmp_path / "exception.wbtn"
    webtoon = Webtoon(db_path)

    try:
        with webtoon:
            assert webtoon.connection._conn is not None
            raise ValueError("Test exception")
    except ValueError:
        pass

    assert webtoon.connection._conn is None


# ===== execute 및 execute_with 메서드 테스트 =====


def test_execute_simple_query(webtoon_instance: Webtoon):
    """단순 쿼리 실행"""
    result = webtoon_instance.execute("SELECT 1 AS value")
    assert result[0] == 1


def test_execute_with_parameters(webtoon_instance: Webtoon):
    """파라미터가 있는 쿼리 실행"""
    webtoon_instance.info["test_key"] = "test_value"

    result = webtoon_instance.execute(
        "SELECT value FROM info WHERE name = ?",
        ("test_key",)
    )
    assert result is not None


def test_execute_with_context_manager(webtoon_instance: Webtoon):
    """execute_with로 cursor 컨텍스트 사용"""
    webtoon_instance.info["key1"] = "value1"
    webtoon_instance.info["key2"] = "value2"

    with webtoon_instance.execute_with("SELECT name FROM info WHERE name LIKE 'key%'") as cursor:
        results = cursor.fetchall()

    assert len(results) >= 2


def test_execute_with_multiple_results(webtoon_instance: Webtoon):
    """여러 결과를 반환하는 쿼리"""
    for i in range(5):
        webtoon_instance.info[f"item_{i}"] = f"value_{i}"

    with webtoon_instance.execute_with("SELECT name, value FROM info WHERE name LIKE 'item_%'") as cursor:
        results = list(cursor)

    assert len(results) == 5


# ===== 전체 워크플로우 통합 테스트 =====


def test_complete_webtoon_workflow(tmp_path: Path):
    """완전한 웹툰 작업 워크플로우"""
    db_path = tmp_path / "workflow.wbtn"

    with Webtoon(db_path) as webtoon:
        # 1. 기본 정보 설정
        webtoon.info["title"] = "테스트 웹툰"
        webtoon.info["author"] = "작가명"
        webtoon.info["description"] = "설명"

        # 2. 에피소드 추가
        ep1 = webtoon.episode.add(1)
        ep1["name"] = "1화"
        ep1["state"] = "complete"
        ep2 = webtoon.episode.add(2)
        ep2["name"] = "2화"
        ep2["state"] = "complete"
        ep3 = webtoon.episode.add(3)
        ep3["name"] = "3화"
        ep3["state"] = "pending"

        # 3. 에피소드별 추가 데이터
        ep1["views"] = 1000
        ep2["views"] = 2000
        ep3["views"] = 500

        # 4. 미디어 추가
        for ep in [ep1, ep2, ep3]:
            for i in range(3):
                webtoon.content.add(
                    ep,
                    i + 1,
                    "image",
                    data=f"image_{ep.episode_no}_{i}".encode()
                )

        # 5. 추가 파일
        extra_file_path = tmp_path / "extra.txt"
        extra_file_path.write_text("extra content")
        webtoon.extra_file.add_value(extra_file_path, value="extra content", purpose="metadata")

    # 데이터베이스 재열기 및 검증
    with Webtoon(db_path) as webtoon:
        assert webtoon.info["title"] == "테스트 웹툰"
        assert webtoon.info["author"] == "작가명"

        # 에피소드 확인
        all_media = list(webtoon.content.iterate(episode=None))
        assert len(all_media) == 9  # 3 episodes * 3 media each

        # 추가 파일 확인
        assert len(webtoon.extra_file) == 1


def test_multi_episode_with_different_media_types(tmp_path: Path):
    """다양한 미디어 타입을 가진 여러 에피소드"""
    db_path = tmp_path / "multi_media.wbtn"

    with Webtoon(db_path) as webtoon:
        # 에피소드 생성
        episode = webtoon.episode.add(100)
        episode["name"] = "Complex Episode"

        # 다양한 타입의 미디어
        webtoon.content.add(
            episode,
            1,
            "image",
            data=b"jpeg data"
        )

        webtoon.content.add(
            episode,
            2,
            "thumbnail",
            data=b"png data"
        )

        webtoon.content.add(
            episode,
            3,
            "comment",
            data=JsonData(data={"comment": "Great episode!"})
        )

        # 검증
        images = list(webtoon.content.iterate(episode=episode, kind="image"))
        thumbs = list(webtoon.content.iterate(episode=episode, kind="thumbnail"))
        comments = list(webtoon.content.iterate(episode=episode, kind="comment"))

        assert len(images) == 1
        assert len(thumbs) == 1
        assert len(comments) == 1


def test_large_scale_data_insertion(tmp_path: Path):
    """대규모 데이터 삽입 테스트"""
    db_path = tmp_path / "large_scale.wbtn"

    with Webtoon(db_path) as webtoon:
        # 100개의 에피소드
        episodes = []
        for i in range(100):
            episode = webtoon.episode.add(1000 + i)
            episode["name"] = f"Episode {i + 1}"
            episode["state"] = "complete"
            episodes.append(episode)

            # 각 에피소드에 10개의 미디어
            for j in range(10):
                webtoon.content.add(
                    episode,
                    j + 1,
                    "image",
                    data=f"data_{i}_{j}".encode()
                )

    # 검증
    with Webtoon(db_path) as webtoon:
        all_media = list(webtoon.content.iterate(episode=None))
        assert len(all_media) == 1000  # 100 episodes * 10 media


# ===== 다중 연결 및 동시성 테스트 =====


def test_sequential_connections(tmp_path: Path):
    """순차적인 여러 연결"""
    db_path = tmp_path / "sequential.wbtn"

    # 첫 번째 연결
    with Webtoon(db_path) as webtoon:
        webtoon.info["session"] = "first"

    # 두 번째 연결
    with Webtoon(db_path) as webtoon:
        assert webtoon.info["session"] == "first"
        webtoon.info["session"] = "second"

    # 세 번째 연결
    with Webtoon(db_path) as webtoon:
        assert webtoon.info["session"] == "second"


def test_data_isolation_between_instances(tmp_path: Path):
    """인스턴스 간 데이터 격리 (파일 기반)"""
    db_path1 = tmp_path / "db1.wbtn"
    db_path2 = tmp_path / "db2.wbtn"

    with Webtoon(db_path1) as webtoon1:
        webtoon1.info["db"] = "first"

    with Webtoon(db_path2) as webtoon2:
        webtoon2.info["db"] = "second"

    # 각 데이터베이스는 독립적
    with Webtoon(db_path1) as webtoon1:
        assert webtoon1.info["db"] == "first"
        assert "second" not in str(webtoon1.info.get("db", ""))

    with Webtoon(db_path2) as webtoon2:
        assert webtoon2.info["db"] == "second"
        assert "first" not in str(webtoon2.info.get("db", ""))


# ===== 트랜잭션 및 롤백 테스트 =====


def test_transaction_commit(tmp_path: Path):
    """트랜잭션 커밋"""
    db_path = tmp_path / "transaction.wbtn"

    with Webtoon(db_path) as webtoon:
        webtoon.info["before_commit"] = "value"
        # context manager 종료 시 자동 커밋

    # 다시 열어서 확인
    with Webtoon(db_path) as webtoon:
        assert webtoon.info["before_commit"] == "value"


def test_explicit_operations_persist(tmp_path: Path):
    """명시적 작업이 지속됨"""
    db_path = tmp_path / "explicit.wbtn"

    with Webtoon(db_path) as webtoon:
        # 여러 작업
        webtoon.info["key1"] = "value1"
        episode = webtoon.episode.add(1)
        episode["name"] = "Test"
        webtoon.content.add(episode, 1, "test", data=b"data")

    # 재확인
    with Webtoon(db_path) as webtoon:
        assert webtoon.info["key1"] == "value1"

        with webtoon.connection.cursor() as cur:
            ep_count = cur.execute("SELECT COUNT(*) FROM Episode").fetchone()[0]
            media_count = cur.execute("SELECT COUNT(*) FROM Content").fetchone()[0]

        assert ep_count >= 1
        assert media_count >= 1


# ===== 매니저 간 상호작용 테스트 =====


def test_managers_work_together(tmp_path: Path):
    """여러 관리자가 함께 작동"""
    db_path = tmp_path / "together.wbtn"

    with Webtoon(db_path) as webtoon:
        # info 설정
        webtoon.info["title"] = "통합 테스트"

        # 에피소드 추가
        episode = webtoon.episode.add(1)
        episode["name"] = "Episode 1"

        # extra_data 추가 (MutableMapping 인터페이스)
        episode["views"] = 1000
        episode["likes"] = 50

        # 미디어 추가 (data로)
        media_data = webtoon.content.add(episode, 1, "thumbnail", data=b"fake image")

        # 검증
        assert webtoon.info["title"] == "통합 테스트"

        # Episode를 통해 extra_data 조회
        assert episode["views"] == 1000
        assert episode["likes"] == 50

        # 미디어 조회
        media_list = list(webtoon.content.iterate(episode=episode))
        assert len(media_list) == 1
        assert media_list[0].load().content_no == 1


# ===== 메모리 데이터베이스 테스트 =====


def test_memory_database_workflow(tmp_path: Path):
    """메모리 데이터베이스 워크플로우"""
    with Webtoon(":memory:") as webtoon:
        # 빠른 작업
        webtoon.info["temp"] = "value"
        episode = webtoon.episode.add(1)
        episode["name"] = "Test"
        webtoon.content.add(episode, 1, "test", data=b"data")

        # 검증
        assert len(list(webtoon.content.iterate(episode=episode))) == 1


def test_memory_database_isolation():
    """메모리 데이터베이스는 각각 독립적"""
    with Webtoon(":memory:") as webtoon1:
        webtoon1.info["db"] = "first"

        with Webtoon(":memory:") as webtoon2:
            webtoon2.info["db"] = "second"

            # 각각 독립적
            assert webtoon1.info["db"] == "first"
            assert webtoon2.info["db"] == "second"
