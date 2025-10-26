import sys
from pathlib import Path
import datetime

import pytest

# Ensure src is importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbtn import Webtoon
from wbtn._managers._extra_file import ExtraFile
from wbtn._json_data import JsonData


def test_extra_file_basic_operations(tmp_path: Path):
    """extra_file의 기본 CRUD 작동"""
    tmp_path = tmp_path.resolve()
    path = tmp_path / "extra.wbtn"
    with Webtoon(path) as webtoon:
        # initially empty
        assert len(webtoon.extra_file) == 0

        # add an extra file with data
        ef = webtoon.extra_file.add_data(tmp_path / "notes.txt", data=b"hello", purpose="notes")
        assert len(webtoon.extra_file) == 1
        assert isinstance(ef, ExtraFile)
        assert ef.purpose == "notes"
        assert ef.path == tmp_path / "notes.txt"
        assert ef.data == b"hello"
        assert ef.conversion == "bytes"  # primitive_conversion=True로 자동 감지됨
        assert isinstance(ef.added_at, datetime.datetime)

        # iterate to get the ExtraFile
        files = list(webtoon.extra_file.iterate())
        assert len(files) == 1
        assert files[0].id == ef.id

        # get by id using from_id
        ef_by_id = ExtraFile.from_id(ef.id, webtoon)
        assert ef_by_id.id == ef.id
        assert ef_by_id.data == b"hello"

        # update fields and set
        new_time = datetime.datetime.now()
        ef.purpose = "updated"
        ef.path = tmp_path / "updated.txt"
        ef.data = b"world"
        ef.added_at = new_time
        webtoon.extra_file.set(ef)

        ef2 = ExtraFile.from_id(ef.id, webtoon)
        assert ef2.purpose == "updated"
        assert ef2.path == tmp_path / "updated.txt"
        assert ef2.data == b"world"

        # remove
        webtoon.extra_file.remove(ef)
        assert len(webtoon.extra_file) == 0

        with pytest.raises(KeyError):
            ExtraFile.from_id(ef.id, webtoon)


def test_extra_file_add_path_only(tmp_path: Path):
    """경로만으로 extra_file 추가 (data 없음)"""
    tmp_path = tmp_path.resolve()
    db_path = tmp_path / "extra_path.wbtn"

    # 실제 파일 생성
    extra_file_path = tmp_path / "metadata.json"
    extra_file_path.write_text('{"key": "value"}')

    with Webtoon(db_path) as webtoon:
        # conversion 명시하여 경로만 저장
        ef = webtoon.extra_file.add_path(extra_file_path, conversion="str", purpose="metadata")

        assert isinstance(ef, ExtraFile)
        assert ef.path == extra_file_path
        assert ef.data is None  # add_path는 data=None을 저장
        assert ef.conversion == "str"
        assert ef.purpose == "metadata"


def test_extra_file_add_data_with_different_types(tmp_path: Path):
    """다양한 타입의 데이터로 extra_file 추가"""
    db_path = tmp_path / "data_types.wbtn"

    with Webtoon(db_path) as webtoon:
        # bytes - primitive_conversion=True로 자동 감지됨
        ef1 = webtoon.extra_file.add_data(tmp_path / "file1.bin", data=b"\x00\x01\x02", purpose="binary")
        assert ef1.conversion == "bytes"
        assert ef1.data == b"\x00\x01\x02"

        # str - primitive_conversion=True로 자동 감지됨
        ef2 = webtoon.extra_file.add_data(tmp_path / "file2.txt", data="Hello, World!", purpose="text")
        assert ef2.conversion == "str"
        assert ef2.data == "Hello, World!"

        # int - primitive_conversion=True로 자동 감지됨
        ef3 = webtoon.extra_file.add_data(tmp_path / "file3.dat", data=42, purpose="number")
        assert ef3.conversion == "int"
        assert ef3.data == 42

        # json
        json_data = JsonData(data={"key": "value"})
        ef4 = webtoon.extra_file.add_data(tmp_path / "file4.json", data=json_data, purpose="json")
        assert ef4.conversion == "json"
        assert isinstance(ef4.data, JsonData)

        # 모든 파일 확인
        files = list(webtoon.extra_file.iterate())
        assert len(files) == 4


