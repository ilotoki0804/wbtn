"""
WebtoonConnectionManager와 ConnectionSettings에 대한 포괄적인 테스트
데이터베이스 생성, 연결, pragma 설정, 에러 처리 등을 테스트합니다.
"""
import os
import sys
from pathlib import Path

import pytest
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbtn import Webtoon
from wbtn._managers import ConnectionSettings, WebtoonConnectionManager
from wbtn._base import (
    SCHEMA_VERSION,
    WebtoonConnectionError,
    WebtoonOpenError,
    WebtoonSchemaError,
)


# ===== ConnectionSettings 테스트 =====


def test_connection_settings_default_values():
    """ConnectionSettings의 기본값 테스트"""
    settings = ConnectionSettings()
    assert settings.read_only is False
    assert settings.create_db is True
    assert settings.clear_existing_db is False
    assert settings.journal_mode is None
    assert settings.bypass_integrity_check is False


def test_connection_settings_custom_values():
    """ConnectionSettings에 사용자 정의 값 설정"""
    settings = ConnectionSettings(
        read_only=True,
        create_db=False,
        journal_mode="wal",
        bypass_integrity_check=True
    )
    assert settings.read_only is True
    assert settings.create_db is False
    assert settings.journal_mode == "wal"
    assert settings.bypass_integrity_check is True


# ===== 기본 연결 테스트 =====


def test_create_new_database_file(tmp_path: Path):
    """새 데이터베이스 파일 생성"""
    db_path = tmp_path / "new.wbtn"
    assert not db_path.exists()

    with Webtoon(db_path) as webtoon:
        assert db_path.exists()
        assert webtoon.connection._conn is not None


def test_connect_to_existing_database(tmp_path: Path):
    """기존 데이터베이스에 연결"""
    db_path = tmp_path / "existing.wbtn"

    # 먼저 데이터베이스 생성
    with Webtoon(db_path):
        pass

    # 다시 연결
    with Webtoon(db_path) as webtoon:
        assert webtoon.connection._conn is not None


def test_memory_database():
    """메모리 내 데이터베이스 생성"""
    with Webtoon(":memory:") as webtoon:
        assert webtoon.connection.in_memory is True
        assert webtoon.connection._conn is not None


def test_context_manager_connects_and_closes(tmp_path: Path):
    """Context manager로 연결 및 종료"""
    db_path = tmp_path / "context.wbtn"
    webtoon = Webtoon(db_path)

    assert webtoon.connection._conn is None

    with webtoon:
        assert webtoon.connection._conn is not None

    assert webtoon.connection._conn is None


def test_manual_connect_and_close(tmp_path: Path):
    """수동 연결 및 종료"""
    db_path = tmp_path / "manual.wbtn"
    webtoon = Webtoon(db_path)

    webtoon.connect()
    assert webtoon.connection._conn is not None

    webtoon.close()
    assert webtoon.connection._conn is None


# ===== read_only 모드 테스트 =====


def test_readonly_connection(tmp_path: Path):
    """읽기 전용 연결"""
    db_path = tmp_path / "readonly.wbtn"

    # 먼저 데이터베이스 생성
    with Webtoon(db_path):
        pass

    # 읽기 전용으로 열기
    settings = ConnectionSettings(read_only=True)
    with Webtoon(db_path, connection_settings=settings) as webtoon:
        # 읽기는 가능
        count = len(webtoon.info)
        assert count >= 0

        # 쓰기 시도 시 에러
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            webtoon.info["test"] = "value"


def test_readonly_with_memory_raises_error():
    """메모리 데이터베이스는 읽기 전용 불가"""
    settings = ConnectionSettings(read_only=True)
    with pytest.raises(WebtoonOpenError, match="read_only.*memory"):
        Webtoon(":memory:", connection_settings=settings).connect()


def test_readonly_without_create_db(tmp_path: Path):
    """읽기 전용이면 create_db 설정 무시"""
    db_path = tmp_path / "readonly_no_create.wbtn"

    # 먼저 파일 생성
    with Webtoon(db_path):
        pass

    # read_only=True이면 파일이 없어도 에러 (rw 모드로 열림)
    settings = ConnectionSettings(read_only=True)
    with Webtoon(db_path, connection_settings=settings) as webtoon:
        assert webtoon.connection.settings.read_only is True


# ===== create_db 및 clear_existing_db 테스트 =====


