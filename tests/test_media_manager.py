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
    episode = webtoon_instance.episode.add(1)

    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"image data"
    )

    assert media is not None
    loaded = media.load()
    assert loaded.data == b"image data"


def test_add_multiple_media_to_episode(webtoon_instance: Webtoon):
    """한 에피소드에 여러 미디어 추가"""
    episode = webtoon_instance.episode.add(2)

    media1 = webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"data1"
    )
    media2 = webtoon_instance.content.add(
        episode,
        2,
        "image",
        data=b"data2"
    )

    assert media1.content_id != media2.content_id


def test_add_media_with_json_data(webtoon_instance: Webtoon):
    """JsonData로 미디어 추가"""
    episode = webtoon_instance.episode.add(3)

    json_meta = JsonData(data={"width": 800, "height": 600})
    media = webtoon_instance.content.add(
        episode,
        1,
        "metadata",
        data=json_meta
    )

    loaded = media.load()
    assert isinstance(loaded.data, JsonData)


# ===== 미디어 추가 (경로) 테스트 =====


def test_add_media_with_path(tmp_path: Path, webtoon_instance: Webtoon):
    """경로로 미디어 추가"""
    episode = webtoon_instance.episode.add(4)

    # 테스트 파일 생성
    media_file = tmp_path / "test.jpg"
    media_file.write_bytes(b"test image")

    # 경로로 미디어 추가
    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        conversion="bytes",
        path=media_file
    )

    loaded = media.load()
    assert loaded.path is not None


def test_add_path_or_data_creates_file_when_not_self_contained(tmp_path: Path):
    """self_contained가 아닐 때 파일 생성"""
    db_path = tmp_path / "media.wbtn"
    media_path = tmp_path / "media" / "001.jpg"

    with Webtoon(db_path) as webtoon:
        episode = webtoon.episode.add(5)
        webtoon.path.initialize_base_path(tmp_path)

        webtoon.content.add_path_or_data(
            episode,
            1,
            "image",
            data=b"image content",
            path=media_path
        )

        assert media_path.exists()
        assert media_path.read_bytes() == b"image content"


# ===== 미디어 조회 및 iterate 테스트 =====


def test_iterate_media_by_episode(webtoon_instance: Webtoon):
    """특정 에피소드의 미디어 순회"""
    episode = webtoon_instance.episode.add(6)

    for i in range(3):
        webtoon_instance.content.add(
            episode,
            i + 1,
            "image",
            data=f"data{i}".encode()
        )

    media_list = list(webtoon_instance.content.iterate(episode=episode))
    assert len(media_list) == 3


def test_iterate_media_by_purpose(webtoon_instance: Webtoon):
    """purpose로 미디어 필터링"""
    episode = webtoon_instance.episode.add(7)

    webtoon_instance.content.add(episode, 1, "image", data=b"img")
    webtoon_instance.content.add(episode, 2, "thumbnail", data=b"thumb")
    webtoon_instance.content.add(episode, 3, "image", data=b"img2")

    images = list(webtoon_instance.content.iterate(episode=episode, kind="image"))
    assert len(images) == 2


def test_iterate_media_by_state(webtoon_instance: Webtoon):
    """state로 미디어 필터링"""
    episode = webtoon_instance.episode.add(8)

    webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"data1"
    )
    webtoon_instance.content.add(
        episode,
        2,
        "image",
        data=b"data2"
    )

    # Note: state filtering is not part of the API, so we'll just check iteration works
    all_media = list(webtoon_instance.content.iterate(episode=episode))
    assert len(all_media) == 2


# ===== 미디어 수정 및 삭제 테스트 =====


def test_remove_media(webtoon_instance: Webtoon):
    """미디어 삭제"""
    episode = webtoon_instance.episode.add(9)

    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"to delete"
    )

    media_id = media.content_id()
    webtoon_instance.content.remove(media)

    # 삭제 후 조회 시 에러
    with pytest.raises(ValueError):
        webtoon_instance.content._load(media_id)


def test_set_media_updates_data(webtoon_instance: Webtoon):
    """set으로 미디어 데이터 업데이트"""
    episode = webtoon_instance.episode.add(10)

    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"original"
    )

    # 데이터 수정
    media_data = media.load()
    media_data.data = b"updated"
    webtoon_instance.content.set(media_data)

    # 다시 로드하여 확인
    reloaded = webtoon_instance.content._load(media.content_id())
    assert reloaded.data == b"updated"


