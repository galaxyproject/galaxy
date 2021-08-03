from galaxy_test.driver import integration_util


class EdamToolboxIntegrationTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True

    def setUp(self):
        super().setUp()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["enable_beta_edam_toolbox"] = True

    def test_edam_toolbox(self):
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True))
        index_as_list = index.json()
        sections = [x for x in index_as_list if x["model_class"] == "ToolSection"]
        section_names = [s["name"] for s in sections]
        assert "Mapping" in section_names
        mapping_section = [s for s in sections if s["name"] == "Mapping"][0]
        mapping_section_elems = mapping_section["elems"]
        # make sure our mapper tool was mapped using Edam correctly...
        assert [x for x in mapping_section_elems if x["id"] == "mapper"]