def test_extra_file_iterate_with_purpose(tmp_path: Path):
    """purpose로 필터링하여 iterate"""
    tmp_path = tmp_path.resolve()
    path = tmp_path / "extra_filter.wbtn"
    with Webtoon(path) as webtoon:
        webtoon.extra_file.add_path(tmp_path / "a.txt", conversion="str", purpose="p1")
        webtoon.extra_file.add_path(tmp_path / "b.txt", conversion="str", purpose="p2")
        webtoon.extra_file.add_path(tmp_path / "c.txt", conversion="str", purpose="p1")

        all_files = list(webtoon.extra_file.iterate())
        assert len(all_files) == 3

        p1_files = list(webtoon.extra_file.iterate("p1"))
        assert len(p1_files) == 2
        assert all(f.purpose == "p1" for f in p1_files)

        p2_files = list(webtoon.extra_file.iterate("p2"))
        assert len(p2_files) == 1
        assert p2_files[0].purpose == "p2"


def test_extra_file_iterate_without_filter(tmp_path: Path):
    """purpose 필터 없이 모든 파일 iterate"""
    db_path = tmp_path / "all_files.wbtn"

    with Webtoon(db_path) as webtoon:
        webtoon.extra_file.add_data(tmp_path / "1.txt", data=b"1", purpose="a")
        webtoon.extra_file.add_data(tmp_path / "2.txt", data=b"2", purpose="b")
        webtoon.extra_file.add_data(tmp_path / "3.txt", data=b"3", purpose=None)

        # iterate() 파라미터 없이 호출
        all_files = list(webtoon.extra_file.iterate())
        assert len(all_files) == 3

        purposes = {f.purpose for f in all_files}
        assert purposes == {"a", "b", None}


def test_extra_file_iterate_with_none_purpose(tmp_path: Path):
    """purpose=None으로 필터링"""
    db_path = tmp_path / "none_purpose.wbtn"

    with Webtoon(db_path) as webtoon:
        webtoon.extra_file.add_data(tmp_path / "1.txt", data=b"1", purpose="labeled")
        webtoon.extra_file.add_data(tmp_path / "2.txt", data=b"2", purpose=None)
        webtoon.extra_file.add_data(tmp_path / "3.txt", data=b"3", purpose=None)

        # purpose IS NULL 쿼리가 추가되어 제대로 작동함
        none_files = list(webtoon.extra_file.iterate(None))
        assert len(none_files) == 2
        for ef in none_files:
            assert ef.purpose is None


def test_extra_file_set_missing_raises(tmp_path):
    """존재하지 않는 extra_file을 set하면 KeyError 발생"""
    path = tmp_path / "extra_missing.wbtn"
    with Webtoon(path) as webtoon:
        # build a fake ExtraFile
        fake = ExtraFile(
            id=9999,
            purpose="x",
            conversion="str",
            path=tmp_path / "x",
            data=None,
            added_at=datetime.datetime.now()
        )
        with pytest.raises(KeyError):
            webtoon.extra_file.set(fake)


def test_extra_file_remove_missing_raises(tmp_path):
    """존재하지 않는 extra_file을 remove하면 KeyError 발생"""
    path = tmp_path / "extra_remove.wbtn"
    with Webtoon(path) as webtoon:
        fake = ExtraFile(
            id=9999,
            purpose="x",
            conversion="str",
            path=tmp_path / "x",
            data=None,
            added_at=datetime.datetime.now()
        )
        with pytest.raises(KeyError):
            webtoon.extra_file.remove(fake)


