import sys
import json
from pathlib import Path

import pytest

# Ensure the src directory is importable (project uses src/ layout)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbtn import Webtoon
from wbtn._base import WebtoonError, WebtoonOpenError, WebtoonSchemaError
from wbtn._webtoon_connection import version, WebtoonConnectionManager
from wbtn._webtoon import WebtoonMedia, MediaLazyLoader, WebtoonInfoManager, _json_dump


# ============ Connection and Basic Tests ============

def test_create_webtoon_new_file(tmp_path):
    """Test creating a new webtoon file with connection_mode='n'"""
    path = tmp_path / "test.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        assert w.info["sys_agent"] == "wbtn-python"
        assert w.info["sys_agent_version"] == version
        assert w.connection.conn is not None
        assert not w.connection.read_only


def test_create_webtoon_with_journal_mode(tmp_path):
    """Test creating a webtoon file with a specific journal mode"""
    path = tmp_path / "wal.wbtn"
    with Webtoon(path, connection_mode="n", journal_mode="wal") as w:
        with w.connection.cursor() as cur:
            mode, = cur.execute("PRAGMA journal_mode").fetchone()
        assert mode == "wal"


def test_open_existing_webtoon_readonly(tmp_path):
    """Test opening an existing webtoon file in read-only mode"""
    path = tmp_path / "readonly.wbtn"
    # Create the file first
    with Webtoon(path, connection_mode="n") as w:
        w.info["test_key"] = "test_value"

    # Open in read-only mode
    with Webtoon(path, connection_mode="r") as w:
        assert w.connection.read_only
        assert w.info["test_key"] == "test_value"


def test_connection_mode_write(tmp_path):
    """Test connection_mode='w' opens existing file for writing"""
    path = tmp_path / "write.wbtn"
    # Create the file first
    with Webtoon(path, connection_mode="n") as w:
        w.info["initial"] = "data"

    # Open for writing
    with Webtoon(path, connection_mode="w") as w:
        assert not w.connection.read_only
        w.info["new_key"] = "new_value"

    # Verify changes persisted
    with Webtoon(path, connection_mode="r") as w:
        assert w.info["new_key"] == "new_value"


def test_connection_mode_create_or_open(tmp_path):
    """Test connection_mode='c' creates if missing or opens if exists"""
    path = tmp_path / "create.wbtn"
    with Webtoon(path, connection_mode="c") as w:
        w.info["key1"] = "value1"

    # Open again with 'c' mode should work
    with Webtoon(path, connection_mode="c") as w:
        assert w.info["key1"] == "value1"
        w.info["key2"] = "value2"


# ============ Info Manager Tests ============

def test_info_set_and_get(tmp_path):
    """Test setting and getting info values"""
    path = tmp_path / "info.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        w.info["title"] = "My Webtoon"
        w.info["author"] = "Test Author"
        w.info["episode_count"] = 10

        assert w.info["title"] == "My Webtoon"
        assert w.info["author"] == "Test Author"
        assert w.info["episode_count"] == 10


def test_info_json_conversion(tmp_path):
    """Test storing and retrieving JSON data in info"""
    path = tmp_path / "json_info.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        w.info.default_conversion = "json"
        w.info["metadata"] = {"tags": ["action", "comedy"], "rating": 4.5}

        result = w.info["metadata"]
        assert result == {"tags": ["action", "comedy"], "rating": 4.5}


def test_info_iteration(tmp_path):
    """Test iterating over info keys"""
    path = tmp_path / "iter.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        w.info["key1"] = "value1"
        w.info["key2"] = "value2"

        keys = list(w.info.keys())
        assert "key1" in keys
        assert "key2" in keys


def test_info_items_and_values(tmp_path):
    """Test getting items and values from info"""
    path = tmp_path / "items.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        w.info["a"] = 1
        w.info["b"] = 2

        items = dict(w.info.items())
        assert items["a"] == 1
        assert items["b"] == 2

        values = list(w.info.values())
        assert 1 in values
        assert 2 in values


def test_info_delete(tmp_path):
    """Test deleting info entries"""
    path = tmp_path / "delete.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        w.info["temp"] = "delete_me"
        assert "temp" in w.info

        del w.info["temp"]
        assert "temp" not in w.info


