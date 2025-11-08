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
        """
        wbtn에서는 여러가지 pragma statement를 이용해서 웹툰의 상태를 확인하고 관리합니다.

        - application_id
            항상 0x5742544e 값으로 설정되어 있습니다. 이 값은 hex로 "WBTN"에 해당합니다.
            wbtn 패키지는 이 값을 바탕으로 해당 테이블이 wbtn 파일인지 체크합니다.
            파일 확장자나 이름, 파일 구조 등은 패키지가 wbtn 파일로 인식하는지 여부에 관여하지 않습니다.
            오로지 이 값이 웹툰 파일인지 여부를 결정합니다.
            단, 빈 파일이 주어지는 경우 오류를 발생시키는 대신 웹툰 파일을 초기화합니다.
            connection 설정에서 bypass_integrity_check이 False로 설정된 경우 이 값은 체크되지 않으며
            application_id는 0x5742544e 값으로 초기화합니다.

        - user_version
            이 값으로 wbtn 파일의 '스키마' 버전을 확인합니다. 따라서 내부적으로는 스키마 버전이라고 부릅니다.
            기존 SQL 스크립트들과는 호환되지만 기존과는 스키마가 다른 경우 이 값은 1씩 증가합니다.
            새로운 스키마에 기존 SQL 스크립트가 호환되지 않는 경우 셋째 자리에서 올림합니다.
            이 스키마 버전은 올릴 수만 있으며 다운그레이드는 불가합니다.
            현재 버전은 1000이며 미래에는 더 많은 스키마 변화가 있을 수 있습니다.

            스키마 버전이 호환되지 않는다고 여겨질 때 wbtn 패키지는 오류를 발생시키고 종료합니다.
            그러나 어떤 이유에서건 파일을 강제로 열고 싶다면 다음의 두 환경 변수를 이용해 강제로 열도록 할 수 있습니다.
            WBTN_FORCE_OPEN_FUTURE_FORMAT: 웹툰 버전이 상위 버전이고 호환되지 않을 때 오류를 발생시키지 않습니다.
            WBTN_FORCE_OPEN_PAST_FORMAT: 웹툰 버전이 하위 버전이고 호환되지 않을 때 오류를 발생시키지 않습니다.
            두 환경 변수 중 필요한 값을 0이 아닌 값으로 설정하면 파일을 열 수 있습니다.

            connection 설정에서 bypass_integrity_check이 False로 설정된 경우 이 값은 체크되지 않으며
            user_version은 현재 wbtn 패키지의 스키마 버전으로 초기화됩니다.

        - foreign_keys=ON
            외래 키를 활성화합니다. 외래 키 관련 동작이 일어날 수 있도록 합니다.

        - journal_mode
            웹툰 파일의 저널링 방식을 변경합니다. 자세한 설명은 다음 문서를 확인하세요.
            https://sqlite.org/pragma.html#pragma_journal_mode

            기본값은 sqlite의 기본값인 DELETE로 설정되어 있습니다.
            값을 변경하려면 connection 설정에서 journal_mode를 변경하세요.
        """
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
        if journal_mode is None:
            return
        if self.in_memory and journal_mode not in ("memory", "off"):
            raise WebtoonOpenError(f"Invalid journal mode for in-memory database: {journal_mode}")
        if journal_mode not in JOURNAL_MODES:
            raise WebtoonOpenError(f"Invalid journal mode: {journal_mode}")
        self._connection().execute(f"PRAGMA journal_mode={journal_mode}")

    def _delete_indices(self) -> None:
        with self.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS episodes_idx")

    def _add_tables(self) -> None:
        """
        wbtn은 다양한 테이블을 이용해 정보를 관리합니다.

        ## value의 처리 방식

        모든 사용자의 커스텀 값을 받을 수 있는 테이블들에서는 conversion과 value column이 존재합니다.
        일부 column은 path column까지 존재할 수도 있습니다.

        Sqlite와 파이썬은 서로 운용하는 타입 시스템이 다르고 특별한 처리를 요구하는 경우가 종종 있습니다.
        가장 간단한 예로 파이썬은 True와 False가 존재하지만 이 둘은 Sqlite에 들어가면 1과 0으로 처리됩니다.
        이렇게 처리된 데이터를 다시 파이썬으로 불러오게 되면 원래의 boolean 값이 아닌 1과 0으로 불러와집니다.
        이런 문제를 방지하기 위해 웹툰 파일에 데이터를 저장할 때 파이썬으로 다시 불러올 때에 타입을 정상적으로 복구하기
        위해서 conversion이라는 column에 별도의 타입 정보를 저장합니다.
        이 conversion의 값은 값을 저장할 때 값을 어떻게 불러올지에 대한 정보를 저장하고 값을 로드할 때 이 값을 기준으로
        값을 복구하게 됩니다.

        ## 테이블들

        - Info
            웹툰에 대한 다양한 정보와 메타데이터를 저장합니다.
            name에는 정보의 이름, conversion/value에는 값이 기록됩니다.
            name이 sys_로 시작되는 경우 특별한 시스템 정보입니다.
            이러한 데이터들은 변경, 수정하는 데에 특별한 제약이 따를 수 있습니다.
        - Episode/EpisodeInfo
            Episode 테이블은 웹툰의 회차를 표현합니다.
            Episode 테이블 자체에는 거의 데이터가 존재하지 않기 때문에
            대부분의 Episode와 관련된 정보는 EpisodeInfo에 저장됩니다.
        - Content/ContentInfo
            Content의 ExtraFile가 더불어 value를 path에 저장할 수 있는 특별한 옵션이 있습니다.
            path는 base path와의 상대적인 경로가 기록되며 경로가 로드되거나 덤프될 때 자동으로 실제 경로로 변환됩니다.
            자세한 내용은 [WebtoonPathManager](./_path/WebtoonPathManager)를 참고하세요.

            ContentInfo는 Content에 담을수 없는 추가적인 Content에 대한 정보를 담는 역할을 합니다.
            예를 들어 해당 Content의 MIME type이나 이미지 파일의 높이와 너비, 현재 상태 등의 다양한 메타데이터를 저장할 수 있습니다.
            단, ContentInfo는 path를 활용해 외부 데이터로 저장할 수 없습니다. path가 필요한 경우
            Content나 ExtraFile로 데이터를 추가하세요.
        - ExtraFile
            웹툰 디렉토리에 존재하는 부가적인 파일에 대한 정보를 보관할 수 있습니다.
            Info의 경우 반드시 table 내부에 값이 보관되어 있어야 하지만 ExtraFile 테이블에 저장된 경우
            데이터가 외부 경로에 저장될 수 있습니다.
            또한, Info는 웹툰의 정보를 담기 위해 디자인된 반면, ExtraFile은 Content로는 표현될 수 없는
            추가적인 파일들에 대한 사항을 기록하기 위해 디자인되었습니다.

        위에 명시된 6개의 table만 문제 없이 존재한다면 웹툰 파일을 인식할 수 있습니다.
        사용자는 별도의 테이블이나 인덱스를 만들어 웹툰 파일을 보충할 수도 있습니다.
        """
        with self.cursor() as cur:
            # sqlite의 문서에서는 WITHOUT ROWID를 사용할 때는 성능을 위해 각각의 row가 200바이트를 넘지 않을 것을 권장하고 있지만
            # info 테이블에서 그 값을 넘어서는 값이 들어갈 확률이 꽤 있기에
            # 혹시나 모를 특정한 상황에서의 성능 하락을 막기 위해 WITHOUT ROWID를 사용하지 않음.
            cur.execute("CREATE TABLE IF NOT EXISTS Info (name TEXT UNIQUE NOT NULL, conversion TEXT, value)")
            # table 이름을 복수로 해야 하는지 단수로 해야 하는지, case는 어떻게 해야 하는지는 사람마다 의견이 다르기에 여기서는 내 선호대로 복수형, snake case를 사용
            # 참고로 'information'은 uncountable이므로 info로만 사용
            # 참고1: https://stackoverflow.com/questions/338156/table-naming-dilemma-singular-vs-plural-names
            # 참고2: https://stackoverflow.com/questions/7662/database-table-and-column-naming-conventions
            # name, id, state와 같은 값들은 standard extra columns로 정의하기
            cur.execute("""CREATE TABLE IF NOT EXISTS Episode (
                -- 구분자들
                episode_no INTEGER PRIMARY KEY NOT NULL,
                -- 시간 정보
                added_at TIMESTAMP NOT NULL
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS EpisodeInfo (
                -- 구분자들
                episode_no INTEGER NOT NULL,
                kind TEXT NOT NULL,
                -- 데이터
                value,
                conversion TEXT,
                -- table constraints
                UNIQUE (episode_no, kind) ON CONFLICT ABORT,
                FOREIGN KEY(episode_no) REFERENCES Episode(episode_no) ON DELETE CASCADE ON UPDATE CASCADE
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS Content (
                -- 구분자들
                content_id INTEGER PRIMARY KEY NOT NULL,
                episode_no INTEGER NOT NULL,
                content_no INTEGER NOT NULL,
                kind TEXT NOT NULL,
                -- 데이터
                value,
                conversion TEXT,
                path,
                -- 시간 정보
                added_at TIMESTAMP NOT NULL,
                -- table constraints
                UNIQUE (episode_no, content_no, kind) ON CONFLICT ABORT,
                FOREIGN KEY(episode_no) REFERENCES Episode(episode_no) ON DELETE CASCADE ON UPDATE CASCADE
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS ContentInfo (
                -- 구분자들
                content_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                -- 데이터
                value,
                conversion TEXT,
                -- table constraints
                UNIQUE (content_id, kind) ON CONFLICT ABORT,
                FOREIGN KEY(content_id) REFERENCES Content(content_id) ON DELETE CASCADE ON UPDATE CASCADE
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS ExtraFile (
                -- 구분자들
                file_id INTEGER PRIMARY KEY NOT NULL,
                kind TEXT,
                -- 데이터 (path가 구분자 역할도 겸함)
                value,
                conversion TEXT,
                path UNIQUE NOT NULL,
                -- 시간 정보
                added_at TIMESTAMP NOT NULL
            )""")
            # cur.execute("CREATE INDEX EpisodeIdx ON Episode ()")
            # cur.execute("CREATE INDEX EpisodeInfoIdx ON EpisodeInfo ()")
            # cur.execute("CREATE INDEX ContentIdx ON Content ()")
            # cur.execute("CREATE INDEX ContentInfoIdx ON ContentInfo ()")
            # cur.execute("CREATE INDEX ExtraFileIdx ON ExtraFile ()")

    def _add_info(self) -> None:
        with self.cursor() as cur:
            current_time = timestamp()
            if not self.existed:
                cur.execute("""
                    INSERT INTO Info (name, conversion, value) VALUES
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
