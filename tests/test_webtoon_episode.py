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
    with Webtoon(path, connection_mode="n") as w:
        ep_no = w.episode.add(id="epX", name="Episode X", state="published")
        # use cursor to fetch episode via classmethod
        with w.connection.cursor() as cur:
            episode = WebtoonEpisode.from_episode_no(ep_no, cur)

        assert episode.episode_no == ep_no
        assert episode.name == "Episode X"
        assert episode.state == "published"
        assert episode.episode_id == "epX"
        # added_at should be a datetime
        assert isinstance(episode.added_at, datetime.datetime)