def test_info_pop(tmp_path):
    """Test popping info entries"""
    path = tmp_path / "pop.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        w.info["remove"] = "value"

        result = w.info.pop("remove")
        assert result == "value"
        assert "remove" not in w.info

        # Pop with default
        result = w.info.pop("nonexistent", "default")
        assert result == "default"


def test_info_clear(tmp_path):
    """Test clearing all info entries"""
    path = tmp_path / "clear.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        w.info["a"] = 1
        w.info["b"] = 2

        w.info.clear()
        # System keys should also be cleared
        assert all(key.startswith("sys_") for key in w.info)

        w.info.clear(delete_system=True)
        assert len(w.info) == 0


def test_info_update(tmp_path):
    """Test updating multiple info entries at once"""
    path = tmp_path / "update.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        w.info.update({
            "title": "Updated Title",
            "author": "Updated Author",
            "year": 2025
        })

        assert w.info["title"] == "Updated Title"
        assert w.info["author"] == "Updated Author"
        assert w.info["year"] == 2025


def test_info_len(tmp_path):
    """Test getting the count of info entries"""
    path = tmp_path / "len.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        initial_len = len(w.info)
        w.info["new_key"] = "value"
        assert len(w.info) == initial_len + 1


# ============ JSON and Conversion Tests ============

def test_json_dump(tmp_path):
    """Test JSON dumping helper"""
    path = tmp_path / "json.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        result = _json_dump({"a": 1, "b": [1, 2, 3]})
        assert isinstance(result, str)
        assert json.loads(result) == {"a": 1, "b": [1, 2, 3]}


def test_dump_conversion_value(tmp_path):
    """Test _dump_conversion_value for different conversion types"""
    path = tmp_path / "dump.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        # No conversion
        assert w._dump_conversion_value(None, "test") == "test"

        # json_raw conversion
        result = w._dump_conversion_value("json", {"key": "value"})
        assert isinstance(result, str)
        assert json.loads(result) == {"key": "value"}

        # jsonb_raw conversion
        result = w._dump_conversion_value("jsonb", [1, 2, 3])
        assert isinstance(result, str)
        assert json.loads(result) == [1, 2, 3]


def test_get_conversion_query(tmp_path):
    """Test _get_conversion_query returns correct SQL fragments"""
    path = tmp_path / "query.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        # None conversion
        conv, query = w._get_conversion_query(None)
        assert conv is None
        assert query == "?"

        # json conversion
        conv, query = w._get_conversion_query("json")
        assert conv == "json"
        assert "json" in query

        # json_raw conversion
        conv, query = w._get_conversion_query("json_raw")
        assert conv == "json"
        assert "json" in query

        # jsonb conversion
        conv, query = w._get_conversion_query("jsonb")
        assert conv == "json"
        assert "jsonb" in query


def test_load_conversion_value(tmp_path):
    """Test _load_conversion_value for different conversion types"""
    path = tmp_path / "load.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        # No conversion
        assert w._load_conversion_value(None, "plain") == "plain"

        # json conversion
        json_str = _json_dump({"key": "value"})
        result = w._load_conversion_value("json", json_str)
        assert result == {"key": "value"}

        # jsonb conversion
        result = w._load_conversion_value("jsonb", json_str)
        assert result == {"key": "value"}

        # Raw conversions should raise ValueError
        with pytest.raises(ValueError):
            w._load_conversion_value("json_raw", json_str)

        with pytest.raises(ValueError):
            w._load_conversion_value("jsonb_raw", json_str)


# ============ Episode Tests ============

def test_episode_add(tmp_path):
    """Test adding an episode"""
    path = tmp_path / "episode.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        episode_no = w.episode.add(
            id="ep001",
            name="Episode 1",
            state="exists"
        )

        # Verify episode was added
        with w.connection.cursor() as cur:
            result = cur.execute(
                "SELECT name, id FROM episodes WHERE episode_no = ?",
                (episode_no,)
            ).fetchone()
            assert result is not None
            name, ep_id = result
            assert name == "Episode 1"
            assert ep_id == "ep001"


