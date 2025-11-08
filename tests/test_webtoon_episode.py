import datetime
import sys
from pathlib import Path

# Ensure src is importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbtn import Webtoon
from wbtn._webtoon import WebtoonEpisode


def test_webtoon_episode_from_episode_no(tmp_path):
    path = tmp_path / "episode_from_no.wbtn"
    with Webtoon(path) as webtoon:
        episode = webtoon.episode.add(123)
        episode["name"] = "Hello World Episode"
        episode["state"] = "downloaded"

        assert episode["name"] == "Hello World Episode"
        assert episode["state"] == "downloaded"
        assert episode.episode_no == 123
        # added_at should be a datetime
        assert isinstance(episode.added_at, datetime.datetime)
