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

    webtoon_instance.info["sys_base_directory"] = str(suggested)

    result = webtoon_instance.path.suggested_base_path()
    assert result == suggested


def test_suggested_base_path_none_when_not_set(webtoon_instance: Webtoon):
    """설정되지 않으면 None 반환"""
    # sys_base_directory 삭제
    if "sys_base_directory" in webtoon_instance.info:
        webtoon_instance.info["sys_base_directory"] = None

    result = webtoon_instance.path.suggested_base_path()
    assert result is None


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