def test_create_db_false_with_nonexistent_file_raises_error(tmp_path: Path):
    """create_db=False일 때 파일이 없으면 에러"""
    db_path = tmp_path / "nonexistent.wbtn"
    settings = ConnectionSettings(create_db=False)

    with pytest.raises(WebtoonOpenError):
        Webtoon(db_path, connection_settings=settings).connect()


def test_clear_existing_db_removes_old_data(tmp_path: Path):
    """clear_existing_db=True면 기존 데이터 삭제"""
    db_path = tmp_path / "clear.wbtn"

    # 먼저 데이터 생성
    with Webtoon(db_path) as webtoon:
        webtoon.info["test_key"] = "old_value"

    # clear_existing_db=True로 다시 열기
    settings = ConnectionSettings(clear_existing_db=True)
    with Webtoon(db_path, connection_settings=settings) as webtoon:
        # 기존 데이터가 없어야 함
        assert "test_key" not in webtoon.info


# ===== journal_mode 테스트 =====


def test_journal_mode_wal(tmp_path: Path):
    """WAL 저널 모드 설정"""
    db_path = tmp_path / "wal.wbtn"
    settings = ConnectionSettings(journal_mode="wal")

    with Webtoon(db_path, connection_settings=settings) as webtoon:
        result = webtoon.connection._connection().execute("PRAGMA journal_mode").fetchone()
        assert result[0].lower() == "wal"


def test_journal_mode_delete(tmp_path: Path):
    """DELETE 저널 모드 설정"""
    db_path = tmp_path / "delete.wbtn"
    settings = ConnectionSettings(journal_mode="delete")

    with Webtoon(db_path, connection_settings=settings) as webtoon:
        result = webtoon.connection._connection().execute("PRAGMA journal_mode").fetchone()
        assert result[0].lower() == "delete"


def test_journal_mode_memory_for_memory_db():
    """메모리 DB에서 memory 저널 모드"""
    settings = ConnectionSettings(journal_mode="memory")

    with Webtoon(":memory:", connection_settings=settings) as webtoon:
        result = webtoon.connection._connection().execute("PRAGMA journal_mode").fetchone()
        assert result[0].lower() in ("memory", "off")


def test_invalid_journal_mode_for_memory_raises_error():
    """메모리 DB에 부적절한 저널 모드 설정 시 에러"""
    settings = ConnectionSettings(journal_mode="wal")

    with pytest.raises(WebtoonOpenError, match="Invalid journal mode for in-memory"):
        Webtoon(":memory:", connection_settings=settings).connect()


# ===== application_id 및 user_version 테스트 =====


def test_application_id_set_correctly(tmp_path: Path):
    """application_id가 올바르게 설정됨"""
    db_path = tmp_path / "app_id.wbtn"

    with Webtoon(db_path) as webtoon:
        app_id = webtoon.connection._connection().execute("PRAGMA application_id").fetchone()[0]
        assert app_id == 0x5742544E  # 'WBTN'


def test_user_version_set_to_schema_version(tmp_path: Path):
    """user_version이 SCHEMA_VERSION으로 설정됨"""
    db_path = tmp_path / "user_ver.wbtn"

    with Webtoon(db_path) as webtoon:
        user_ver = webtoon.connection.file_user_version
        assert user_ver == SCHEMA_VERSION


def test_open_file_with_wrong_application_id_raises_error(tmp_path: Path):
    """잘못된 application_id를 가진 파일 열기 시 에러"""
    db_path = tmp_path / "wrong_app_id.wbtn"

    # 잘못된 application_id로 데이터베이스 생성
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA application_id=0x12345678")
    conn.close()

    with pytest.raises(WebtoonSchemaError, match="not a WBTN file"):
        Webtoon(db_path).connect()


def test_bypass_integrity_check_skips_validation(tmp_path: Path):
    """bypass_integrity_check=True면 검증 생략"""
    db_path = tmp_path / "bypass.wbtn"

    # 잘못된 application_id로 데이터베이스 생성
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA application_id=0x12345678")
    conn.execute("CREATE TABLE test (id INTEGER)")
    conn.close()

    settings = ConnectionSettings(bypass_integrity_check=True)
    # 에러 없이 열림
    with Webtoon(db_path, connection_settings=settings) as webtoon:
        assert webtoon.connection._conn is not None


# ===== 테이블 생성 테스트 =====


