import os
from pathlib import Path

from galaxy.util.unittest_utils.test_http_server import RecordingHttpServer
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver.integration_util import IntegrationTestCase

TOOL_ID = "select_from_url_depends_on"

TOOL_PATH = Path(__file__).resolve().parents[1] / "functional/tools/select_from_url_depends_on.xml"
OPTIONS_SERVER_PLACEHOLDER = "http://options-server.invalid"


class TestSelectFromUrlDependsOn(IntegrationTestCase):
    options_server: RecordingHttpServer
    dataset_populator: DatasetPopulator

    @classmethod
    def setUpClass(cls):
        # The tool's URLs point at this server, so it must be up before Galaxy loads the tool.
        cls.options_server = RecordingHttpServer()
        cls.options_server.start()
        try:
            super().setUpClass()
        except BaseException:
            cls.options_server.stop()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            cls.options_server.stop()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        tool_dir = cls.temp_config_dir("select_from_url_depends_on")
        os.makedirs(tool_dir, exist_ok=True)
        assert cls.options_server.base_url
        with open(os.path.join(tool_dir, "tool.xml"), "w") as f:
            f.write(TOOL_PATH.read_text().replace(OPTIONS_SERVER_PLACEHOLDER, cls.options_server.base_url))
        tool_conf = os.path.join(tool_dir, "tool_conf.xml")
        with open(tool_conf, "w") as f:
            f.write(f'<toolbox tool_path="{tool_dir}"><tool file="tool.xml"/></toolbox>')
        config["tool_config_file"] = tool_conf

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.options_server.clear()
        self.options_server.add_json_route("/crops", [["Maize", "maize"], ["Wheat", "wheat"]])
        self.options_server.add_json_route("/crops/maize/genotype_sets", [["Maize panel", "maize_panel"]])
        self.options_server.add_json_route(
            "/crops/wheat/genotype_sets", [["Wheat panel 1", "wheat_panel_1"], ["Wheat panel 2", "wheat_panel_2"]]
        )
        self.options_server.add_json_route(
            "/genotype_sets?crops=maize,wheat", [["Maize panel", "maize_panel"], ["Wheat panel 1", "wheat_panel_1"]]
        )

    def _build(self, inputs=None):
        history_id = self.dataset_populator.new_history()
        tool_state = self.dataset_populator.build_tool_state(TOOL_ID, history_id, inputs)
        return {tool_input["name"]: tool_input for tool_input in tool_state["inputs"]}

    def _genotype_set_requests(self):
        return [request for request in self.options_server.requests if request.path != "/crops"]

    def test_crop_refreshes_genotype_sets(self):
        inputs = self._build()
        assert inputs["crop"]["refresh_on_change"] is True
        assert inputs["genotype_set"]["options"] == []
        assert self._genotype_set_requests() == []

        inputs = self._build({"crop": "maize"})
        assert inputs["genotype_set"]["options"] == [["Maize panel", "maize_panel", False]]

        inputs = self._build({"crop": "wheat"})
        assert inputs["genotype_set"]["options"] == [
            ["Wheat panel 1", "wheat_panel_1", False],
            ["Wheat panel 2", "wheat_panel_2", False],
        ]
        requests = self._genotype_set_requests()
        assert [request.path for request in requests] == [
            "/crops/maize/genotype_sets",
            "/crops/wheat/genotype_sets",
        ]
        assert [request.headers["x-crop"] for request in requests] == ["maize", "wheat"]

    def test_repeat_dependencies(self):
        inputs = self._build({"queries_0|query_crop": "maize", "queries_1|query_crop": "wheat"})
        query_sets = [
            {tool_input["name"]: tool_input for tool_input in instance}["query_set"]["options"]
            for instance in inputs["queries"]["cache"]
        ]
        assert query_sets == [
            [["Maize panel", "maize_panel", False]],
            [["Wheat panel 1", "wheat_panel_1", False], ["Wheat panel 2", "wheat_panel_2", False]],
        ]
        assert inputs["all_query_sets"]["options"] == [
            ["Maize panel", "maize_panel", False],
            ["Wheat panel 1", "wheat_panel_1", False],
        ]

        inputs = self._build({"queries_0|query_crop": "maize", "queries_1|query_crop": None})
        assert inputs["all_query_sets"]["options"] == []

    def test_run_with_dependent_value(self):
        history_id = self.dataset_populator.new_history()
        run = self.dataset_populator.run_tool(TOOL_ID, {"crop": "wheat", "genotype_set": "wheat_panel_2"}, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=run["outputs"][0])
        assert content == "wheat wheat_panel_2\n"
