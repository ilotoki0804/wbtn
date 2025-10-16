import sys
from pathlib import Path
import datetime

import pytest

# Ensure src is importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbtn import Webtoon


def test_extra_file_add_get_set_remove(tmp_path):
    path = tmp_path / "extra.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        # initially empty
        assert len(w.extra_file) == 0

        # add an extra file
        w.extra_file.add(Path("notes.txt"), purpose="notes", data=b"hello")
        assert len(w.extra_file) == 1

        # iterate to get the ExtraFile
        files = list(w.extra_file.iterate())
        assert len(files) == 1
        ef = files[0]
        assert ef.purpose == "notes"
        assert ef.path == Path("notes.txt")
        assert ef.data == b"hello"

        # get by id and by object
        ef_by_id = w.extra_file.get(ef.id)
        assert ef_by_id.id == ef.id
        ef_by_obj = w.extra_file.get(ef)
        assert ef_by_obj.id == ef.id

        # update fields and set
        new_time = datetime.datetime.now()
        ef.purpose = "updated"
        ef.path = Path("updated.txt")
        ef.data = b"world"
        ef.added_at = new_time
        w.extra_file.set(ef)

        ef2 = w.extra_file.get(ef.id)
        assert ef2.purpose == "updated"
        assert ef2.path == Path("updated.txt")
        assert ef2.data == b"world"

        # remove
        w.extra_file.remove(ef.id)
        assert len(w.extra_file) == 0

        with pytest.raises(KeyError):
            w.extra_file.get(ef.id)


def test_extra_file_iterate_with_purpose(tmp_path):
    path = tmp_path / "extra_filter.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        w.extra_file.add(Path("a.txt"), purpose="p1", data=None)
        w.extra_file.add(Path("b.txt"), purpose="p2", data=None)
        w.extra_file.add(Path("c.txt"), purpose="p1", data=None)

        all_files = list(w.extra_file.iterate())
        assert len(all_files) == 3

        p1_files = list(w.extra_file.iterate("p1"))
        assert len(p1_files) == 2
        assert all(f.purpose == "p1" for f in p1_files)


def test_extra_file_set_missing_raises(tmp_path):
    path = tmp_path / "extra_missing.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        # build a fake ExtraFile-like object
        from wbtn._webtoon import ExtraFile

        fake = ExtraFile(9999, "x", Path("x"), None, datetime.datetime.now())
        with pytest.raises(KeyError):
            w.extra_file.set(fake)

        with pytest.raises(KeyError):
            w.extra_file.remove(9999)