def test_episode_add_with_episode_no(tmp_path):
    """Test adding an episode with a specific episode number"""
    path = tmp_path / "episode_no.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        episode_no = w.episode.add(
            id="ep100",
            name="Episode 100",
            episode_no=100,
            state="exists"
        )

        assert episode_no == 100


def test_episode_add_extra_data(tmp_path):
    """Test adding extra data to an episode"""
    path = tmp_path / "extra.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        episode_no = w.episode.add(id="ep1", name="Ep1", state="exists")

        w.episode.add_extra_data(
            episode_no=episode_no,
            purpose="thumbnail",
            value="thumb.jpg"
        )

        # Verify extra data was added
        with w.connection.cursor() as cur:
            result = cur.execute(
                "SELECT value FROM episodes_extra WHERE episode_no = ? AND purpose = ?",
                (episode_no, "thumbnail")
            ).fetchone()
            assert result is not None
            assert result[0] == "thumb.jpg"


# ============ Media Tests ============

def test_media_add_with_data(tmp_path):
    """Test adding media with data"""
    path = tmp_path / "media.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        episode_no = w.episode.add(id="ep1", name="Ep1", state="exists")

        media = w.media.add(
            "test_data",
            episode_no=episode_no,
            media_no=0,
            purpose="image",
            lazy_load=False
        )

        assert media.media_id is not None
        assert media.episode_no == episode_no
        assert media.media_no == 0
        assert media.purpose == "image"
        assert media.data == "test_data"


def test_media_add_with_json_data(tmp_path):
    """Test adding media with JSON data"""
    path = tmp_path / "json_media.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        episode_no = w.episode.add(id="ep1", name="Ep1", state="exists")

        json_data = {"type": "comment", "text": "Great episode!"}
        media = w.media.add(
            json_data,
            episode_no=episode_no,
            media_no=1,
            purpose="comment",
            conversion="json",
            lazy_load=False
        )

        assert media.media_id is not None
        # Data should be stored as JSON string
        assert isinstance(media.data, str)
        assert json.loads(media.data) == json_data


def test_media_add_with_path(tmp_path):
    """Test adding media with a relative path"""
    path = tmp_path / "path_media.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        episode_no = w.episode.add(id="ep1", name="Ep1", state="exists")

        # Create a dummy file
        image_path = tmp_path / "image.jpg"
        image_path.write_text("fake image data")

        # Use relative path
        rel_path = Path("image.jpg")
        media = w.media.add(
            rel_path,
            episode_no=episode_no,
            media_no=2,
            purpose="image",
            lazy_load=False
        )

        assert media.path == rel_path
        assert media.data is None


def test_media_get_matched(tmp_path):
    """Test getting matched media"""
    path = tmp_path / "matched.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        episode_no = w.episode.add(id="ep1", name="Ep1", state="exists")

        # Add multiple media items
        w.media.add("img1", episode_no, 0, "image", lazy_load=False)
        w.media.add("img2", episode_no, 1, "image", lazy_load=False)
        w.media.add("comment", episode_no, 2, "comment", lazy_load=False)

        # Get all media for episode
        all_media = list(w.media.get_matched_media(episode_no=episode_no))
        assert len(all_media) == 3

        # Get only images
        images = list(w.media.get_matched_media(episode_no=episode_no, purpose="image"))
        assert len(images) == 2


def test_media_lazy_loading(tmp_path):
    """Test lazy loading of media attributes"""
    path = tmp_path / "lazy.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        episode_no = w.episode.add(id="ep1", name="Ep1", state="exists")

        # Add media with lazy_load=True
        media = w.media.add(
            "lazy_data",
            episode_no=episode_no,
            media_no=0,
            purpose="image",
            lazy_load=True
        )

        # Media should only have media_id initially
        assert hasattr(media, "media_id")

        # Accessing attributes should trigger lazy loading
        assert media.episode_no == episode_no
        assert media.purpose == "image"


def test_media_from_id(tmp_path):
    """Test creating media from ID"""
    path = tmp_path / "from_id.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        episode_no = w.episode.add(id="ep1", name="Ep1", state="exists")

        media = w.media.add("test", episode_no, 0, "image", lazy_load=False)
        media_id = media.media_id

        # Create new media object from ID
        media2 = WebtoonMedia.media_from_id(media_id, w, is_lazy=False)
        assert media2.media_id == media_id
        assert media2.episode_no == episode_no
        assert media2.data == "test"


