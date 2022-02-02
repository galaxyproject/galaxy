import pytest

from galaxy.webapps.galaxy.services.history_contents import HistoriesContentsService


@pytest.fixture
def mock_init(monkeypatch):
    monkeypatch.setattr(HistoriesContentsService, "__init__", lambda _: None)


class TestSetItemCounts:
    """
    up:         number of displayed items with hid > {hid}
    down:       number of displayed items with hid < {hid}
    total_up:   total number of items with hid > {hid}
    total_down: total number of items with hid < {hid}
    """

    def test_set_item_counts_before(self, mock_init):
        service = HistoriesContentsService()  # type: ignore
        down = 10
        total_up = 90
        total_down = 100
        counts = service._set_item_counts(matches_down=down, total_matches_up=total_up, total_matches_down=total_down)
        self._verify_counts(counts, down=down, total_up=total_up, total_down=total_down)

    def test_set_item_counts_after(self, mock_init):
        service = HistoriesContentsService()  # type: ignore
        up = 9
        total_up = 90
        total_down = 100
        counts = service._set_item_counts(matches_up=up, total_matches_up=total_up, total_matches_down=total_down)
        self._verify_counts(counts, up=up, total_up=total_up, total_down=total_down)

    def test_set_item_counts_near(self, mock_init):
        service = HistoriesContentsService()  # type: ignore
        up = 9
        down = 10
        total_up = 90
        total_down = 100
        counts = service._set_item_counts(
            matches_up=up, matches_down=down, total_matches_up=total_up, total_matches_down=total_down
        )
        self._verify_counts(counts, up=up, down=down, total_up=total_up, total_down=total_down)

    def _verify_counts(self, counts, up=0, total_up=0, down=0, total_down=0):
        # counts of displayed items
        assert counts["matches"] == up + down
        assert counts["matches_up"] == up
        assert counts["matches_down"] == down
        # total counts of matching items
        assert counts["total_matches"] == total_up + total_down + 1
        assert counts["total_matches_up"] == total_up
        assert counts["total_matches_down"] == total_down