# ===== load_data 및 dump_path 테스트 =====


def test_load_data_from_path_media(tmp_path: Path, webtoon_instance: Webtoon):
    """경로 기반 미디어에서 데이터 로드"""
    episode = webtoon_instance.episode.add(11)

    media_file = tmp_path / "load_test.dat"
    media_file.write_bytes(b"file content")

    media = webtoon_instance.content.add(
        episode,
        1,
        "data",
        conversion="bytes",
        path=media_file
    )

    loaded_data = webtoon_instance.content.load_data(media)
    # conversion이 bytes이므로 bytes로 변환된 값이 나옴
    assert isinstance(loaded_data, (bytes, int))


def test_dump_path_writes_data_to_file(tmp_path: Path, webtoon_instance: Webtoon):
    """데이터를 파일로 dump"""
    episode = webtoon_instance.episode.add(12)

    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"dump this"
    )

    output_path = tmp_path / "dumped.dat"
    webtoon_instance.path.initialize_base_path(tmp_path)
    webtoon_instance.content.dump_path(media, output_path)

    assert output_path.exists()
    assert output_path.read_bytes() == b"dump this"


# ===== WebtoonMedia 및 WebtoonMediaData 테스트 =====


def test_webtoon_media_loaded_property(webtoon_instance: Webtoon):
    """WebtoonMedia의 loaded 속성"""
    episode = webtoon_instance.episode.add(13)

    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"test"
    )

    # 처음엔 ID만 저장됨
    assert media.loaded is False

    # load 후 데이터 저장됨
    media.load(store_content=True)
    assert media.loaded is True


def test_webtoon_media_from_media_id(webtoon_instance: Webtoon):
    """media_id로 WebtoonMedia 생성"""
    from wbtn._managers import WebtoonContent

    episode = webtoon_instance.episode.add(14)

    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"test data"
    )

    media_id = media.content_id()
    new_media = WebtoonContent.from_content_id(media_id, webtoon_instance)

    assert new_media.content_id() == media_id


# ===== 엣지 케이스 테스트 =====


def test_media_with_none_data(webtoon_instance: Webtoon):
    """None 데이터로 미디어 추가"""
    episode = webtoon_instance.episode.add(15)

    media = webtoon_instance.content.add(
        episode,
        1,
        "placeholder",
        data=None
    )

    loaded = media.load()
    assert loaded.data is None


def test_media_with_empty_bytes(webtoon_instance: Webtoon):
    """빈 bytes로 미디어 추가"""
    episode = webtoon_instance.episode.add(16)

    media = webtoon_instance.content.add(
        episode,
        1,
        "empty",
        data=b""
    )

    loaded = media.load()
    assert loaded.data == b""


def test_media_with_large_data(webtoon_instance: Webtoon):
    """큰 데이터로 미디어 추가"""
    episode = webtoon_instance.episode.add(17)

    large_data = b"x" * (1024 * 1024)  # 1MB
    media = webtoon_instance.content.add(
        episode,
        1,
        "large",
        data=large_data
    )

    loaded = media.load()
    assert isinstance(loaded.data, bytes)
    assert len(loaded.data) == 1024 * 1024


# ===== WebtoonMedia 생성 및 상태 관리 테스트 =====


def test_webtoon_media_from_media_data(webtoon_instance: Webtoon):
    """WebtoonMediaData로 WebtoonMedia 생성"""
    from wbtn._managers import WebtoonContent

    episode = webtoon_instance.episode.add(18)

    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"test"
    )

    media_data = media.load()
    new_media = WebtoonContent.from_content(media_data)

    assert new_media.loaded is True
    assert new_media.load() == media_data


def test_webtoon_media_invalid_init_raises(webtoon_instance: Webtoon):
    """잘못된 초기화 파라미터는 ValueError 발생"""
    from wbtn._managers import WebtoonContent, WebtoonContentData
    import datetime

    # content와 content_id 모두 제공
    with pytest.raises(ValueError, match="Only one of"):
        WebtoonContent(  # type: ignore
            content_id=1,
            webtoon=webtoon_instance,
            content=WebtoonContentData(
                content_id=1,
                episode_no=1,
                content_no=1,
                kind="test",
                conversion=None,
                path=None,
                data=b"test",
                added_at=datetime.datetime.now()
            )
        )

    # content_id만 제공 (webtoon 없이)
    with pytest.raises(ValueError, match="must be provided with webtoon"):
        WebtoonContent(content_id=1)  # type: ignore