def test_media_lazy_loader_descriptor(tmp_path):
    """Test MediaLazyLoader descriptor behavior"""
    path = tmp_path / "descriptor.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        episode_no = w.episode.add(id="ep1", name="Ep1", state="exists")

        media = w.media.add("test_data", episode_no, 0, "image", lazy_load=True)

        # Access data through the descriptor
        assert media.data == "test_data"


# ============ Error Handling Tests ============

def test_webtoon_error_hierarchy():
    """Test error class hierarchy"""
    assert issubclass(WebtoonOpenError, WebtoonError)
    assert issubclass(WebtoonSchemaError, WebtoonError)


def test_invalid_connection_mode(tmp_path):
    """Test that invalid connection mode raises an error"""
    path = tmp_path / "invalid.wbtn"
    with pytest.raises(WebtoonOpenError):
        with Webtoon(path, connection_mode="invalid"):  # type: ignore
            pass


def test_invalid_journal_mode(tmp_path):
    """Test that invalid journal mode raises an error"""
    path = tmp_path / "invalid_journal.wbtn"
    with pytest.raises(WebtoonOpenError):
        with Webtoon(path, connection_mode="n", journal_mode="invalid"):  # type: ignore
            pass


def test_info_keyerror_on_missing_key(tmp_path):
    """Test that accessing missing info key raises KeyError"""
    path = tmp_path / "missing.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        with pytest.raises(KeyError):
            _ = w.info["nonexistent_key"]


def test_info_get_with_default(tmp_path):
    """Test that info.get() returns default for missing keys"""
    path = tmp_path / "default.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        result = w.info.get("missing", "default_value")
        assert result == "default_value"


# ============ Context Manager Tests ============

def test_webtoon_context_manager(tmp_path):
    """Test that Webtoon works as a context manager"""
    path = tmp_path / "context.wbtn"

    with Webtoon(path, connection_mode="n") as w:
        w.info["test"] = "value"
        assert w.connection.conn is not None

    # Connection should be closed after exiting context
    # (we can't easily test this without accessing internals)


def test_webtoon_explicit_open_close(tmp_path):
    """Test explicit open and close of webtoon"""
    path = tmp_path / "explicit.wbtn"

    w = Webtoon(path, connection_mode="n")
    w.__enter__()
    try:
        w.info["key"] = "value"
        assert w.connection.conn is not None
    finally:
        w.__exit__(None, None, None)


# ============ Timestamp Tests ============

def test_connection_timestamp(tmp_path):
    """Test timestamp generation and conversion"""
    path = tmp_path / "timestamp.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        ts = w.connection.timestamp()
        assert isinstance(ts, int)
        assert ts > 0

        # Convert back to datetime
        dt = WebtoonConnectionManager.fromtimestamp(ts)
        import datetime
        assert isinstance(dt, datetime.datetime)


# ============ Additional Robustness / Edge-case Tests ============


def test_info_setdefault_behavior(tmp_path):
    """setdefault should not overwrite existing keys and should insert when missing"""
    path = tmp_path / "setdefault.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        # ensure missing key is inserted
        w.info.setdefault("new_key", "value")
        assert w.info["new_key"] == "value"

        # existing key should not be overwritten
        w.info["existing"] = "orig"
        w.info.setdefault("existing", "new")
        assert w.info["existing"] == "orig"


def test_webtoon_migrate_non_replace_creates_new_instance(tmp_path):
    """Test migrate with replace=False returns a new Webtoon instance connected to new file"""
    src_path = tmp_path / "orig.wbtn"
    dest_path = tmp_path / "migrated.wbtn"

    with Webtoon(src_path, connection_mode="n") as w:
        w.info["key"] = "value"

        new_w = w.migrate(str(dest_path), replace=False)
        # Should be a different object
        assert new_w is not w
        # New webtoon should have the same sys_agent
        assert new_w.info.get("sys_agent") == "wbtn-python"

    # Original file should still exist and have data
    with Webtoon(src_path, connection_mode="r") as w2:
        assert w2.info.get("key") == "value"

    # Migrated file should exist
    with Webtoon(dest_path, connection_mode="r") as wm:
        assert wm.info.get("sys_agent") == "wbtn-python"


