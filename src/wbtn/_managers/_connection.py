from __future__ import annotations

import os
import sqlite3
import typing
import warnings
from contextlib import closing, contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path

from .._base import JOURNAL_MODES, JournalModes, WebtoonConnectionError, WebtoonOpenError, WebtoonSchemaError, timestamp
from .._base import SCHEMA_VERSION as user_version
from .._base import VERSION as version

if typing.TYPE_CHECKING:
    from _typeshed import StrOrBytesPath as Pathlike

__all__ = ("WebtoonConnectionManager", "ConnectionSettings")


@dataclass(slots=True)
class ConnectionSettings:
    read_only: bool = False
    create_db: bool = True
    clear_existing_db: bool = False
    journal_mode: JournalModes | None = None
    bypass_integrity_check: bool = False
    _configure_pragma_only = False


class WebtoonConnectionManager:
    # __slots__ = (
    #     "path",
    #     "settings",
    #     "_conn",
    #     "in_memory",
    #     "existed",
    # )

    def __init__(
        self,
        path: Pathlike,
        settings: ConnectionSettings | None = None,
    ) -> None:
        self.path: Path | None = None if path == ":memory:" else Path(os.fsdecode(path))
        self.settings: ConnectionSettings = settings or ConnectionSettings()
        self._conn = None

    def __enter__(self) -> typing.Self:
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def connect(self) -> None:
        if self._conn:
            return
        try:
            self._connect()
            self._configure_pragma()
            if not self.settings.read_only and not self.settings._configure_pragma_only:
                self._add_tables()
                self._add_info()
        except BaseException:
            if self._conn:
                try:
                    self._conn.close()
                finally:
                    self._conn = None
            raise

    def close(self) -> None:
        if self._conn:
            self._conn.close()
        self._conn = None

    def _connection(self, write: bool | None = True) -> sqlite3.Connection:
        """연결 조건들을 확인합니다. WebtoonConnectionManager 내부에서만 사용되어야 하며 write 파라미터를 통한 read_only 여부 체크는 WebtoonConnectionManager 내부 일부 pragma 설정 함수들만 사용해야 합니다."""
        if self._conn is None:
            raise WebtoonConnectionError("Connection is not initialized or already finalized.")
        if write and self.settings.read_only:
            raise WebtoonConnectionError("Attempt to write using read-only connection")
        return self._conn

    @contextmanager
    def cursor(self) -> typing.Iterator[sqlite3.Cursor]:
        conn = self._connection(write=None)
        with conn, closing(conn.cursor()) as cur:
            yield cur

    @property
    def file_user_version(self) -> int:
        user_version, = self._connection(write=False).execute("PRAGMA user_version").fetchone()
        return user_version

    @file_user_version.setter
    def file_user_version(self, user_version: int) -> None:
        if self.file_user_version > user_version:
            raise WebtoonSchemaError(f"User version of file cannot be updated because the files' version ({self.file_user_version}) is higher than the version to set ({user_version}) (cannot downgrade).")
        else:
            # 호오옥시 모를 SQL 인젝션을 방어하기 위해 타입 확인 추가
            # 물론 실수를 막을 수 있다 정도지 완전히 안전한 건 전혀 아님.
            self._connection().execute(f"PRAGMA user_version={int(user_version)}")

    def _connect(self) -> None:
        assert not self._conn, "Connection is already initialized."

        if self.path is None:
            # file::memory:?mode=...으로 모드를 설정할 수 있기는 하나 별로 쓸모는 없기에 그냥 다른 모드는 사용하지 못하도록 함.
            if self.settings.read_only:
                raise WebtoonOpenError(
                    "Cannot set read_only when writing at memory."
                )
            if not self.settings.create_db:
                raise WebtoonOpenError(
                    "Memory database need to be created. Invalid flag."
                )
            self.in_memory = True
            self.existed = False
            self._conn = sqlite3.connect(":memory:")
            return

        path = self.path
        # 비어있지 않은 존재하는 파일은 존재하는 것으로 간주
        self.in_memory = False
        match self.settings.read_only, self.settings.create_db, self.settings.clear_existing_db:
            case True, _, _:
                mode = "ro"
            case False, False, False:
                mode = "rw"
            case False, True, False:
                mode = "rwc"
                path.touch(exist_ok=True)
            case False, create_db, True:
                mode = "rwc"
                path.unlink(missing_ok=create_db)
                path.touch()
            case _:
                raise WebtoonOpenError("Invalid set of flags.")
        self.existed = path.exists() and path.stat().st_size != 0

        # We use the URI format when opening the database.
        uri = self._normalize_uri(path)
        uri = f"{uri}?mode={mode}"

        try:
            # unfortunately autocommit=False is BROKEN. Yon can't set pragmas reliably.
            # See https://stackoverflow.com/questions/78898176/ for more details.
            # self.conn = sqlite3.connect(uri, autocommit=False, uri=True)
            self._conn = sqlite3.connect(uri, uri=True)
        except sqlite3.Error as exc:
            raise WebtoonOpenError(f"Failed to connect to the webtoon file") from exc

    @staticmethod
    def _normalize_uri(path: Path) -> str:
        uri = path.absolute().as_uri()
        while "//" in uri:
            uri = uri.replace("//", "/")
        return uri

    def _configure_pragma(self) -> None:
        if not self.settings.bypass_integrity_check:
            self._check_application_id()
            self._check_user_version()

        if self.settings.read_only:
            return

        conn = self._connection()

        if not self.existed:
            conn.execute(f"PRAGMA application_id=0x5742544e")
        if self.settings.bypass_integrity_check:
            conn.execute(f"PRAGMA user_version={int(user_version)}")
        else:
            with suppress(WebtoonSchemaError):
                self.file_user_version = user_version

        self._set_journal_mode()
        conn.execute("PRAGMA foreign_keys=ON")
        conn.commit()

    def _check_application_id(self) -> None:
        if not self.existed:
            return
        # 'WBTN'을 뜻하는 bytes
        # assert bytes.fromhex("5742544e") == b"WBTN"
        APPLICATION_ID = 0x5742544e
        # 파일이 존재했었다면 application_id를 통해 WBTN 파일인지 확인
        application_id, = self._connection(write=False).execute("PRAGMA application_id").fetchone()
        if application_id == 0:
            # webtoon 파일이나 initialize되지 않았을 수도 있고, 그냥 webtoon 파일이 아닌 다른 sqlite 데이터베이스일 수도 있음.
            # 첫 번째일 경우 id를 초기화하는 것이 정당화될 수 있지만 두 번째는 아님. 따라서 user_version과는 다르게 초기화하지 않고
            # 오류를 발생시킴
            raise WebtoonSchemaError("The file is not a WBTN file. Application ID is not initialized.")
        if APPLICATION_ID != application_id:
            raise WebtoonSchemaError("The file is not a WBTN file")

    def _check_user_version(self) -> None:
        # user_version은 1000에서 시작.
        # 만약 다른 파일을 받았을 때 1000으로 정수 나눗셈한 값이 2 이상이 된다면 호환되지 않는 스키마로 간주됨.
        if not self.existed:
            return
        if self.file_user_version == 0:
            if self.settings.read_only:
                warnings.warn("Webtoon file schema version is not initialized.", UserWarning)
            else:
                warnings.warn("Webtoon file schema version is not initialized. Initialize to the current version.", UserWarning)
                self.file_user_version = int(user_version)
            return
        if user_version // 1000 < self.file_user_version // 1000:
            if os.getenv("WBTN_FORCE_OPEN_FUTURE_FORMAT", "0") == "0":
                raise WebtoonSchemaError(
                    f"Cannot open future file format: V{self.file_user_version}. "
                    "to force open the file, set WBTN_FORCE_OPEN_FUTURE_FORMAT environment variable to 1."
                )
        if user_version // 1000 > self.file_user_version // 1000:
            if os.getenv("WBTN_FORCE_OPEN_PAST_FORMAT", "0") == "0":
                raise WebtoonSchemaError(
                    f"Cannot open future file format: V{self.file_user_version}. "
                    "to force open the file, set WBTN_FORCE_OPEN_PAST_FORMAT environment variable to 1."
                )

    def _set_journal_mode(self) -> None:
        journal_mode = None if self.settings.journal_mode is None else str(self.settings.journal_mode).lower()
        if self.in_memory and journal_mode not in (None, "memory", "off"):
            raise WebtoonOpenError(f"Invalid journal mode for in-memory database: {journal_mode}")
        if journal_mode is not None and journal_mode not in JOURNAL_MODES:
            raise WebtoonOpenError(f"Invalid journal mode: {journal_mode}")
        self._connection().execute(f"PRAGMA journal_mode={journal_mode}")

    def _delete_indices(self) -> None:
        with self.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS episodes_idx")

    def _add_tables(self) -> None:
        with self.cursor() as cur:
            # sqlite의 문서에서는 WITHOUT ROWID를 사용할 때는 성능을 위해 각각의 row가 200바이트를 넘지 않을 것을 권장하고 있지만
            # info 테이블에서 그 값을 넘어서는 값이 들어갈 확률이 꽤 있기에
            # 혹시나 모를 특정한 상황에서의 성능 하락을 막기 위해 WITHOUT ROWID를 사용하지 않음.
            cur.execute("CREATE TABLE IF NOT EXISTS info (name TEXT PRIMARY KEY NOT NULL, conversion TEXT, value)")
            # table 이름을 복수로 해야 하는지 단수로 해야 하는지, case는 어떻게 해야 하는지는 사람마다 의견이 다르기에 여기서는 내 선호대로 복수형, snake case를 사용
            # 참고로 'information'은 uncountable이므로 info로만 사용
            # 참고1: https://stackoverflow.com/questions/338156/table-naming-dilemma-singular-vs-plural-names
            # 참고2: https://stackoverflow.com/questions/7662/database-table-and-column-naming-conventions
            cur.execute("""CREATE TABLE IF NOT EXISTS episodes (
                episode_no INTEGER PRIMARY KEY NOT NULL,
                name TEXT,
                state,
                id UNIQUE,
                added_at TIMESTAMP NOT NULL
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS episodes_extra (
                episode_no INTEGER NOT NULL,
                purpose NOT NULL,
                conversion TEXT,
                value,
                UNIQUE (episode_no, purpose) ON CONFLICT ABORT,
                FOREIGN KEY(episode_no) REFERENCES episodes(episode_no) ON DELETE CASCADE ON UPDATE CASCADE
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS media (
                id INTEGER PRIMARY KEY NOT NULL,
                episode_no INTEGER NOT NULL,
                media_no INTEGER NOT NULL,
                purpose NOT NULL,
                state,
                media_type TEXT,
                name TEXT,
                conversion TEXT,
                path,
                data,
                added_at TIMESTAMP NOT NULL,
                UNIQUE (episode_no, media_no, purpose) ON CONFLICT ABORT,
                FOREIGN KEY(episode_no) REFERENCES episodes(episode_no) ON DELETE CASCADE ON UPDATE CASCADE
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS extra_files (
                id INTEGER PRIMARY KEY NOT NULL,
                purpose TEXT,
                conversion TEXT,
                path UNIQUE NOT NULL,
                data BLOB,
                added_at TIMESTAMP NOT NULL
            )""")
            # cur.execute("CREATE INDEX episodes_idx ON episodes (state, added_at)")
            # cur.execute("CREATE INDEX episodes_extra_idx ON episodes_extra (episode_no, purpose, conversion, value)")
            # cur.execute("CREATE INDEX media_idx ON media (episode_no, media_no, purpose, state, name, added_at)")

    def _add_info(self) -> None:
        with self.cursor() as cur:
            current_time = timestamp()
            if not self.existed:
                cur.execute("""
                    INSERT INTO info (name, conversion, value) VALUES
                    -- about schema
                    ('sys_agent', NULL, 'wbtn-python'),
                    ('sys_agent_version', NULL, :version),
                    ('sys_created_at', NULL, :created_at),
                    -- about filesystem
                    ('sys_base_directory', NULL, NULL),
                    -- about webtoon
                    ('sys_packager', NULL, NULL),
                    ('sys_platform', NULL, NULL)
                    -- ('single_episode', NULL, FALSE),
                    -- ('consecutive_episode', NULL, FALSE),
                    -- ('authors', 'json', json('[]')),
                    -- ('url', NULL, NULL),
                    -- ('title', NULL, NULL),
                    -- ('id', NULL, NULL),
                    -- 페이지 형식 웹툰을 구성할 때 필요한 정보. 설정되지 않는다면 일반적인 웹툰 형식으로 간주됨
                    -- ('format', NULL, NULL),  -- 'webtoon', 'page', 'rtl_page', 'blog' 등으로 설정 가능
                    -- 한 장에 두 장씩 있는 형태인지, 단순히 페이지가 있는 형태인지 구분함. 만약 페이지 형식이기만 하나면 1을, 한 장에 두 페이지가 있는 형태라면 2를 사용
                    -- ('page_number', NULL, NULL),
                    -- 페이지에 오프셋이 있는지 정보. 0이면 표지 없이 하나의 장이 구성되고, 1이면 표지는 한 페이지로 하고 나머지로 한 장이 구성됨.
                    -- ('offset', NULL, NULL)
                """, dict(
                    version=version,
                    created_at=current_time,
                ))
            # 반드시 필요한지 잘 모르겠음. 스키마가 업데이트되었을 때 sys_version을 그냥 올리는 게 나을 것 같음
            # # 이 메소드는 '항상' not read only일 때만 실행되기 때문에
            # # 완전히 필요 없는 컨디션이지만 어차피 cost도 별로 없고 또 혹시 모르니깐...
            # if not self.settings.read_only:
            #     cur.execute("""
            #         INSERT OR REPLACE INTO info (name, json_encoded, value) VALUES
            #         ('sys_last_opened_version', FALSE, :opened_version),
            #         ('sys_last_opened_at', FALSE, :opened_at)
            #     """, dict(
            #         opened_version=version,
            #         opened_at=current_time,
            #     ))
