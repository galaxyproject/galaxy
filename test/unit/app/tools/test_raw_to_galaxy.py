from galaxy import model
from galaxy.app_unittest_utils.tools_support import UsesApp
from galaxy.tools.parameters.basic import raw_to_galaxy
from galaxy.util.unittest import TestCase


class TestRawToGalaxy(TestCase, UsesApp):
    def setUp(self):
        self.setup_app()
        self.history = model.History(name="test history")
        self.app.model.context.add(self.history)
        self.app.model.context.commit()

    def tearDown(self):
        self.tear_down_app()

    def test_file_default_name(self):
        hda = raw_to_galaxy(self.app, self.history, {"class": "File", "location": "https://example.org/a/1.bed?x=1"})
        assert hda.name == "1.bed"

    def test_file_default_name_leaves_out_userinfo(self):
        for location, name in [
            ("https://proxy.example.org/fetch/https://user:secret@inner.example.org", "inner.example.org"),
            ("https://proxy.example.org/fetch/https://user:12?34@inner.example.org", "[redacted]"),
            ("https://user:12?34@example.org/1.bed", "1.bed"),
        ]:
            hda = raw_to_galaxy(self.app, self.history, {"class": "File", "location": location})
            assert isinstance(hda, model.HistoryDatasetAssociation)
            assert hda.name == name
            assert hda.dataset.sources[0].source_uri == location
