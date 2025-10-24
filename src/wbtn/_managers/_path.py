from __future__ import annotations

import os
from pathlib import Path
from .._base import WebtoonType

from .._base import (
    WebtoonPathError,
    WebtoonPathInitializationError,
)
from .._json_data import JsonData

__all__ = ("WebtoonPathManager",)


class WebtoonPathManager:
    _base_path: Path | None = None
    """
    웹툰 파일에는 절대 경로를 저장하거나 로드할 수 없습니다.
    base_path는 경로를 웹툰 파일에 저장되는 상대 경로의 '기준'이 되는 path입니다.
    따라서, 웹툰에 경로 정보를 저장하거나 불러올 때는 일반적인 경로를 사용하지만,
    그 정보들이 웹툰 파일 내에 저장될 때에는 base_path를 기준으로 하는 상대 경로가 저장됩니다.

    예를 들면 다음과 같습니다.
    base_path를 `media`라고 설정했다고 해봅시다.
    그리고 `media/001.jpg`라는 경로를 웹툰 파일에 저장하도록 요청했다고 해봅시다.
    이 파일의 경로의 `media`라는 base_path에 대한 상대적인 위치는 `001.jpg`입니다.
    따라서 이 경로가 웹툰 파일에 저장될 때에는 `001.jpg`로 저장됩니다.

    웹툰 파일에 저장되어 있는 미디어를 불러올 때도 마찬가지입니다.
    웹툰 파일에는 이제 `001.jpg`라는 경로가 저장되어 있습니다.
    이 경로를 불러오게 되면, base_path의 subpath로 이 값이 붙게 되어
    최종적으로 리턴되는 값은 `media/001.jpg`가 됩니다.

    이렇게 번거로운 작업을 왜 거칠까요?
    가장 기본적인 이유는 웹툰 파일은 portability를 높이기 위해서입니다.
    base_path는 따로 설정하지 않아도 기본적으로 '웹툰 파일이 위치하고 있는
    폴더'로 설정되어 있습니다. 따라서 웹툰 파일과 미디어 파일을 통째로 옮기게 되면
    웹툰 파일과 미디어 파일 간의 상대적인 경로는 그대로 유지되므로 파일을 그대로 사용할 수 있습니다.

    또한, 기본적으로 상대 경로의 기준은 current working directory인데, 이 값은 실행하는 환경에 따라 언제나 바뀔 수 있습니다.
    웹툰 파일을 실행한 주체에 상관없이 웹툰 파일의 경로를 안정적으로 저장하고 불러오려면 항상 고정적인 경로의 기준이 필요합니다.

    다른 이유는 혹시 모를 파일 corruption과 보안 문제와 피하기 위해서입니다.
    웹툰 파일에 절대 경로를 허용하게 되면 웹툰 파일은 특정한 고정된 시스템 파일에 접근하게 될 수도 있습니다.
    이게 보안 위협으로 다가올 가능성은 낮습니다; 웹툰 파일 자체는 단순히 데이터베이스 파일일 뿐이며 이 파일을 읽는 것은
    익명의 존재가 아니라 웹툰 파일을 읽는 리더이기 때문입니다.
    그러나 웹툰 리더 소프트웨어에서 파일을 삭제하거나 수정하는 코드가 있다면 중요한 파일에 간섭을 발생시킬 수 있고,
    단순히 읽는 코드라 하더라도 만약 파일의 크기가 너무 크거나 한다면 메모리 부족 등으로 프로그램이 멈출 수 있습니다.
    이런 문제가 발생하는 것을 피하기 위해 번거롭지만 base directory 설정이 필수적으로 요구되는 것입니다.
    """
    convert_absolute: bool = True
    """
    웹툰 파일에 경로를 저장할 때 절대 경로가 들어온 경우 상대 경로로의 전환을 시도할지 결정합니다.
    이 값이 거짓이라면 절대 경로가 주어졌을 때 항상 오류가 발생하며,
    이 값이 참이면 만약 상대 경로로 변환한 결과 base_path의 하위 경로가 아니라면 오류가 발생합니다.

    이 값은 경로를 불러올 때와는 무관합니다. 경로를 불러왔을 때 절대 경로인 경우
    이 값과는 무관하게 항상 오류가 발생합니다.
    """
    self_contained: bool = False
    """
    이 값이 True로 설정된 경우 self-contained 모드가 활성화됩니다.
    self-contained 상태에서는 이 경우에는 path에 접근하는 것이 완전히 거부됩니다.
    path를 저장할 수도 로드할 수도 없으며 모든 데이터가 웹툰 파일 내부에 저장되어야 합니다.
    """
    zip_path_support: bool = False
    """
    zip path를 활성화할지에 대한 플래그로 예정되어 있습니다. 현재는 구현되어 있지 않습니다.
    """
    fallback_base_path: bool = True
    """
    설정되어 있다면 오류를 발생시키는 대신 기본값으로 fallback합니다.
    거짓이면 잘못된 base directory가 제안되었을 때
    WebtoonPathInitializationError 오류를 발생시킵니다.
    """
    auto_initialize_base_path: bool = True
    """
    활성화되어 있다면 base_path를 자동으로 초기화합니다.
    꺼져 있다면 초기화되지 않은 상태에서 base_path를 사용하려 할 경우
    WebtoonPathInitializationError 오류를 발생시킵니다.
    """

    def __init__(self, webtoon: WebtoonType):
        self.webtoon = webtoon

    def dump(self, path: Path | None) -> str | None:
        return path and self.dump_str(path)

    def dump_str(self, path: Path) -> str:
        return str(self._dump_path(path))

    def load(self, raw_path: str | None) -> Path | None:
        return raw_path if raw_path is None else self.load_str(raw_path)

    def load_str(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            raise WebtoonPathError("Absolute path is not allowed.")
        return self.base_path / path

    def file_base_path(self) -> Path:
        """
        웹툰 파일이 주재하는 디렉토리의 경로를 반환합니다.
        만약 :memory: 연결인 경우 cwd를 값으로 리턴합니다.
        """
        if self.webtoon.connection.in_memory:
            # memory의 경우에는 캐싱하지 않는 방향으로도 고민해보면 좋을 듯
            return Path.cwd()
        else:
            return Path(os.fsdecode(self.webtoon.connection.path)).parent  # type: ignore

    def suggested_base_path(self) -> Path | None:
        """
        파일이 직접 제안한 base directory를 리턴합니다.
        이 값은 위험할 수도 있으니 직접 사용해선 안 되고 반드시 직접 확인해야 합니다.
        만약 절대 경로라면 별다른 이유가 없다면 반드시 거부해야 하고,
        file_folder_location이나 그 하위의 경로가 아니라면 반드시 적절한 요청인지 체크해야 합니다.
        """
        raw_base_directory = self.webtoon.info.get("sys_base_directory")
        if isinstance(raw_base_directory, JsonData):
            raw_base_directory = raw_base_directory.load()
        if raw_base_directory is None or not isinstance(raw_base_directory, (str, bytes)):
            return None
        else:
            return Path(os.fsdecode(raw_base_directory))

    def transform(self, path, old_base_path: Path, current_base_path: Path | None = None) -> Path:
        raise NotImplementedError()
        return (old_base_path / path).relative_to(current_base_path or self.base_path)

    def initialize_base_path(self, path: Path | None = None) -> Path:
        # path가 직접 제공된 경우 별도의 체크 없이 바로 초기화되니 꼭!!! 안전한 값만 path로 제공해야 함
        self._base_path = self._get_base_path(path).resolve()
        return self._base_path

    @property
    def base_path(self) -> Path:
        if self.self_contained:
            raise WebtoonPathError("Self-contained mode is activated. Cannot dump or load a path.")
        if self._base_path is None:
            if self.auto_initialize_base_path:
                return self.initialize_base_path()
            raise WebtoonPathInitializationError("Webtoon path is not yet initialized.")
        else:
            return self._base_path

    @base_path.setter
    def base_path(self, path: Path | None) -> None:
        """직접 값을 제공한 경우라고 base_path는 resolve됩니다."""
        self.initialize_base_path(path)

    def _dump_path(self, path: Path) -> Path:
        if path.is_absolute() and not self.convert_absolute:
            raise WebtoonPathError("Absolute path cannot be stored in the file.")
        return path.resolve().relative_to(self.base_path)

    def _get_base_path(self, path: Path | None = None) -> Path:
        if self._base_path:
            raise WebtoonPathInitializationError("Base path has already been initialized.")

        if path is not None:
            return path

        path = self.suggested_base_path()
        if path is None:
            return self.file_base_path()

        if path.is_absolute():
            if self.fallback_base_path:
                raise WebtoonPathInitializationError("Suggested base directory is an absolute path", "SUGGESTED_BASE_PATH_ABSOLUTE")
            return self.file_base_path()

        file_folder = self.file_base_path()
        try:
            path.resolve().relative_to(file_folder.resolve())
        except ValueError as exc:
            if self.fallback_base_path:
                raise WebtoonPathInitializationError("Suggested base directory is not a subtree of webtoon file's folder", "SUGGESTED_BASE_PATH_NOT_CHILD") from exc
            return file_folder
        else:
            return path