def test_all_tables_created(tmp_path: Path):
    """모든 필수 테이블이 생성됨"""
    db_path = tmp_path / "tables.wbtn"

    with Webtoon(db_path) as webtoon:
        conn = webtoon.connection._connection()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = {t[0] for t in tables}

        assert "Info" in table_names
        assert "Episode" in table_names
        assert "EpisodeInfo" in table_names
        assert "Content" in table_names
        assert "ContentInfo" in table_names
        assert "ExtraFile" in table_names


def test_system_info_initialized(tmp_path: Path):
    """시스템 정보가 초기화됨"""
    db_path = tmp_path / "sys_info.wbtn"

    with Webtoon(db_path) as webtoon:
        assert "sys_agent" in webtoon.info
        assert "sys_agent_version" in webtoon.info
        assert "sys_created_at" in webtoon.info
        assert webtoon.info["sys_agent"] == "wbtn-python"


# ===== 에러 처리 테스트 =====


def test_connection_without_connect_raises_error(tmp_path: Path):
    """연결하지 않고 connection 접근 시 에러"""
    db_path = tmp_path / "no_connect.wbtn"
    webtoon = Webtoon(db_path)

    with pytest.raises(WebtoonConnectionError, match="not initialized"):
        webtoon.connection._connection()


def test_double_connect_is_safe(tmp_path: Path):
    """이중 연결 시도는 무시됨"""
    db_path = tmp_path / "double.wbtn"

    with Webtoon(db_path) as webtoon:
        first_conn = webtoon.connection._conn
        webtoon.connection.connect()  # 다시 연결 시도
        second_conn = webtoon.connection._conn
        assert first_conn is second_conn


def test_foreign_keys_enabled(tmp_path: Path):
    """외래 키 제약이 활성화됨"""
    db_path = tmp_path / "fk.wbtn"

    with Webtoon(db_path) as webtoon:
        fk_status = webtoon.connection._connection().execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk_status == 1


# ===== 파일 경로 정규화 테스트 =====


def test_uri_normalization_removes_double_slashes(tmp_path: Path):
    """URI 정규화가 이중 슬래시 제거"""
    db_path = tmp_path / "uri_norm.wbtn"

    with Webtoon(db_path) as webtoon:
        uri = webtoon.connection._normalize_uri(db_path)
        # 이중 슬래시가 없어야 함 (file:// 제외)
        assert "///" not in uri or uri.startswith("file:///")


# ===== _connect 메모리 데이터베이스 테스트 (공개 API를 통해) =====


def test_memory_database_with_create_db_false_raises_error():
    """메모리 데이터베이스에서 create_db=False일 때 에러 발생"""
    settings = ConnectionSettings(create_db=False)

    with pytest.raises(WebtoonOpenError, match="Memory database need to be created"):
        Webtoon(":memory:", connection_settings=settings).connect()


def test_memory_database_with_clear_existing_db(tmp_path: Path):
    """메모리 데이터베이스에서 clear_existing_db는 무시됨 (생성만 됨)"""
    settings = ConnectionSettings(clear_existing_db=True)

    # 에러 없이 생성되어야 함
    with Webtoon(":memory:", connection_settings=settings) as webtoon:
        assert webtoon.connection.in_memory is True
        assert webtoon.connection.existed is False


# ===== _check_user_version 테스트 (공개 API를 통해) =====