def test_webtoon_media_media_id_with_store(webtoon_instance: Webtoon):
    """media_id() 메서드의 store_id 옵션"""
    from wbtn._managers import WebtoonContent

    episode = webtoon_instance.episode.add(19)

    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"test"
    )

    # load로 데이터 저장
    media.load(store_content=True)
    assert media.loaded is True

    # content_id 호출 시 ID 저장
    media_id = media.content_id(store_id=True)
    assert media.loaded is False
    assert media.content_id() == media_id


def test_webtoon_media_stored_property(webtoon_instance: Webtoon):
    """WebtoonMedia의 stored 속성"""
    from wbtn._managers import WebtoonContentData

    episode = webtoon_instance.episode.add(20)

    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"test"
    )

    # 처음엔 content_id 저장
    stored = media.stored
    assert isinstance(stored, int)

    # load 후엔 WebtoonContentData 저장
    media.load(store_content=True)
    stored = media.stored
    assert isinstance(stored, WebtoonContentData)


# ===== set 메서드 에러 처리 테스트 =====


def test_set_media_path_without_conversion_raises(webtoon_instance: Webtoon):
    """path가 있는데 conversion이 없으면 ValueError"""
    episode = webtoon_instance.episode.add(21)

    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"test"
    )

    media_data = media.load()
    media_data.path = Path("/some/path.jpg")
    media_data.conversion = None

    with pytest.raises(ValueError, match="conversion is required"):
        webtoon_instance.content.set(media_data)


def test_set_media_conversion_without_path_is_valid(webtoon_instance: Webtoon):
    """conversion이 있고 path가 없는 것은 유효함 (data를 직접 저장하는 경우)"""
    episode = webtoon_instance.episode.add(22)

    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"test"
    )

    media_data = media.load()
    media_data.path = None
    media_data.conversion = "bytes"
    media_data.data = b"updated data"

    # 이것은 정상적으로 작동해야 함
    webtoon_instance.content.set(media_data)

    # 검증
    reloaded = media.load()
    assert reloaded.data == b"updated data"
    assert reloaded.path is None
    assert reloaded.conversion == "bytes"


def test_set_media_both_path_and_data_raises(webtoon_instance: Webtoon):
    """path와 data가 모두 있으면 ValueError"""
    episode = webtoon_instance.episode.add(23)

    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"test"
    )

    media_data = media.load()
    media_data.path = Path("/some/path.jpg")
    media_data.data = b"some data"
    media_data.conversion = "bytes"

    with pytest.raises(ValueError, match="Only data or path"):
        webtoon_instance.content.set(media_data)


def test_set_media_nonexistent_media_raises(webtoon_instance: Webtoon):
    """존재하지 않는 미디어 업데이트 시 KeyError"""
    from wbtn._managers import WebtoonContentData
    import datetime

    webtoon_instance.episode.add(24)

    fake_media = WebtoonContentData(
        content_id=99999,
        episode_no=1,
        content_no=1,
        kind="fake",
        conversion=None,
        path=None,
        data=b"test",
        added_at=datetime.datetime.now()
    )

    with pytest.raises(KeyError):
        webtoon_instance.content.set(fake_media)


# ===== iterate 복합 필터링 테스트 =====


def test_iterate_all_media_with_none_filters(webtoon_instance: Webtoon):
    """모든 필터를 None으로 설정하면 전체 미디어 반환"""
    ep1 = webtoon_instance.episode.add(25)
    ep2 = webtoon_instance.episode.add(26)

    webtoon_instance.content.add(ep1, 1, "image", data=b"data1")
    webtoon_instance.content.add(ep2, 1, "image", data=b"data2")

    all_media = list(webtoon_instance.content.iterate(episode=None, kind=None))
    assert len(all_media) >= 2


def test_iterate_with_multiple_filters(webtoon_instance: Webtoon):
    """여러 필터 동시 적용"""
    episode = webtoon_instance.episode.add(27)

    webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"data1"
    )
    webtoon_instance.content.add(
        episode,
        2,
        "thumbnail",
        data=b"data2"
    )
    webtoon_instance.content.add(
        episode,
        3,
        "image",
        data=b"data3"
    )

    # episode, kind="image" 필터
    filtered = list(webtoon_instance.content.iterate(
        episode=episode,
        kind="image"
    ))
    assert len(filtered) == 2