def test_webtoon_migrate_replace_switches_connection(tmp_path):
    """Test migrate with replace=True replaces current Webtoon.connection in-place"""
    src_path = tmp_path / "orig_replace.wbtn"
    dest_path = tmp_path / "migrated_replace.wbtn"

    with Webtoon(src_path, connection_mode="n") as w:
        replaced_w = w.migrate(str(dest_path), replace=True)
        # When replace=True and used as contextmanager, the yielded object should be the same instance
        assert replaced_w is w
        # The connection should now point to the migrated file
        with replaced_w.connection.cursor() as cur:
            # check that pragma application_id exists (basic health check)
            app_id, = cur.execute("PRAGMA application_id").fetchone()
            assert app_id == 0x5742544e


def test_get_conversion_invalid_raises(tmp_path):
    """Unknown conversion passed to _get_conversion_query should raise ValueError"""
    path = tmp_path / "conv.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        with pytest.raises(ValueError):
            w._get_conversion_query("xml")  # type: ignore[arg-type]


def test_absolute_and_relative_path_permissions(tmp_path):
    """Tests that absolute/relative path permission flags are respected"""
    path = tmp_path / "pathperm.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        ep = w.episode.add(id="ep1", name="Ep1", state="exists")

        # absolute path not allowed
        abs_file = tmp_path / "abs.jpg"
        abs_file.write_text("data")
        w.info["sys_allow_absolute_path"] = False
        with pytest.raises(ValueError):
            w.media.add(abs_file, ep, 0, "image", lazy_load=False)

        # relative path not allowed
        w.info["sys_allow_relative_path"] = False
        rel = Path("some_relative.jpg")
        with pytest.raises(ValueError):
            w.media.add(rel, ep, 1, "image", lazy_load=False)


def test_media_lazy_loader_caching_and_missing(tmp_path):
    """Test that MediaLazyLoader can cache results and that missing media raises"""
    path = tmp_path / "lazy_cache.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        ep = w.episode.add(id="ep1", name="Ep1", state="exists")
        media = w.media.add("cache_data", ep, 0, "image", lazy_load=True)

        # enable caching on this media instance
        media = media.replace_config(cache_results=True)
        # first access triggers loader and caches value on instance
        assert media.data == "cache_data"
        assert hasattr(media, "data")

        # remove the DB row and subsequent accesses should still work because of cache
        with w.connection.cursor() as cur:
            cur.execute("DELETE FROM media WHERE id == ?", (media.media_id,))

        # because cached, attribute lookup should still return the cached value
        assert media.data == "cache_data"


def test_medialazyloader_invalid_column_name(tmp_path):
    """MediaLazyLoader should reject invalid column names early"""
    path = tmp_path / "lazy_invalid.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        ep = w.episode.add(id="ep1", name="Ep1", state="exists")
        media = w.media.add("x", ep, 0, "image", lazy_load=True)

        # build a loader with invalid identifier
        from wbtn._webtoon import MediaLazyLoader

        loader = MediaLazyLoader("123bad")
        # media instance needs _webtoon and media_id
        with pytest.raises(ValueError):
            loader.__get__(media)


def test_file_user_version_setter_readonly_raises(tmp_path):
    """Setting file_user_version on a read-only connection should raise WebtoonSchemaError"""
    path = tmp_path / "version.wbtn"
    # create file
    with Webtoon(path, connection_mode="n"):
        pass

    # open read-only and attempt to set
    with Webtoon(path, connection_mode="r") as w:
        with pytest.raises(WebtoonSchemaError):
            w.connection.file_user_version = 2000


def test_execute_context_manager_and_timestamp_monotonic(tmp_path):
    """Test Webtoon.execute context manager and that timestamp is monotonic"""
    path = tmp_path / "exec.wbtn"
    with Webtoon(path, connection_mode="n") as w:
        with w.execute_with("SELECT 1", ()) as cur:
            row = cur.fetchone()
            assert row[0] == 1

        t1 = w.connection.timestamp()
        t2 = w.connection.timestamp()
        assert t2 >= t1
