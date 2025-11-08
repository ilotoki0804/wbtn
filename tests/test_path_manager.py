"""
WebtoonPathManager에 대한 포괄적인 테스트
경로 dump/load, base_path 관리, self_contained 모드 등을 테스트합니다.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbtn import Webtoon
from wbtn._base import WebtoonPathError, WebtoonPathInitializationError


# ===== base_path 초기화 테스트 =====


def test_auto_initialize_base_path(tmp_path: Path):
    """base_path 자동 초기화"""
    db_path = tmp_path / "path_test.wbtn"

    with Webtoon(db_path) as webtoon:
        # 자동으로 초기화됨
        base = webtoon.path.base_path
        assert base is not None
        # 기본값은 webtoon 파일의 부모 디렉토리
        assert base == tmp_path


def test_manual_initialize_base_path(tmp_path: Path, webtoon_instance: Webtoon):
    """수동으로 base_path 초기화"""
    custom_base = tmp_path / "custom_base"
    custom_base.mkdir()

    webtoon_instance.path.initialize_base_path(custom_base)
    assert webtoon_instance.path.base_path == custom_base.resolve()


def test_base_path_property_setter(tmp_path: Path, webtoon_instance: Webtoon):
    """base_path 속성으로 설정"""
    new_base = tmp_path / "new_base"
    new_base.mkdir()

    webtoon_instance.path.base_path = new_base
    assert webtoon_instance.path.base_path == new_base.resolve()


def test_file_base_path_returns_db_parent(tmp_path: Path):
    """file_base_path는 DB 파일의 부모 디렉토리 반환"""
    db_path = tmp_path / "subdir" / "test.wbtn"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with Webtoon(db_path) as webtoon:
        file_base = webtoon.path.file_base_path()
        assert file_base == db_path.parent


def test_file_base_path_for_memory_returns_cwd():
    """메모리 DB는 cwd 반환"""
    with Webtoon(":memory:") as webtoon:
        file_base = webtoon.path.file_base_path()
        assert file_base == Path.cwd()


# ===== dump 및 load 테스트 =====


def test_dump_and_load_relative_path(tmp_path: Path, webtoon_instance: Webtoon):
    """상대 경로 dump 및 load"""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    webtoon_instance.path.initialize_base_path(base_dir)

    test_path = base_dir / "subdir" / "file.txt"
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.touch()

    # dump
    dumped = webtoon_instance.path.dump(test_path)
    assert dumped == "subdir/file.txt"

    # load
    loaded = webtoon_instance.path.load(dumped)
    assert loaded == test_path


def test_dump_absolute_path_converts_to_relative(tmp_path: Path, webtoon_instance: Webtoon):
    """절대 경로는 상대 경로로 변환"""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    webtoon_instance.path.initialize_base_path(base_dir)

    abs_path = (base_dir / "file.txt").resolve()

    dumped = webtoon_instance.path.dump(abs_path)
    assert dumped is not None
    assert not Path(dumped).is_absolute()
    assert dumped == "file.txt"


def test_dump_none_returns_none(webtoon_instance: Webtoon):
    """None을 dump하면 None 반환"""
    result = webtoon_instance.path.dump(None)
    assert result is None


def test_load_none_returns_none(webtoon_instance: Webtoon):
    """None을 load하면 None 반환"""
    result = webtoon_instance.path.load(None)
    assert result is None


def test_dump_str_and_load_str(tmp_path: Path, webtoon_instance: Webtoon):
    """문자열 경로 dump 및 load"""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    webtoon_instance.path.initialize_base_path(base_dir)

    test_path = base_dir / "test.txt"
    test_path.touch()

    dumped = webtoon_instance.path.dump_str(test_path)
    assert isinstance(dumped, str)

    loaded = webtoon_instance.path.load_str(dumped)
    assert loaded == test_path


# ===== convert_absolute 설정 테스트 =====


def test_convert_absolute_true_allows_conversion(tmp_path: Path, webtoon_instance: Webtoon):
    """convert_absolute=True이면 절대 경로를 상대 경로로 변환"""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    webtoon_instance.path.initialize_base_path(base_dir)
    webtoon_instance.path.convert_absolute = True

    abs_path = (base_dir / "file.txt").resolve()
    dumped = webtoon_instance.path.dump(abs_path)

    assert dumped is not None
    assert not Path(dumped).is_absolute()


def test_convert_absolute_false_raises_error(tmp_path: Path, webtoon_instance: Webtoon):
    """convert_absolute=False이면 절대 경로는 에러"""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    webtoon_instance.path.initialize_base_path(base_dir)
    webtoon_instance.path.convert_absolute = False

    abs_path = (base_dir / "file.txt").resolve()

    with pytest.raises(WebtoonPathError, match="Absolute path cannot be stored"):
        webtoon_instance.path.dump(abs_path)


def test_load_absolute_path_raises_error(tmp_path: Path, webtoon_instance: Webtoon):
    """load 시 절대 경로는 항상 에러"""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    webtoon_instance.path.initialize_base_path(base_dir)

    abs_path_str = str((tmp_path / "file.txt").resolve())

    with pytest.raises(WebtoonPathError, match="Absolute path is not allowed"):
        webtoon_instance.path.load_str(abs_path_str)


# ===== self_contained 모드 테스트 =====


def test_self_contained_mode_prevents_dump(webtoon_instance: Webtoon):
    """self_contained 모드에서는 dump 불가"""
    webtoon_instance.path.self_contained = True

    with pytest.raises(WebtoonPathError, match="Self-contained mode"):
        webtoon_instance.path.dump(Path("/some/path"))


def test_self_contained_mode_prevents_load(webtoon_instance: Webtoon):
    """self_contained 모드에서는 load 불가"""
    webtoon_instance.path.self_contained = True

    with pytest.raises(WebtoonPathError, match="Self-contained mode"):
        webtoon_instance.path.load("some/path")


def test_self_contained_mode_prevents_base_path_access(webtoon_instance: Webtoon):
    """self_contained 모드에서는 base_path 접근 불가"""
    webtoon_instance.path.self_contained = True

    with pytest.raises(WebtoonPathError, match="Self-contained mode"):
        _ = webtoon_instance.path.base_path


# ===== auto_initialize_base_path 설정 테스트 =====


def test_auto_initialize_disabled_raises_error(webtoon_instance: Webtoon):
    """auto_initialize=False이고 초기화하지 않으면 에러"""
    webtoon_instance.path.auto_initialize_base_path = False

    with pytest.raises(WebtoonPathInitializationError, match="not yet initialized"):
        _ = webtoon_instance.path.base_path


def test_manual_initialize_when_auto_disabled(tmp_path: Path, webtoon_instance: Webtoon):
    """auto_initialize=False여도 수동 초기화는 가능"""
    webtoon_instance.path.auto_initialize_base_path = False

    custom_base = tmp_path / "manual"
    custom_base.mkdir()
    webtoon_instance.path.initialize_base_path(custom_base)

    assert webtoon_instance.path.base_path == custom_base.resolve()


# ===== suggested_base_path 테스트 =====


def test_suggested_base_path_from_info(tmp_path: Path, webtoon_instance: Webtoon):
    """info에서 제안된 base_path 읽기"""
    suggested = tmp_path / "suggested"
    suggested.mkdir()

    webtoon_instance.info.set("sys_base_directory", str(suggested), system=True)

    result = webtoon_instance.path.suggested_base_path()
    assert result == suggested


def test_suggested_base_path_none_when_not_set(webtoon_instance: Webtoon):
    """설정되지 않으면 None 반환"""
    # sys_base_directory 삭제
    if "sys_base_directory" in webtoon_instance.info:
        webtoon_instance.info.set("sys_base_directory", None, system=True)

    result = webtoon_instance.path.suggested_base_path()
    assert result is None


def test_suggested_base_path_with_json_data(tmp_path: Path, webtoon_instance: Webtoon):
    """sys_base_directory가 JsonData로 저장되어 있을 때 처리"""
    from wbtn._json_data import JsonData

    suggested_path = "suggested_dir"
    # JsonData 형식으로 저장
    json_data = JsonData(data=suggested_path, conversion="json")
    webtoon_instance.info.set("sys_base_directory", json_data, system=True)

    result = webtoon_instance.path.suggested_base_path()
    assert result == Path(suggested_path)


def test_suggested_base_path_with_invalid_type(webtoon_instance: Webtoon):
    """sys_base_directory가 유효하지 않은 타입일 때 None 반환"""
    # int 같은 잘못된 타입 저장
    webtoon_instance.info.set("sys_base_directory", 12345, system=True)

    result = webtoon_instance.path.suggested_base_path()
    assert result is None


def test_suggested_base_path_with_bytes(webtoon_instance: Webtoon):
    """sys_base_directory가 bytes일 때 Path로 변환"""
    suggested_bytes = b"suggested_dir"
    webtoon_instance.info.set("sys_base_directory", suggested_bytes, system=True)

    result = webtoon_instance.path.suggested_base_path()
    assert result == Path("suggested_dir")


# ===== 에러 처리 테스트 =====


def test_dump_path_outside_base_raises_error(tmp_path: Path, webtoon_instance: Webtoon):
    """base_path 외부의 경로는 에러"""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    webtoon_instance.path.initialize_base_path(base_dir)

    outside_path = tmp_path / "outside" / "file.txt"
    outside_path.parent.mkdir(parents=True, exist_ok=True)

    with pytest.raises(ValueError):
        webtoon_instance.path.dump(outside_path)


def test_double_initialize_raises_error(tmp_path: Path, webtoon_instance: Webtoon):
    """이미 초기화된 base_path를 다시 초기화하면 에러"""
    base1 = tmp_path / "base1"
    base1.mkdir()
    webtoon_instance.path.initialize_base_path(base1)

    base2 = tmp_path / "base2"
    base2.mkdir()

    with pytest.raises(WebtoonPathInitializationError, match="already been initialized"):
        webtoon_instance.path._get_base_path(base2)


# ===== 엣지 케이스 테스트 =====


def test_dump_and_load_nested_path(tmp_path: Path, webtoon_instance: Webtoon):
    """깊이 중첩된 경로"""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    webtoon_instance.path.initialize_base_path(base_dir)

    nested_path = base_dir / "a" / "b" / "c" / "d" / "file.txt"
    nested_path.parent.mkdir(parents=True, exist_ok=True)
    nested_path.touch()

    dumped = webtoon_instance.path.dump(nested_path)
    assert dumped == "a/b/c/d/file.txt"

    loaded = webtoon_instance.path.load(dumped)
    assert loaded == nested_path


def test_dump_path_with_unicode_filename(tmp_path: Path, webtoon_instance: Webtoon):
    """유니코드 파일명"""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    webtoon_instance.path.initialize_base_path(base_dir)

    unicode_path = base_dir / "한글파일.txt"
    unicode_path.touch()

    dumped = webtoon_instance.path.dump(unicode_path)
    loaded = webtoon_instance.path.load(dumped)

    assert loaded == unicode_path


def test_dump_path_with_spaces(tmp_path: Path, webtoon_instance: Webtoon):
    """공백이 포함된 경로"""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    webtoon_instance.path.initialize_base_path(base_dir)

    spaced_path = base_dir / "folder with spaces" / "file name.txt"
    spaced_path.parent.mkdir(parents=True, exist_ok=True)
    spaced_path.touch()

    dumped = webtoon_instance.path.dump(spaced_path)
    loaded = webtoon_instance.path.load(dumped)

    assert loaded == spaced_path


def test_path_normalization(tmp_path: Path, webtoon_instance: Webtoon):
    """경로 정규화 (../. 등)"""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    webtoon_instance.path.initialize_base_path(base_dir)

    # 복잡한 경로
    file_path = base_dir / "subdir" / ".." / "file.txt"
    normalized = file_path.resolve()
    normalized.touch()

    dumped = webtoon_instance.path.dump(normalized)
    loaded = webtoon_instance.path.load(dumped)

    # 정규화된 경로와 동일해야 함
    assert loaded == normalized


# ===== _get_base_path 엣지 케이스 테스트 (공개 API를 통해) =====


def test_get_base_path_with_absolute_suggested_path_fallback_enabled(tmp_path: Path):
    """suggested_base_path가 절대 경로이고 fallback_base_path=True일 때 file_base_path로 fallback"""
    db_path = tmp_path / "test.wbtn"

    with Webtoon(db_path) as webtoon:
        # 절대 경로를 sys_base_directory에 저장
        webtoon.info.set("sys_base_directory", str(tmp_path / "absolute_path"), system=True)
        webtoon.path.fallback_base_path = True

        # initialize_base_path 호출 시 fallback되어야 함
        base = webtoon.path.initialize_base_path()
        assert base == db_path.parent


def test_get_base_path_with_absolute_suggested_path_fallback_disabled(tmp_path: Path):
    """suggested_base_path가 절대 경로이고 fallback_base_path=False일 때 에러 발생"""
    db_path = tmp_path / "test.wbtn"

    with Webtoon(db_path) as webtoon:
        # 절대 경로를 sys_base_directory에 저장
        webtoon.info.set("sys_base_directory", str(tmp_path / "absolute_path"), system=True)
        webtoon.path.fallback_base_path = False

        # 에러가 발생해야 함
        with pytest.raises(WebtoonPathInitializationError, match="absolute path"):
            webtoon.path.initialize_base_path()


def test_get_base_path_with_non_child_suggested_path_fallback_enabled(tmp_path: Path):
    """suggested_base_path가 webtoon 파일 폴더의 자식이 아니고 fallback_base_path=True일 때 fallback"""
    db_path = tmp_path / "subdir" / "test.wbtn"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with Webtoon(db_path) as webtoon:
        # 부모 폴더가 아닌 다른 경로를 suggested로 설정 (상대 경로)
        webtoon.info.set("sys_base_directory", "../../outside", system=True)
        webtoon.path.fallback_base_path = True

        # fallback되어 file_base_path 사용
        base = webtoon.path.initialize_base_path()
        assert base == db_path.parent


def test_get_base_path_with_non_child_suggested_path_fallback_disabled(tmp_path: Path):
    """suggested_base_path가 webtoon 파일 폴더의 자식이 아니고 fallback_base_path=False일 때 에러"""
    db_path = tmp_path / "subdir" / "test.wbtn"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with Webtoon(db_path) as webtoon:
        # 부모 폴더가 아닌 다른 경로를 suggested로 설정
        webtoon.info.set("sys_base_directory", "../../outside", system=True)
        webtoon.path.fallback_base_path = False

        # 에러가 발생해야 함
        with pytest.raises(WebtoonPathInitializationError, match="not a subtree"):
            webtoon.path.initialize_base_path()


def test_get_base_path_with_valid_suggested_path(tmp_path: Path):
    """suggested_base_path가 유효한 상대 경로일 때 정상 사용"""
    db_path = tmp_path / "test.wbtn"

    with Webtoon(db_path) as webtoon:
        # 유효한 상대 경로 - 하지만 실제로는 cwd 기준이므로 file_folder 밖에 있을 수 있음
        # 그런 경우 fallback됨
        suggested = "media"
        webtoon.info.set("sys_base_directory", suggested, system=True)

        base = webtoon.path.initialize_base_path()
        # 상대 경로가 file_folder 외부면 fallback되어 db_path.parent가 됨
        # 또는 내부라면 resolve된 경로가 됨
        # 안전하게 둘 중 하나를 확인
        assert base == Path(suggested).resolve() or base == db_path.parent


def test_get_base_path_with_valid_child_path(tmp_path: Path):
    """suggested_base_path가 webtoon 파일 폴더의 자식일 때 정상 사용"""
    db_path = tmp_path / "subdir" / "test.wbtn"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with Webtoon(db_path) as webtoon:
        # 상대 경로이면서 실제로 파일 폴더의 자식인 경로
        # 현재 작업 디렉토리를 변경하여 테스트
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            # 이제 "subdir/media"는 tmp_path 기준 상대 경로
            suggested = "subdir/media"
            webtoon.info.set("sys_base_directory", suggested, system=True)

            base = webtoon.path.initialize_base_path()
            # 정상적으로 설정되어야 함
            assert base == Path(suggested).resolve()
        finally:
            os.chdir(old_cwd)


def test_get_base_path_with_none_suggested_uses_file_base_path(tmp_path: Path):
    """suggested_base_path가 None일 때 file_base_path 사용"""
    db_path = tmp_path / "test.wbtn"

    with Webtoon(db_path) as webtoon:
        # sys_base_directory를 None으로 설정
        webtoon.info.set("sys_base_directory", None, system=True)

        base = webtoon.path.initialize_base_path()
        assert base == db_path.parent


def test_get_base_path_with_direct_path_argument(tmp_path: Path, webtoon_instance: Webtoon):
    """initialize_base_path에 직접 path를 제공하면 검증 없이 사용"""
    custom_path = tmp_path / "direct_custom"
    custom_path.mkdir()

    # 직접 제공한 path는 검증 없이 바로 사용됨
    base = webtoon_instance.path.initialize_base_path(custom_path)
    assert base == custom_path.resolve()


# ===== base_path 변경 시 media/extra_file path 저장 테스트 =====


def test_media_path_storage_with_custom_base_path(tmp_path: Path):
    """custom base_path 설정 시 media의 path가 올바르게 저장되고 로드됨"""
    db_path = tmp_path / "test.wbtn"
    base_dir = tmp_path / "media_base"
    base_dir.mkdir()

    with Webtoon(db_path) as webtoon:
        # custom base_path 설정
        webtoon.path.base_path = base_dir

        # 에피소드 추가
        episode = webtoon.episode.add(1)

        # 미디어 파일 생성
        media_file = base_dir / "images" / "001.jpg"
        media_file.parent.mkdir(parents=True, exist_ok=True)
        media_file.write_bytes(b"fake image data")

        # 미디어 경로로 추가 - 파일 경로를 path 파라미터로 전달해야 함
        # add_path_or_data 메서드 사용
        webtoon.content.add_path_or_data(episode, 1, "image", data=b"fake image data", path=media_file)

    # 데이터베이스를 닫았다가 다시 열어서 확인
    with Webtoon(db_path) as webtoon:
        webtoon.path.base_path = base_dir

        # episode 다시 로드
        from wbtn._managers._episode import WebtoonEpisode
        episode = WebtoonEpisode.from_episode_no(1, webtoon)
        media_list = list(webtoon.content.iterate(episode=episode))

        assert len(media_list) == 1
        media = media_list[0].load()

        # 경로가 올바르게 저장되고 로드되었는지 확인
        assert media.path == media_file
        # DB에는 상대 경로로 저장되어야 함
        with webtoon.connection.cursor() as cur:
            stored_path = cur.execute("SELECT path FROM Content WHERE content_id=?", (media.content_id,)).fetchone()[0]
            assert stored_path == "images/001.jpg"


def test_media_path_storage_with_changed_base_path(tmp_path: Path):
    """base_path 변경 시 기존 미디어 경로가 제대로 처리되는지 확인"""
    db_path = tmp_path / "test.wbtn"
    old_base = tmp_path / "old_media"
    new_base = tmp_path / "new_media"
    old_base.mkdir()
    new_base.mkdir()

    # 처음 base_path로 미디어 추가
    with Webtoon(db_path) as webtoon:
        webtoon.path.base_path = old_base

        episode = webtoon.episode.add(1)
        media_file = old_base / "image.jpg"
        media_file.write_bytes(b"data")

        webtoon.content.add_path_or_data(episode, 1, "image", data=b"data", path=media_file)

    # 새로운 base_path로 미디어 추가
    with Webtoon(db_path) as webtoon:
        webtoon.path.base_path = new_base

        # episode 로드
        from wbtn._managers._episode import WebtoonEpisode
        episode = WebtoonEpisode.from_episode_no(1, webtoon)
        new_media_file = new_base / "new_image.jpg"
        new_media_file.write_bytes(b"new data")

        webtoon.content.add_path_or_data(episode, 2, "image", data=b"new data", path=new_media_file)

    # 각 base_path로 열어서 확인
    with Webtoon(db_path) as webtoon:
        webtoon.path.base_path = old_base

        # episode 로드
        from wbtn._managers._episode import WebtoonEpisode
        episode = WebtoonEpisode.from_episode_no(1, webtoon)

        # old_base 기준으로 첫 번째 미디어 로드
        media_list = list(webtoon.content.iterate(episode=episode))
        first_media = [m for m in media_list if m.load().content_no == 1][0].load()
        assert first_media.path == old_base / "image.jpg"


def test_extra_file_path_storage_with_custom_base_path(tmp_path: Path):
    """custom base_path 설정 시 extra_file의 path가 올바르게 저장되고 로드됨"""
    db_path = tmp_path / "test.wbtn"
    base_dir = tmp_path / "files_base"
    base_dir.mkdir()

    with Webtoon(db_path) as webtoon:
        # custom base_path 설정
        webtoon.path.base_path = base_dir

        # extra file 생성
        extra_file = base_dir / "extra" / "metadata.json"
        extra_file.parent.mkdir(parents=True, exist_ok=True)
        extra_file.write_bytes(b'{"key": "value"}')

        # extra file 추가 (경로만)
        webtoon.extra_file.add_path(extra_file, conversion="str", purpose="metadata")

    # 다시 열어서 확인
    with Webtoon(db_path) as webtoon:
        webtoon.path.base_path = base_dir

        files = list(webtoon.extra_file.iterate(kind="metadata"))
        assert len(files) == 1

        file_data = files[0]
        assert file_data.path == extra_file

        # DB에는 상대 경로로 저장되어야 함
        with webtoon.connection.cursor() as cur:
            stored_path = cur.execute("SELECT path FROM ExtraFile WHERE file_id=?", (file_data.file_id,)).fetchone()[0]
            assert stored_path == "extra/metadata.json"


def test_media_data_storage_without_path(tmp_path: Path):
    """미디어를 data로 저장할 때는 base_path와 무관함"""
    db_path = tmp_path / "test.wbtn"
    base_dir = tmp_path / "base"
    base_dir.mkdir()

    with Webtoon(db_path) as webtoon:
        webtoon.path.base_path = base_dir

        episode = webtoon.episode.add(1)

        # data로 저장 (path 없음)
        webtoon.content.add(episode, 1, "image", data=b"image data")

    # 다시 열어서 확인
    with Webtoon(db_path) as webtoon:
        # episode 로드
        episode_no = 1
        from wbtn._managers._episode import WebtoonEpisode
        episode = WebtoonEpisode.from_episode_no(episode_no, webtoon)
        media_list = list(webtoon.content.iterate(episode=episode))

        assert len(media_list) == 1
        media = media_list[0].load()

        # path는 None이어야 함
        assert media.path is None
        # data가 저장되어 있어야 함
        assert media.data == b"image data"


def test_path_resolution_with_symlinks(tmp_path: Path):
    """심볼릭 링크가 있을 때 경로가 올바르게 resolve됨"""
    import os

    db_path = tmp_path / "test.wbtn"
    real_base = tmp_path / "real_base"
    real_base.mkdir()

    # 심볼릭 링크 생성 (운영 체제에 따라 작동 여부 다름)
    symlink_base = tmp_path / "symlink_base"
    try:
        symlink_base.symlink_to(real_base)
        has_symlink = True
    except (OSError, NotImplementedError):
        # Windows에서 권한이 없거나 지원하지 않는 경우
        has_symlink = False

    if has_symlink:
        with Webtoon(db_path) as webtoon:
            # 심볼릭 링크를 base_path로 설정
            webtoon.path.base_path = symlink_base

            episode = webtoon.episode.add(1)

            # 실제 경로에 파일 생성
            media_file = real_base / "image.jpg"
            media_file.write_bytes(b"data")

            # 미디어 추가
            webtoon.content.add_path_or_data(episode, 1, "image", data=b"data", path=media_file)

        # 다시 열어서 경로 확인
        with Webtoon(db_path) as webtoon:
            webtoon.path.base_path = symlink_base

            # episode 로드
            episode_no = 1
            from wbtn._managers._episode import WebtoonEpisode
            episode = WebtoonEpisode.from_episode_no(episode_no, webtoon)
            media_list = list(webtoon.content.iterate(episode=episode))

            media = media_list[0].load()
            # resolve된 경로여야 함
            assert media.path is not None
            assert media.path.resolve() == media_file.resolve()