def test_extra_file_remove_by_object(tmp_path: Path):
    """ExtraFile 객체로 제거"""
    db_path = tmp_path / "remove_obj.wbtn"

    with Webtoon(db_path) as webtoon:
        ef = webtoon.extra_file.add_data(tmp_path / "file.txt", data=b"data", purpose="test")

        assert len(webtoon.extra_file) == 1

        # 객체로 제거
        webtoon.extra_file.remove(ef)
        assert len(webtoon.extra_file) == 0


def test_extra_file_update_all_fields(tmp_path: Path):
    """모든 필드를 업데이트"""
    db_path = tmp_path / "update_all.wbtn"

    with Webtoon(db_path) as webtoon:
        ef = webtoon.extra_file.add_data(tmp_path / "original.txt", data=b"old", purpose="original")
        original_id = ef.id

        # 모든 필드 변경 - set()은 raw data를 그대로 저장
        ef.purpose = "modified"
        ef.conversion = "str"
        ef.path = tmp_path / "modified.txt"
        ef.data = "new text"
        ef.added_at = datetime.datetime(2020, 1, 1, 12, 0, 0)

        webtoon.extra_file.set(ef)

        # 확인 - set()이 raw data를 저장하므로 conversion과 관계없이 저장됨
        updated = ExtraFile.from_id(original_id, webtoon)
        assert updated.purpose == "modified"
        assert updated.conversion == "str"
        assert updated.path == tmp_path / "modified.txt"
        assert updated.data == "new text"  # load_value로 로드됨
        assert updated.added_at == datetime.datetime(2020, 1, 1, 12, 0, 0)


def test_extra_file_iterator_protocol(tmp_path: Path):
    """__iter__를 통한 iteration"""
    db_path = tmp_path / "iterator.wbtn"

    with Webtoon(db_path) as webtoon:
        webtoon.extra_file.add_data(tmp_path / "1.txt", data=b"1")
        webtoon.extra_file.add_data(tmp_path / "2.txt", data=b"2")
        webtoon.extra_file.add_data(tmp_path / "3.txt", data=b"3")

        # for 루프로 직접 iterate
        count = 0
        for ef in webtoon.extra_file:
            assert isinstance(ef, ExtraFile)
            count += 1

        assert count == 3


def test_extra_file_added_at_timestamp(tmp_path: Path):
    """added_at 필드가 올바르게 저장되고 로드됨"""
    db_path = tmp_path / "timestamp.wbtn"

    with Webtoon(db_path) as webtoon:
        before = datetime.datetime.now()
        ef = webtoon.extra_file.add_data(tmp_path / "file.txt", data=b"data")
        after = datetime.datetime.now()

        # added_at이 추가 시점의 시간이어야 함
        assert before <= ef.added_at <= after
        assert isinstance(ef.added_at, datetime.datetime)


def test_extra_file_with_custom_base_path(tmp_path: Path):
    """custom base_path와 함께 사용"""
    db_path = tmp_path / "custom_base.wbtn"
    base_dir = tmp_path / "files"
    base_dir.mkdir()

    with Webtoon(db_path) as webtoon:
        webtoon.path.base_path = base_dir

        file_path = base_dir / "subdir" / "file.txt"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"content")

        ef = webtoon.extra_file.add_data(file_path, data=b"data", purpose="test")

    # 다시 열어서 확인
    with Webtoon(db_path) as webtoon:
        webtoon.path.base_path = base_dir

        files = list(webtoon.extra_file.iterate())
        assert len(files) == 1
        assert files[0].path == file_path

        # DB에는 상대 경로로 저장되어야 함
        with webtoon.connection.cursor() as cur:
            stored_path = cur.execute("SELECT path FROM extra_files WHERE id=?", (files[0].id,)).fetchone()[0]
            assert stored_path == "subdir/file.txt"


def test_extra_file_from_id_not_found(tmp_path: Path):
    """존재하지 않는 ID로 from_id 호출 시 KeyError 발생"""
    db_path = tmp_path / "not_found.wbtn"

    with Webtoon(db_path) as webtoon:
        with pytest.raises(KeyError):
            ExtraFile.from_id(9999, webtoon)