def test_user_version_uninitialized_warning_readonly(tmp_path: Path):
    """user_version이 0이고 read_only일 때 경고 발생"""
    db_path = tmp_path / "uninit_version.wbtn"

    # user_version을 0으로 설정한 DB 생성
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA application_id=0x5742544e")  # WBTN
    conn.execute("PRAGMA user_version=0")
    conn.execute("CREATE TABLE IF NOT EXISTS info (name TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

    # 읽기 전용으로 열 때 경고
    settings = ConnectionSettings(read_only=True)
    with pytest.warns(UserWarning, match="not initialized"):
        with Webtoon(db_path, connection_settings=settings):
            pass


def test_user_version_uninitialized_auto_initialize(tmp_path: Path):
    """user_version이 0일 때 자동으로 현재 버전으로 초기화 (쓰기 모드)"""
    db_path = tmp_path / "uninit_auto.wbtn"

    # user_version을 0으로 설정한 DB 생성
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA application_id=0x5742544e")
    conn.execute("PRAGMA user_version=0")
    conn.execute("CREATE TABLE IF NOT EXISTS info (name TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

    # 경고와 함께 자동 초기화
    with pytest.warns(UserWarning, match="Initialize to the current version"):
        with Webtoon(db_path) as webtoon:
            # 현재 스키마 버전으로 업데이트되어야 함
            assert webtoon.connection.file_user_version == SCHEMA_VERSION


def test_user_version_future_format_raises_error(tmp_path: Path):
    """미래 버전의 파일 형식은 에러 발생"""
    db_path = tmp_path / "future_version.wbtn"

    # 미래 버전으로 설정 (현재 버전보다 1000 이상 큰 값)
    future_version = SCHEMA_VERSION + 1000
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA application_id=0x5742544e")
    conn.execute(f"PRAGMA user_version={future_version}")
    conn.execute("CREATE TABLE IF NOT EXISTS info (name TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

    # 미래 형식은 열 수 없음
    with pytest.raises(WebtoonSchemaError, match="Cannot open future file format"):
        with Webtoon(db_path):
            pass


def test_user_version_future_format_with_force_open_env(tmp_path: Path, monkeypatch):
    """환경 변수로 미래 버전 강제 열기"""
    db_path = tmp_path / "future_force.wbtn"

    future_version = SCHEMA_VERSION + 1000
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA application_id=0x5742544e")
    conn.execute(f"PRAGMA user_version={future_version}")
    conn.execute("CREATE TABLE IF NOT EXISTS info (name TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

    # 환경 변수 설정
    monkeypatch.setenv("WBTN_FORCE_OPEN_FUTURE_FORMAT", "1")

    # 에러 없이 열려야 함
    with Webtoon(db_path) as webtoon:
        assert webtoon.connection.file_user_version == future_version


def test_user_version_past_format_raises_error(tmp_path: Path):
    """과거 버전의 파일 형식은 에러 발생"""
    db_path = tmp_path / "past_version.wbtn"

    # 과거 버전으로 설정 (1 버전대, 현재가 1000대라고 가정)
    past_version = 1
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA application_id=0x5742544e")
    conn.execute(f"PRAGMA user_version={past_version}")
    conn.execute("CREATE TABLE IF NOT EXISTS info (name TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

    # 과거 형식도 열 수 없음
    with pytest.raises(WebtoonSchemaError, match="Cannot open"):
        with Webtoon(db_path):
            pass


def test_user_version_past_format_with_force_open_env(tmp_path: Path, monkeypatch):
    """환경 변수로 과거 버전 강제 열기"""
    db_path = tmp_path / "past_force.wbtn"

    past_version = 1
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA application_id=0x5742544e")
    conn.execute(f"PRAGMA user_version={past_version}")
    conn.execute("CREATE TABLE IF NOT EXISTS info (name TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

    # 환경 변수 설정
    monkeypatch.setenv("WBTN_FORCE_OPEN_PAST_FORMAT", "1")

    # 에러 없이 열려야 함
    with Webtoon(db_path) as webtoon:
        assert webtoon.connection.file_user_version == SCHEMA_VERSION


def test_user_version_same_major_version_compatible(tmp_path: Path):
    """같은 메이저 버전(1000 단위)은 호환됨"""
    db_path = tmp_path / "same_major.wbtn"

    # 같은 메이저 버전 내의 다른 마이너 버전
    # 예: 현재가 1050이면 1001~1999는 모두 호환
    same_major_version = (SCHEMA_VERSION // 1000) * 1000 + 1
    if same_major_version == SCHEMA_VERSION:
        same_major_version += 1  # 정확히 같으면 +1

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA application_id=0x5742544e")
    conn.execute(f"PRAGMA user_version={same_major_version}")
    conn.execute("CREATE TABLE IF NOT EXISTS info (name TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

    # 에러 없이 열려야 함
    with Webtoon(db_path) as webtoon:
        # user_version은 현재 버전으로 업그레이드될 수 있음
        assert webtoon.connection.file_user_version >= same_major_version


def test_user_version_bypass_integrity_check_sets_version(tmp_path: Path):
    """bypass_integrity_check가 True이면 검증 없이 버전 설정"""
    db_path = tmp_path / "bypass_version.wbtn"

    # 잘못된 버전으로 설정
    wrong_version = 999999
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA application_id=0x5742544e")
    conn.execute(f"PRAGMA user_version={wrong_version}")
    conn.execute("CREATE TABLE IF NOT EXISTS info (name TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

    # bypass_integrity_check로 열기
    settings = ConnectionSettings(bypass_integrity_check=True)
    with Webtoon(db_path, connection_settings=settings) as webtoon:
        # 버전이 현재 버전으로 강제 설정됨
        assert webtoon.connection.file_user_version == SCHEMA_VERSION