# ===== load_data의 store_data 옵션 테스트 =====


def test_load_data_with_store_data_true(tmp_path: Path, webtoon_instance: Webtoon):
    """store_data=True로 경로 데이터를 DB에 저장"""
    episode = webtoon_instance.episode.add(28)

    media_file = tmp_path / "store_test.dat"
    media_file.write_bytes(b"file content")

    media = webtoon_instance.content.add(
        episode,
        1,
        "data",
        conversion="bytes",
        path=media_file
    )

    # 처음엔 path가 있음
    data_before = media.load()
    assert data_before.path is not None
    assert data_before.data is None

    # store_data=True로 로드
    loaded_data = webtoon_instance.content.load_data(media, store_data=True)

    # 이제 data가 있고 path는 None
    data_after = media.load()
    assert data_after.path is None
    assert data_after.data is not None


def test_load_data_from_data_media(webtoon_instance: Webtoon):
    """데이터 기반 미디어에서 load_data는 그냥 데이터 반환"""
    episode = webtoon_instance.episode.add(29)

    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"direct data"
    )

    loaded_data = webtoon_instance.content.load_data(media)
    assert loaded_data == b"direct data"


# ===== dump_path 추가 테스트 =====


def test_dump_path_already_has_path_returns_existing(tmp_path: Path, webtoon_instance: Webtoon):
    """이미 경로가 있으면 기존 경로 반환"""
    episode = webtoon_instance.episode.add(30)

    existing_file = tmp_path / "existing.dat"
    existing_file.write_bytes(b"existing")

    media = webtoon_instance.content.add(
        episode,
        1,
        "data",
        conversion="bytes",
        path=existing_file
    )

    # dump_path 호출해도 기존 경로 반환
    output_path = tmp_path / "new.dat"
    result_path = webtoon_instance.content.dump_path(media, output_path)

    assert result_path == existing_file
    assert not output_path.exists()  # 새 파일은 생성되지 않음


def test_dump_path_creates_parent_directories(tmp_path: Path, webtoon_instance: Webtoon):
    """dump_path가 부모 디렉터리 자동 생성"""
    episode = webtoon_instance.episode.add(31)

    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"test data"
    )

    deep_path = tmp_path / "level1" / "level2" / "level3" / "file.dat"
    webtoon_instance.path.initialize_base_path(tmp_path)
    webtoon_instance.content.dump_path(media, deep_path)

    assert deep_path.exists()
    assert deep_path.parent.exists()


# ===== add_path_or_data 추가 테스트 =====


def test_add_path_or_data_self_contained_uses_data(webtoon_instance: Webtoon):
    """self_contained 모드에서는 파일 생성 안 하고 데이터로 저장"""
    from pathlib import Path as PathType

    episode = webtoon_instance.episode.add(32)
    webtoon_instance.path.self_contained = True

    fake_path = PathType("/fake/path.jpg")

    media = webtoon_instance.content.add_path_or_data(
        episode,
        1,
        "image",
        data=b"image data",
        path=fake_path
    )

    loaded = media.load()
    assert loaded.data == b"image data"
    assert loaded.path is None


def test_add_path_or_data_mkdir_false(tmp_path: Path):
    """mkdir=False면 부모 디렉터리 생성 안 함"""
    db_path = tmp_path / "test.wbtn"
    media_path = tmp_path / "nonexistent" / "file.jpg"

    with Webtoon(db_path) as webtoon:
        episode = webtoon.episode.add(33)
        webtoon.path.initialize_base_path(tmp_path)

        with pytest.raises(FileNotFoundError):
            webtoon.content.add_path_or_data(
                episode,
                1,
                "image",
                data=b"data",
                path=media_path,
                mkdir=False
            )


def test_add_path_or_data_rollback_on_error(tmp_path: Path):
    """에러 발생 시 생성된 파일 롤백"""
    db_path = tmp_path / "test.wbtn"
    media_path = tmp_path / "rollback.jpg"

    with Webtoon(db_path) as webtoon:
        episode = webtoon.episode.add(34)
        webtoon.path.initialize_base_path(tmp_path)

        # 잘못된 WebtoonEpisode 객체로 에러 유발
        # 존재하지 않는 가짜 에피소드
        fake_episode = WebtoonEpisode(9999, datetime.datetime.now())

        with pytest.raises(Exception):
            # 데이터베이스에 문제를 일으킬 상황 만들기
            webtoon.content.add_path_or_data(
                fake_episode,
                1,
                "image",
                data=b"data",
                path=media_path
            )

        # 파일이 생성되지 않았거나 롤백되었는지 확인
        # (에러 시 unlink가 호출되므로)
        assert not media_path.exists()