def test_extra_file_add_data_returns_populated_object(tmp_path: Path):
    """add_data가 완전히 채워진 ExtraFile 객체를 반환"""
    db_path = tmp_path / "return_obj.wbtn"

    with Webtoon(db_path) as webtoon:
        ef = webtoon.extra_file.add_data(tmp_path / "test.txt", data="test data", purpose="test")

        assert ef.id > 0
        assert ef.purpose == "test"
        assert ef.conversion == "str"  # primitive_conversion=True로 자동 감지됨
        assert ef.path == tmp_path / "test.txt"
        assert ef.data == "test data"
        assert isinstance(ef.added_at, datetime.datetime)


def test_extra_file_add_path_returns_populated_object(tmp_path: Path):
    """add_path가 완전히 채워진 ExtraFile 객체를 반환"""
    db_path = tmp_path / "return_obj2.wbtn"

    with Webtoon(db_path) as webtoon:
        ef = webtoon.extra_file.add_path(tmp_path / "test.txt", conversion="bytes", purpose="test")

        assert ef.id > 0
        assert ef.purpose == "test"
        assert ef.conversion == "bytes"
        assert ef.path == tmp_path / "test.txt"
        assert ef.data is None  # add_path는 data=None을 저장
        assert isinstance(ef.added_at, datetime.datetime)


def test_extra_file_multiple_operations(tmp_path: Path):
    """여러 작업을 연속으로 수행"""
    db_path = tmp_path / "multiple_ops.wbtn"

    with Webtoon(db_path) as webtoon:
        # 여러 파일 추가
        ef1 = webtoon.extra_file.add_data(tmp_path / "1.txt", data=b"one")
        ef2 = webtoon.extra_file.add_data(tmp_path / "2.txt", data=b"two")
        ef3 = webtoon.extra_file.add_path(tmp_path / "3.txt", conversion="str")

        assert len(webtoon.extra_file) == 3

        # 하나 수정
        ef2.data = b"modified"
        webtoon.extra_file.set(ef2)

        # 하나 삭제
        webtoon.extra_file.remove(ef1)

        assert len(webtoon.extra_file) == 2

        # 남은 파일 확인
        remaining = list(webtoon.extra_file.iterate())
        remaining_ids = {f.id for f in remaining}
        assert remaining_ids == {ef2.id, ef3.id}

        # 수정된 내용 확인
        ef2_reloaded = ExtraFile.from_id(ef2.id, webtoon)
        assert ef2_reloaded.data == b"modified"


def test_extra_file_with_json_data(tmp_path: Path):
    """JsonData를 사용하는 extra_file"""
    db_path = tmp_path / "json_data.wbtn"

    with Webtoon(db_path) as webtoon:
        json_obj = {"name": "test", "value": 123, "nested": {"key": "value"}}
        json_data = JsonData(data=json_obj)

        ef = webtoon.extra_file.add_data(tmp_path / "config.json", data=json_data, purpose="config")

        assert ef.conversion == "json"  # JsonData는 항상 json conversion으로 감지됨
        assert isinstance(ef.data, JsonData)

        # 다시 로드
        ef_reloaded = ExtraFile.from_id(ef.id, webtoon)
        assert isinstance(ef_reloaded.data, JsonData)
        assert ef_reloaded.data.load() == json_obj


def test_extra_file_purpose_can_be_none(tmp_path: Path):
    """purpose가 None일 수 있음"""
    db_path = tmp_path / "no_purpose.wbtn"

    with Webtoon(db_path) as webtoon:
        ef = webtoon.extra_file.add_data(tmp_path / "file.txt", data=b"data", purpose=None)

        assert ef.purpose is None

        ef_reloaded = ExtraFile.from_id(ef.id, webtoon)
        assert ef_reloaded.purpose is None

