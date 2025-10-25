"""
공통 테스트 fixture 및 유틸리티 함수들
"""
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

# Ensure src is importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbtn import Webtoon
from wbtn._managers import ConnectionSettings


@pytest.fixture
def temp_wbtn_path(tmp_path: Path) -> Path:
    """임시 .wbtn 파일 경로를 반환합니다."""
    return tmp_path / "test.wbtn"


@pytest.fixture
def webtoon_instance(temp_wbtn_path: Path) -> Iterator[Webtoon]:
    """연결된 Webtoon 인스턴스를 제공하고 테스트 후 정리합니다."""
    with Webtoon(temp_wbtn_path) as webtoon:
        yield webtoon


@pytest.fixture
def readonly_webtoon(temp_wbtn_path: Path) -> Iterator[Webtoon]:
    """읽기 전용 Webtoon 인스턴스를 제공합니다."""
    # 먼저 파일을 생성
    with Webtoon(temp_wbtn_path):
        pass

    # 읽기 전용으로 열기
    settings = ConnectionSettings(read_only=True)
    with Webtoon(temp_wbtn_path, connection_settings=settings) as webtoon:
        yield webtoon


@pytest.fixture
def memory_webtoon() -> Iterator[Webtoon]:
    """메모리 내 Webtoon 인스턴스를 제공합니다."""
    with Webtoon(":memory:") as webtoon:
        yield webtoon


@pytest.fixture
def sample_episode_data():
    """테스트용 에피소드 데이터를 반환합니다."""
    return {
        "id": 12345,
        "name": "Test Episode Title",
        "state": "downloaded"
    }


@pytest.fixture
def sample_media_data():
    """테스트용 미디어 데이터를 반환합니다."""
    return {
        "episode_no": 1,
        "media_no": 1,
        "purpose": "image",
        "state": "complete",
        "media_type": "image/jpeg",
        "media_name": "001.jpg",
        "data": b"fake image data"
    }


def create_populated_webtoon(path: Path) -> Webtoon:
    """데이터가 채워진 Webtoon 인스턴스를 생성합니다."""
    webtoon = Webtoon(path)
    webtoon.connect()

    # 기본 정보 추가
    webtoon.info["title"] = "Test Webtoon"
    webtoon.info["author"] = "Test Author"

    # 에피소드 추가
    for i in range(1, 4):
        webtoon.episode.add(
            id=1000 + i,
            name=f"Episode {i}",
            state="complete"
        )

    return webtoon
