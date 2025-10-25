"""
WebtoonMediaManager와 관련 클래스들에 대한 테스트
미디어 추가, 조회, 수정, path/data 처리 등을 테스트합니다.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbtn import Webtoon
from wbtn._json_data import JsonData


# ===== 미디어 추가 (데이터) 테스트 =====


def test_add_media_with_data(webtoon_instance: Webtoon):
    """데이터로 미디어 추가"""
    webtoon_instance.episode.add(id=1, name="Test Ep")

    media = webtoon_instance.media.add(
        b"image data",
        episode_no=1,
        media_no=1,
        purpose="image",
        media_type="image/jpeg",
        media_name="001.jpg"
    )

    assert media is not None
    loaded = media.load()
    assert loaded.data == b"image data"


def test_add_multiple_media_to_episode(webtoon_instance: Webtoon):
    """한 에피소드에 여러 미디어 추가"""
    webtoon_instance.episode.add(id=2, name="Multi Media Ep")

    media1 = webtoon_instance.media.add(
        b"data1",
        episode_no=1,
        media_no=1,
        purpose="image"
    )
    media2 = webtoon_instance.media.add(
        b"data2",
        episode_no=1,
        media_no=2,
        purpose="image"
    )

    assert media1.media_id() != media2.media_id()


def test_add_media_with_json_data(webtoon_instance: Webtoon):
    """JsonData로 미디어 추가"""
    webtoon_instance.episode.add(id=3, name="JSON Media Ep")

    json_meta = JsonData(data={"width": 800, "height": 600})
    media = webtoon_instance.media.add(
        json_meta,
        episode_no=1,
        media_no=1,
        purpose="metadata"
    )

    loaded = media.load()
    assert isinstance(loaded.data, JsonData)


# ===== 미디어 추가 (경로) 테스트 =====


def test_add_media_with_path(tmp_path: Path, webtoon_instance: Webtoon):
    """경로로 미디어 추가"""
    webtoon_instance.episode.add(id=4, name="Path Media Ep")

    # 테스트 파일 생성
    media_file = tmp_path / "test.jpg"
    media_file.write_bytes(b"test image")

    # 경로로 미디어 추가
    media = webtoon_instance.media.add(
        media_file,
        episode_no=1,
        media_no=1,
        purpose="image",
        conversion="bytes"
    )

    loaded = media.load()
    assert loaded.path is not None


def test_add_path_or_data_creates_file_when_not_self_contained(tmp_path: Path):
    """self_contained가 아닐 때 파일 생성"""
    db_path = tmp_path / "media.wbtn"
    media_path = tmp_path / "media" / "001.jpg"

    with Webtoon(db_path) as webtoon:
        webtoon.episode.add(id=5, name="File Test")
        webtoon.path.initialize_base_path(tmp_path)

        webtoon.media.add_path_or_data(
            path=media_path,
            data=b"image content",
            episode_no=1,
            media_no=1,
            purpose="image"
        )

        assert media_path.exists()
        assert media_path.read_bytes() == b"image content"


# ===== 미디어 조회 및 iterate 테스트 =====


def test_iterate_media_by_episode(webtoon_instance: Webtoon):
    """특정 에피소드의 미디어 순회"""
    webtoon_instance.episode.add(id=6, name="Iterate Test")

    for i in range(3):
        webtoon_instance.media.add(
            f"data{i}".encode(),
            episode_no=1,
            media_no=i + 1,
            purpose="image"
        )

    media_list = list(webtoon_instance.media.iterate(episode_no=1))
    assert len(media_list) == 3


def test_iterate_media_by_purpose(webtoon_instance: Webtoon):
    """purpose로 미디어 필터링"""
    webtoon_instance.episode.add(id=7, name="Purpose Test")

    webtoon_instance.media.add(b"img", episode_no=1, media_no=1, purpose="image")
    webtoon_instance.media.add(b"thumb", episode_no=1, media_no=2, purpose="thumbnail")
    webtoon_instance.media.add(b"img2", episode_no=1, media_no=3, purpose="image")

    images = list(webtoon_instance.media.iterate(episode_no=1, purpose="image"))
    assert len(images) == 2


def test_iterate_media_by_state(webtoon_instance: Webtoon):
    """state로 미디어 필터링"""
    webtoon_instance.episode.add(id=8, name="State Test")

    webtoon_instance.media.add(
        b"data1",
        episode_no=1,
        media_no=1,
        purpose="image",
        state="complete"
    )
    webtoon_instance.media.add(
        b"data2",
        episode_no=1,
        media_no=2,
        purpose="image",
        state="pending"
    )

    complete_media = list(webtoon_instance.media.iterate(episode_no=1, state="complete"))
    assert len(complete_media) == 1


# ===== 미디어 수정 및 삭제 테스트 =====


def test_remove_media(webtoon_instance: Webtoon):
    """미디어 삭제"""
    webtoon_instance.episode.add(id=9, name="Remove Test")

    media = webtoon_instance.media.add(
        b"to delete",
        episode_no=1,
        media_no=1,
        purpose="image"
    )

    media_id = media.media_id()
    webtoon_instance.media.remove(media)

    # 삭제 후 조회 시 에러
    with pytest.raises(ValueError):
        webtoon_instance.media._load(media_id)


def test_set_media_updates_data(webtoon_instance: Webtoon):
    """set으로 미디어 데이터 업데이트"""
    webtoon_instance.episode.add(id=10, name="Update Test")

    media = webtoon_instance.media.add(
        b"original",
        episode_no=1,
        media_no=1,
        purpose="image"
    )

    # 데이터 수정
    media_data = media.load()
    media_data.data = b"updated"
    webtoon_instance.media.set(media_data)

    # 다시 로드하여 확인
    reloaded = webtoon_instance.media._load(media.media_id())
    assert reloaded.data == b"updated"


# ===== load_data 및 dump_path 테스트 =====


def test_load_data_from_path_media(tmp_path: Path, webtoon_instance: Webtoon):
    """경로 기반 미디어에서 데이터 로드"""
    webtoon_instance.episode.add(id=11, name="Load Data Test")

    media_file = tmp_path / "load_test.dat"
    media_file.write_bytes(b"file content")

    media = webtoon_instance.media.add(
        media_file,
        episode_no=1,
        media_no=1,
        purpose="data",
        conversion="bytes"
    )

    loaded_data = webtoon_instance.media.load_data(media)
    # conversion이 bytes이므로 bytes로 변환된 값이 나옴
    assert isinstance(loaded_data, (bytes, int))


def test_dump_path_writes_data_to_file(tmp_path: Path, webtoon_instance: Webtoon):
    """데이터를 파일로 dump"""
    webtoon_instance.episode.add(id=12, name="Dump Path Test")

    media = webtoon_instance.media.add(
        b"dump this",
        episode_no=1,
        media_no=1,
        purpose="image"
    )

    output_path = tmp_path / "dumped.dat"
    webtoon_instance.path.initialize_base_path(tmp_path)
    webtoon_instance.media.dump_path(media, output_path)

    assert output_path.exists()
    assert output_path.read_bytes() == b"dump this"


# ===== WebtoonMedia 및 WebtoonMediaData 테스트 =====


def test_webtoon_media_loaded_property(webtoon_instance: Webtoon):
    """WebtoonMedia의 loaded 속성"""
    webtoon_instance.episode.add(id=13, name="Loaded Test")

    media = webtoon_instance.media.add(
        b"test",
        episode_no=1,
        media_no=1,
        purpose="image"
    )

    # 처음엔 ID만 저장됨
    assert media.loaded is False

    # load 후 데이터 저장됨
    media.load(store_media=True)
    assert media.loaded is True


def test_webtoon_media_from_media_id(webtoon_instance: Webtoon):
    """media_id로 WebtoonMedia 생성"""
    from wbtn._managers import WebtoonMedia

    webtoon_instance.episode.add(id=14, name="From ID Test")

    media = webtoon_instance.media.add(
        b"test data",
        episode_no=1,
        media_no=1,
        purpose="image"
    )

    media_id = media.media_id()
    new_media = WebtoonMedia.from_media_id(media_id, webtoon_instance)

    assert new_media.media_id() == media_id


# ===== 엣지 케이스 테스트 =====


def test_media_with_none_data(webtoon_instance: Webtoon):
    """None 데이터로 미디어 추가"""
    webtoon_instance.episode.add(id=15, name="None Data Test")

    media = webtoon_instance.media.add(
        None,
        episode_no=1,
        media_no=1,
        purpose="placeholder"
    )

    loaded = media.load()
    assert loaded.data is None


def test_media_with_empty_bytes(webtoon_instance: Webtoon):
    """빈 bytes로 미디어 추가"""
    webtoon_instance.episode.add(id=16, name="Empty Bytes Test")

    media = webtoon_instance.media.add(
        b"",
        episode_no=1,
        media_no=1,
        purpose="empty"
    )

    loaded = media.load()
    assert loaded.data == b""


def test_media_with_large_data(webtoon_instance: Webtoon):
    """큰 데이터로 미디어 추가"""
    webtoon_instance.episode.add(id=17, name="Large Data Test")

    large_data = b"x" * (1024 * 1024)  # 1MB
    media = webtoon_instance.media.add(
        large_data,
        episode_no=1,
        media_no=1,
        purpose="large"
    )

    loaded = media.load()
    assert isinstance(loaded.data, bytes)
    assert len(loaded.data) == 1024 * 1024
