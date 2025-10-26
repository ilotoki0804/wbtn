"""
WebtoonMediaManager와 관련 클래스들에 대한 테스트
미디어 추가, 조회, 수정, path/data 처리 등을 테스트합니다.
"""
import datetime
import sys
from pathlib import Path

import pytest

from wbtn._managers._episode import WebtoonEpisode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbtn import Webtoon
from wbtn._json_data import JsonData


# ===== 미디어 추가 (데이터) 테스트 =====


def test_add_media_with_data(webtoon_instance: Webtoon):
    """데이터로 미디어 추가"""
    episode = webtoon_instance.episode.add(id=1, name="Test Ep")

    media = webtoon_instance.media.add(
        b"image data",
        episode=episode,
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
    episode = webtoon_instance.episode.add(id=2, name="Multi Media Ep")

    media1 = webtoon_instance.media.add(
        b"data1",
        episode=episode,
        media_no=1,
        purpose="image"
    )
    media2 = webtoon_instance.media.add(
        b"data2",
        episode=episode,
        media_no=2,
        purpose="image"
    )

    assert media1.media_id() != media2.media_id()


def test_add_media_with_json_data(webtoon_instance: Webtoon):
    """JsonData로 미디어 추가"""
    episode = webtoon_instance.episode.add(id=3, name="JSON Media Ep")

    json_meta = JsonData(data={"width": 800, "height": 600})
    media = webtoon_instance.media.add(
        json_meta,
        episode=episode,
        media_no=1,
        purpose="metadata"
    )

    loaded = media.load()
    assert isinstance(loaded.data, JsonData)


# ===== 미디어 추가 (경로) 테스트 =====


def test_add_media_with_path(tmp_path: Path, webtoon_instance: Webtoon):
    """경로로 미디어 추가"""
    episode = webtoon_instance.episode.add(id=4, name="Path Media Ep")

    # 테스트 파일 생성
    media_file = tmp_path / "test.jpg"
    media_file.write_bytes(b"test image")

    # 경로로 미디어 추가
    media = webtoon_instance.media.add(
        media_file,
        episode=episode,
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
        episode = webtoon.episode.add(id=5, name="File Test")
        webtoon.path.initialize_base_path(tmp_path)

        webtoon.media.add_path_or_data(
            path=media_path,
            data=b"image content",
            episode=episode,
            media_no=1,
            purpose="image"
        )

        assert media_path.exists()
        assert media_path.read_bytes() == b"image content"


# ===== 미디어 조회 및 iterate 테스트 =====


def test_iterate_media_by_episode(webtoon_instance: Webtoon):
    """특정 에피소드의 미디어 순회"""
    episode = webtoon_instance.episode.add(id=6, name="Iterate Test")

    for i in range(3):
        webtoon_instance.media.add(
            f"data{i}".encode(),
            episode=episode,
            media_no=i + 1,
            purpose="image"
        )

    media_list = list(webtoon_instance.media.iterate(episode=episode))
    assert len(media_list) == 3


def test_iterate_media_by_purpose(webtoon_instance: Webtoon):
    """purpose로 미디어 필터링"""
    episode = webtoon_instance.episode.add(id=7, name="Purpose Test")

    webtoon_instance.media.add(b"img", episode=episode, media_no=1, purpose="image")
    webtoon_instance.media.add(b"thumb", episode=episode, media_no=2, purpose="thumbnail")
    webtoon_instance.media.add(b"img2", episode=episode, media_no=3, purpose="image")

    images = list(webtoon_instance.media.iterate(episode=episode, purpose="image"))
    assert len(images) == 2


def test_iterate_media_by_state(webtoon_instance: Webtoon):
    """state로 미디어 필터링"""
    episode = webtoon_instance.episode.add(id=8, name="State Test")

    webtoon_instance.media.add(
        b"data1",
        episode=episode,
        media_no=1,
        purpose="image",
        state="complete"
    )
    webtoon_instance.media.add(
        b"data2",
        episode=episode,
        media_no=2,
        purpose="image",
        state="pending"
    )

    complete_media = list(webtoon_instance.media.iterate(episode=episode, state="complete"))
    assert len(complete_media) == 1


# ===== 미디어 수정 및 삭제 테스트 =====


def test_remove_media(webtoon_instance: Webtoon):
    """미디어 삭제"""
    episode = webtoon_instance.episode.add(id=9, name="Remove Test")

    media = webtoon_instance.media.add(
        b"to delete",
        episode=episode,
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
    episode = webtoon_instance.episode.add(id=10, name="Update Test")

    media = webtoon_instance.media.add(
        b"original",
        episode=episode,
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
    episode = webtoon_instance.episode.add(id=11, name="Load Data Test")

    media_file = tmp_path / "load_test.dat"
    media_file.write_bytes(b"file content")

    media = webtoon_instance.media.add(
        media_file,
        episode=episode,
        media_no=1,
        purpose="data",
        conversion="bytes"
    )

    loaded_data = webtoon_instance.media.load_data(media)
    # conversion이 bytes이므로 bytes로 변환된 값이 나옴
    assert isinstance(loaded_data, (bytes, int))


def test_dump_path_writes_data_to_file(tmp_path: Path, webtoon_instance: Webtoon):
    """데이터를 파일로 dump"""
    episode = webtoon_instance.episode.add(id=12, name="Dump Path Test")

    media = webtoon_instance.media.add(
        b"dump this",
        episode=episode,
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
    episode = webtoon_instance.episode.add(id=13, name="Loaded Test")

    media = webtoon_instance.media.add(
        b"test",
        episode=episode,
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

    episode = webtoon_instance.episode.add(id=14, name="From ID Test")

    media = webtoon_instance.media.add(
        b"test data",
        episode=episode,
        media_no=1,
        purpose="image"
    )

    media_id = media.media_id()
    new_media = WebtoonMedia.from_media_id(media_id, webtoon_instance)

    assert new_media.media_id() == media_id


# ===== 엣지 케이스 테스트 =====


def test_media_with_none_data(webtoon_instance: Webtoon):
    """None 데이터로 미디어 추가"""
    episode = webtoon_instance.episode.add(id=15, name="None Data Test")

    media = webtoon_instance.media.add(
        None,
        episode=episode,
        media_no=1,
        purpose="placeholder"
    )

    loaded = media.load()
    assert loaded.data is None


def test_media_with_empty_bytes(webtoon_instance: Webtoon):
    """빈 bytes로 미디어 추가"""
    episode = webtoon_instance.episode.add(id=16, name="Empty Bytes Test")

    media = webtoon_instance.media.add(
        b"",
        episode=episode,
        media_no=1,
        purpose="empty"
    )

    loaded = media.load()
    assert loaded.data == b""


def test_media_with_large_data(webtoon_instance: Webtoon):
    """큰 데이터로 미디어 추가"""
    episode = webtoon_instance.episode.add(id=17, name="Large Data Test")

    large_data = b"x" * (1024 * 1024)  # 1MB
    media = webtoon_instance.media.add(
        large_data,
        episode=episode,
        media_no=1,
        purpose="large"
    )

    loaded = media.load()
    assert isinstance(loaded.data, bytes)
    assert len(loaded.data) == 1024 * 1024


# ===== WebtoonMedia 생성 및 상태 관리 테스트 =====


def test_webtoon_media_from_media_data(webtoon_instance: Webtoon):
    """WebtoonMediaData로 WebtoonMedia 생성"""
    from wbtn._managers import WebtoonMedia

    episode = webtoon_instance.episode.add(id=18, name="From Data Test")

    media = webtoon_instance.media.add(
        b"test",
        episode=episode,
        media_no=1,
        purpose="image"
    )

    media_data = media.load()
    new_media = WebtoonMedia.from_media(media_data)

    assert new_media.loaded is True
    assert new_media.load() == media_data


def test_webtoon_media_invalid_init_raises(webtoon_instance: Webtoon):
    """잘못된 초기화 파라미터는 ValueError 발생"""
    from wbtn._managers import WebtoonMedia, WebtoonMediaData
    import datetime

    # media와 media_id 모두 제공
    with pytest.raises(ValueError, match="Only one of"):
        WebtoonMedia(  # type: ignore
            media_id=1,
            webtoon=webtoon_instance,
            media=WebtoonMediaData(
                media_id=1,
                episode_no=1,
                media_no=1,
                purpose="test",
                media_type="image/jpeg",  # type: ignore
                name="test.jpg",  # type: ignore
                state=None,
                conversion=None,
                path=None,
                data=b"test",
                added_at=datetime.datetime.now()
            )
        )

    # media_id만 제공 (webtoon 없이)
    with pytest.raises(ValueError, match="must be provided with webtoon"):
        WebtoonMedia(media_id=1)  # type: ignore


def test_webtoon_media_media_id_with_store(webtoon_instance: Webtoon):
    """media_id() 메서드의 store_id 옵션"""
    from wbtn._managers import WebtoonMedia

    episode = webtoon_instance.episode.add(id=19, name="Store ID Test")

    media = webtoon_instance.media.add(
        b"test",
        episode=episode,
        media_no=1,
        purpose="image"
    )

    # load로 데이터 저장
    media.load(store_media=True)
    assert media.loaded is True

    # media_id 호출 시 ID 저장
    media_id = media.media_id(store_id=True)
    assert media.loaded is False
    assert media.media_id() == media_id


def test_webtoon_media_stored_property(webtoon_instance: Webtoon):
    """WebtoonMedia의 stored 속성"""
    from wbtn._managers import WebtoonMediaData

    episode = webtoon_instance.episode.add(id=20, name="Stored Test")

    media = webtoon_instance.media.add(
        b"test",
        episode=episode,
        media_no=1,
        purpose="image"
    )

    # 처음엔 media_id 저장
    stored = media.stored
    assert isinstance(stored, int)

    # load 후엔 WebtoonMediaData 저장
    media.load(store_media=True)
    stored = media.stored
    assert isinstance(stored, WebtoonMediaData)


# ===== set 메서드 에러 처리 테스트 =====


def test_set_media_path_without_conversion_raises(webtoon_instance: Webtoon):
    """path가 있는데 conversion이 없으면 ValueError"""
    episode = webtoon_instance.episode.add(id=21, name="Set Error Test")

    media = webtoon_instance.media.add(
        b"test",
        episode=episode,
        media_no=1,
        purpose="image"
    )

    media_data = media.load()
    media_data.path = Path("/some/path.jpg")
    media_data.conversion = None

    with pytest.raises(ValueError, match="Both path and conversion"):
        webtoon_instance.media.set(media_data)


def test_set_media_conversion_without_path_raises(webtoon_instance: Webtoon):
    """conversion이 있는데 path가 없으면 ValueError"""
    episode = webtoon_instance.episode.add(id=22, name="Set Error Test 2")

    media = webtoon_instance.media.add(
        b"test",
        episode=episode,
        media_no=1,
        purpose="image"
    )

    media_data = media.load()
    media_data.path = None
    media_data.conversion = "bytes"

    with pytest.raises(ValueError, match="Both path and conversion"):
        webtoon_instance.media.set(media_data)


def test_set_media_both_path_and_data_raises(webtoon_instance: Webtoon):
    """path와 data가 모두 있으면 ValueError"""
    episode = webtoon_instance.episode.add(id=23, name="Set Error Test 3")

    media = webtoon_instance.media.add(
        b"test",
        episode=episode,
        media_no=1,
        purpose="image"
    )

    media_data = media.load()
    media_data.path = Path("/some/path.jpg")
    media_data.data = b"some data"
    media_data.conversion = "bytes"

    with pytest.raises(ValueError, match="Only data or path"):
        webtoon_instance.media.set(media_data)


def test_set_media_nonexistent_media_raises(webtoon_instance: Webtoon):
    """존재하지 않는 미디어 업데이트 시 KeyError"""
    from wbtn._managers import WebtoonMediaData
    import datetime

    webtoon_instance.episode.add(id=24, name="Set Nonexistent")

    fake_media = WebtoonMediaData(
        media_id=99999,
        episode_no=1,
        media_no=1,
        purpose="fake",
        media_type="image/jpeg",  # type: ignore
        name="fake.jpg",  # type: ignore
        state=None,
        conversion=None,
        path=None,
        data=b"test",
        added_at=datetime.datetime.now()
    )

    with pytest.raises(KeyError):
        webtoon_instance.media.set(fake_media)


# ===== iterate 복합 필터링 테스트 =====


def test_iterate_all_media_with_none_filters(webtoon_instance: Webtoon):
    """모든 필터를 None으로 설정하면 전체 미디어 반환"""
    ep1 = webtoon_instance.episode.add(id=25, name="Ep 1")
    ep2 = webtoon_instance.episode.add(id=26, name="Ep 2")

    webtoon_instance.media.add(b"data1", episode=ep1, media_no=1, purpose="image")
    webtoon_instance.media.add(b"data2", episode=ep2, media_no=1, purpose="image")

    all_media = list(webtoon_instance.media.iterate(episode=None, purpose=None, state=None))
    assert len(all_media) >= 2


def test_iterate_with_multiple_filters(webtoon_instance: Webtoon):
    """여러 필터 동시 적용"""
    episode = webtoon_instance.episode.add(id=27, name="Multi Filter Test")

    webtoon_instance.media.add(
        b"data1",
        episode=episode,
        media_no=1,
        purpose="image",
        state="complete"
    )
    webtoon_instance.media.add(
        b"data2",
        episode=episode,
        media_no=2,
        purpose="thumbnail",
        state="complete"
    )
    webtoon_instance.media.add(
        b"data3",
        episode=episode,
        media_no=3,
        purpose="image",
        state="pending"
    )

    # episode, purpose="image", state="complete"
    filtered = list(webtoon_instance.media.iterate(
        episode=episode,
        purpose="image",
        state="complete"
    ))
    assert len(filtered) == 1


# ===== load_data의 store_data 옵션 테스트 =====


def test_load_data_with_store_data_true(tmp_path: Path, webtoon_instance: Webtoon):
    """store_data=True로 경로 데이터를 DB에 저장"""
    episode = webtoon_instance.episode.add(id=28, name="Store Data Test")

    media_file = tmp_path / "store_test.dat"
    media_file.write_bytes(b"file content")

    media = webtoon_instance.media.add(
        media_file,
        episode=episode,
        media_no=1,
        purpose="data",
        conversion="bytes"
    )

    # 처음엔 path가 있음
    data_before = media.load()
    assert data_before.path is not None
    assert data_before.data is None

    # store_data=True로 로드
    loaded_data = webtoon_instance.media.load_data(media, store_data=True)

    # 이제 data가 있고 path는 None
    data_after = media.load()
    assert data_after.path is None
    assert data_after.data is not None


def test_load_data_from_data_media(webtoon_instance: Webtoon):
    """데이터 기반 미디어에서 load_data는 그냥 데이터 반환"""
    episode = webtoon_instance.episode.add(id=29, name="Data Media Test")

    media = webtoon_instance.media.add(
        b"direct data",
        episode=episode,
        media_no=1,
        purpose="image"
    )

    loaded_data = webtoon_instance.media.load_data(media)
    assert loaded_data == b"direct data"


# ===== dump_path 추가 테스트 =====


def test_dump_path_already_has_path_returns_existing(tmp_path: Path, webtoon_instance: Webtoon):
    """이미 경로가 있으면 기존 경로 반환"""
    episode = webtoon_instance.episode.add(id=30, name="Existing Path Test")

    existing_file = tmp_path / "existing.dat"
    existing_file.write_bytes(b"existing")

    media = webtoon_instance.media.add(
        existing_file,
        episode=episode,
        media_no=1,
        purpose="data",
        conversion="bytes"
    )

    # dump_path 호출해도 기존 경로 반환
    output_path = tmp_path / "new.dat"
    result_path = webtoon_instance.media.dump_path(media, output_path)

    assert result_path == existing_file
    assert not output_path.exists()  # 새 파일은 생성되지 않음


def test_dump_path_creates_parent_directories(tmp_path: Path, webtoon_instance: Webtoon):
    """dump_path가 부모 디렉터리 자동 생성"""
    episode = webtoon_instance.episode.add(id=31, name="Parent Dir Test")

    media = webtoon_instance.media.add(
        b"test data",
        episode=episode,
        media_no=1,
        purpose="image"
    )

    deep_path = tmp_path / "level1" / "level2" / "level3" / "file.dat"
    webtoon_instance.path.initialize_base_path(tmp_path)
    webtoon_instance.media.dump_path(media, deep_path)

    assert deep_path.exists()
    assert deep_path.parent.exists()


# ===== add_path_or_data 추가 테스트 =====


def test_add_path_or_data_self_contained_uses_data(webtoon_instance: Webtoon):
    """self_contained 모드에서는 파일 생성 안 하고 데이터로 저장"""
    from pathlib import Path as PathType

    episode = webtoon_instance.episode.add(id=32, name="Self Contained Test")
    webtoon_instance.path.self_contained = True

    fake_path = PathType("/fake/path.jpg")

    media = webtoon_instance.media.add_path_or_data(
        path=fake_path,
        data=b"image data",
        episode=episode,
        media_no=1,
        purpose="image"
    )

    loaded = media.load()
    assert loaded.data == b"image data"
    assert loaded.path is None


def test_add_path_or_data_mkdir_false(tmp_path: Path):
    """mkdir=False면 부모 디렉터리 생성 안 함"""
    db_path = tmp_path / "test.wbtn"
    media_path = tmp_path / "nonexistent" / "file.jpg"

    with Webtoon(db_path) as webtoon:
        episode = webtoon.episode.add(id=33, name="No Mkdir Test")
        webtoon.path.initialize_base_path(tmp_path)

        with pytest.raises(FileNotFoundError):
            webtoon.media.add_path_or_data(
                path=media_path,
                data=b"data",
                episode=episode,
                media_no=1,
                purpose="image",
                mkdir=False
            )


def test_add_path_or_data_rollback_on_error(tmp_path: Path):
    """에러 발생 시 생성된 파일 롤백"""
    db_path = tmp_path / "test.wbtn"
    media_path = tmp_path / "rollback.jpg"

    with Webtoon(db_path) as webtoon:
        episode = webtoon.episode.add(id=34, name="Rollback Test")
        webtoon.path.initialize_base_path(tmp_path)

        # 잘못된 WebtoonEpisode 객체로 에러 유발
        # 존재하지 않는 가짜 에피소드
        fake_episode = WebtoonEpisode(9999, "fake", None, 111, datetime.datetime.now())

        with pytest.raises(Exception):
            # 데이터베이스에 문제를 일으킬 상황 만들기
            webtoon.media.add_path_or_data(
                path=media_path,
                data=b"data",
                episode=fake_episode,
                media_no=1,
                purpose="image"
            )

        # 파일이 생성되지 않았거나 롤백되었는지 확인
        # (에러 시 unlink가 호출되므로)
        assert not media_path.exists()


# ===== conversion 파라미터 에러 테스트 =====


def test_add_with_data_and_conversion_raises(webtoon_instance: Webtoon):
    """데이터와 함께 conversion 파라미터 제공 시 ValueError"""
    episode = webtoon_instance.episode.add(id=35, name="Conversion Error Test")

    with pytest.raises(ValueError, match="conversion cannot be provided"):
        webtoon_instance.media.add(
            b"data",  # type: ignore
            episode=episode,
            media_no=1,
            purpose="image",
            conversion="bytes"
        )


# ===== 미디어 타입과 이름 관련 테스트 =====


def test_media_with_all_metadata_fields(webtoon_instance: Webtoon):
    """모든 메타데이터 필드를 포함한 미디어"""
    episode = webtoon_instance.episode.add(id=36, name="Full Metadata Test")

    media = webtoon_instance.media.add(
        b"image data",
        episode=episode,
        media_no=1,
        purpose="image",
        state="complete",
        media_type="image/png",
        media_name="hero_image.png"
    )

    loaded = media.load()
    assert loaded.state == "complete"
    assert loaded.media_type == "image/png"
    assert loaded.name == "hero_image.png"


def test_media_type_various_formats(webtoon_instance: Webtoon):
    """다양한 미디어 타입"""
    episode = webtoon_instance.episode.add(id=37, name="Media Types Test")

    types = [
        ("image/jpeg", b"jpg data"),
        ("image/png", b"png data"),
        ("image/webp", b"webp data"),
        ("application/json", b'{"key": "value"}'),
        ("text/plain", b"text data"),
    ]

    for i, (media_type, data) in enumerate(types):
        media = webtoon_instance.media.add(
            data,
            episode=episode,
            media_no=i + 1,
            purpose="content",
            media_type=media_type
        )

        loaded = media.load()
        assert loaded.media_type == media_type


# ===== added_at 타임스탬프 테스트 =====


def test_media_added_at_timestamp(webtoon_instance: Webtoon):
    """added_at이 현재 시간으로 설정됨"""
    import datetime

    episode = webtoon_instance.episode.add(id=38, name="Timestamp Test")

    before_time = datetime.datetime.now()
    media = webtoon_instance.media.add(
        b"data",
        episode=episode,
        media_no=1,
        purpose="image"
    )
    after_time = datetime.datetime.now()

    loaded = media.load()
    assert isinstance(loaded.added_at, datetime.datetime)
    # 약간의 시간 여유를 두고 확인 (초 단위)
    assert (before_time - datetime.timedelta(seconds=1)) <= loaded.added_at <= (after_time + datetime.timedelta(seconds=1))


# ===== remove 추가 테스트 =====


def test_remove_nonexistent_media_raises(webtoon_instance: Webtoon):
    """존재하지 않는 미디어 삭제 시 KeyError"""
    from wbtn._managers import WebtoonMedia

    # 존재하지 않는 media_id로 WebtoonMedia 생성
    fake_media = WebtoonMedia.from_media_id(99999, webtoon_instance)

    with pytest.raises(KeyError):
        webtoon_instance.media.remove(fake_media)


def test_remove_media_with_path_keeps_file(tmp_path: Path, webtoon_instance: Webtoon):
    """미디어 삭제해도 실제 파일은 유지됨"""
    episode = webtoon_instance.episode.add(id=39, name="Remove Path Test")

    media_file = tmp_path / "keep_file.jpg"
    media_file.write_bytes(b"file content")

    media = webtoon_instance.media.add(
        media_file,
        episode=episode,
        media_no=1,
        purpose="image",
        conversion="bytes"
    )

    webtoon_instance.media.remove(media)

    # 파일은 여전히 존재
    assert media_file.exists()


# ===== 복합 시나리오 테스트 =====


def test_complete_media_workflow(tmp_path: Path):
    """전체 미디어 워크플로우"""
    db_path = tmp_path / "workflow.wbtn"

    with Webtoon(db_path) as webtoon:
        webtoon.path.initialize_base_path(tmp_path)

        # 에피소드 생성
        episode = webtoon.episode.add(id=40, name="Episode 1")

        # 여러 미디어 추가
        for i in range(5):
            webtoon.media.add(
                f"image_{i}".encode(),
                episode=episode,
                media_no=i + 1,
                purpose="image",
                media_type="image/jpeg",
                media_name=f"img_{i:03d}.jpg"
            )

        # 조회
        all_media = list(webtoon.media.iterate(episode=episode))
        assert len(all_media) == 5

        # 수정
        first_media = all_media[0]
        data = first_media.load()
        data.state = "complete"
        webtoon.media.set(data)

        # 삭제
        webtoon.media.remove(all_media[-1])

        # 최종 확인
        remaining = list(webtoon.media.iterate(episode=episode))
        assert len(remaining) == 4