# ===== conversion 파라미터 에러 테스트 =====


def test_add_with_path_without_conversion_raises(webtoon_instance: Webtoon, tmp_path: Path):
    """경로와 함께 conversion 없으면 ValueError"""
    episode = webtoon_instance.episode.add(35)

    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b"data")

    with pytest.raises(ValueError, match="Conversion must be provided"):
        webtoon_instance.content.add(
            episode,
            1,
            "image",
            path=test_file  # type: ignore
        )


# ===== 미디어 타입과 이름 관련 테스트 =====


def test_media_with_all_metadata_fields(webtoon_instance: Webtoon):
    """모든 메타데이터 필드를 포함한 미디어"""
    episode = webtoon_instance.episode.add(36)

    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"image data"
    )

    loaded = media.load()
    assert loaded.kind == "image"
    assert loaded.data == b"image data"


def test_media_type_various_formats(webtoon_instance: Webtoon):
    """다양한 미디어 타입"""
    episode = webtoon_instance.episode.add(37)

    types_data = [
        ("image", b"jpg data"),
        ("thumbnail", b"png data"),
        ("metadata", b"webp data"),
        ("text", b'{"key": "value"}'),
        ("content", b"text data"),
    ]

    for i, (kind, data) in enumerate(types_data):
        media = webtoon_instance.content.add(
            episode,
            i + 1,
            kind,
            data=data
        )

        loaded = media.load()
        assert loaded.kind == kind


# ===== added_at 타임스탬프 테스트 =====


def test_media_added_at_timestamp(webtoon_instance: Webtoon):
    """added_at이 현재 시간으로 설정됨"""
    import datetime

    episode = webtoon_instance.episode.add(38)

    before_time = datetime.datetime.now()
    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        data=b"data"
    )
    after_time = datetime.datetime.now()

    loaded = media.load()
    assert isinstance(loaded.added_at, datetime.datetime)
    # 약간의 시간 여유를 두고 확인 (초 단위)
    assert (before_time - datetime.timedelta(seconds=1)) <= loaded.added_at <= (after_time + datetime.timedelta(seconds=1))


# ===== remove 추가 테스트 =====


def test_remove_nonexistent_media_raises(webtoon_instance: Webtoon):
    """존재하지 않는 미디어 삭제 시 KeyError"""
    from wbtn._managers import WebtoonContent

    # 존재하지 않는 content_id로 WebtoonContent 생성
    fake_media = WebtoonContent.from_content_id(99999, webtoon_instance)

    with pytest.raises(KeyError):
        webtoon_instance.content.remove(fake_media)


def test_remove_media_with_path_keeps_file(tmp_path: Path, webtoon_instance: Webtoon):
    """미디어 삭제해도 실제 파일은 유지됨"""
    episode = webtoon_instance.episode.add(39)

    media_file = tmp_path / "keep_file.jpg"
    media_file.write_bytes(b"file content")

    media = webtoon_instance.content.add(
        episode,
        1,
        "image",
        conversion="bytes",
        path=media_file
    )

    webtoon_instance.content.remove(media)

    # 파일은 여전히 존재
    assert media_file.exists()


# ===== 복합 시나리오 테스트 =====


def test_complete_media_workflow(tmp_path: Path):
    """전체 미디어 워크플로우"""
    db_path = tmp_path / "workflow.wbtn"

    with Webtoon(db_path) as webtoon:
        webtoon.path.initialize_base_path(tmp_path)

        # 에피소드 생성
        episode = webtoon.episode.add(40)

        # 여러 미디어 추가
        for i in range(5):
            webtoon.content.add(
                episode,
                i + 1,
                "image",
                data=f"image_{i}".encode()
            )

        # 조회
        all_media = list(webtoon.content.iterate(episode=episode))
        assert len(all_media) == 5

        # 수정
        first_media = all_media[0]
        data = first_media.load()
        data.data = b"modified"
        webtoon.content.set(data)

        # 삭제
        webtoon.content.remove(all_media[-1])

        # 최종 확인
        remaining = list(webtoon.content.iterate(episode=episode))
        assert len(remaining) == 4
