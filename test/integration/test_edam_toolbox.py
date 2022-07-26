from galaxy_test.driver import integration_util


class EdamToolboxIntegrationTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["edam_panel_views"] = "merged"

    def test_edam_toolbox(self):
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True, view="ontology:edam_merged"))
        index.raise_for_status()
        index_as_list = index.json()
        sections = [x for x in index_as_list if x["model_class"] == "ToolSection"]
        section_names = [s["name"] for s in sections]
        assert "Mapping" in section_names
        mapping_section = [s for s in sections if s["name"] == "Mapping"][0]
        mapping_section_elems = mapping_section["elems"]
        # make sure our mapper tool was mapped using Edam correctly...
        assert [x for x in mapping_section_elems if x["id"] == "mapper"]

        config_index = self.galaxy_interactor.get("configuration")
        config_index.raise_for_status()
        panel_views = config_index.json()["panel_views"]
        assert len(panel_views) > 1
        assert isinstance(panel_views, dict)
        edam_panel_view = panel_views["ontology:edam_merged"]
        assert edam_panel_view["view_type"] == "ontology"


class EdamToolboxDefaultIntegrationTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["edam_panel_views"] = "topics"
        config["default_panel_view"] = "ontology:edam_topics"

    def test_edam_toolbox(self):
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True))
        index.raise_for_status()
        index_as_list = index.json()
        sections = [x for x in index_as_list if x["model_class"] == "ToolSection"]
        section_names = [s["name"] for s in sections]
        assert "Mapping" in section_names
        mapping_section = [s for s in sections if s["name"] == "Mapping"][0]
        mapping_section_elems = mapping_section["elems"]
        # make sure our mapper tool was mapped using Edam correctly...
        assert [x for x in mapping_section_elems if x["id"] == "mapper"]

        config_index = self.galaxy_interactor.get("configuration")
        config_index.raise_for_status()
        panel_views = config_index.json()["panel_views"]
        assert len(panel_views) > 1
        assert isinstance(panel_views, dict)
        edam_panel_view = panel_views["ontology:edam_topics"]
        assert edam_panel_view["view_type"] == "ontology"
