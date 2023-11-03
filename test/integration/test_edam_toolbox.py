from galaxy_test.driver import integration_util


class TestEdamToolboxIntegration(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["edam_panel_views"] = "merged"

    def test_edam_toolbox(self):
        index = self.galaxy_interactor.get("tool_panels/ontology:edam_merged")
        index.raise_for_status()
        index_panel = index.json()
        sections = [x for _, x in index_panel.items() if x["model_class"] == "ToolSection"]
        section_names = [s["name"] for s in sections]
        assert "Mapping" in section_names
        mapping_section = [s for s in sections if s["name"] == "Mapping"][0]
        mapping_section_tools = mapping_section["tools"]
        # make sure our mapper tool was mapped using Edam correctly...
        assert [x for x in mapping_section_tools if x == "mapper"]

        tool_panels = self.galaxy_interactor.get("tool_panels")
        tool_panels.raise_for_status()
        panel_views = tool_panels.json()["views"]
        assert len(panel_views) > 1
        assert isinstance(panel_views, dict)
        edam_panel_view = panel_views["ontology:edam_merged"]
        assert edam_panel_view["view_type"] == "ontology"


class TestEdamToolboxDefaultIntegration(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["edam_panel_views"] = "topics"
        config["default_panel_view"] = "ontology:edam_topics"

    def test_edam_toolbox(self):
        index = self.galaxy_interactor.get("tool_panels/default_panel_view")
        index.raise_for_status()
        index_panel = index.json()
        sections = [x for _, x in index_panel.items() if x["model_class"] == "ToolSection"]
        section_names = [s["name"] for s in sections]
        assert "Mapping" in section_names
        mapping_section = [s for s in sections if s["name"] == "Mapping"][0]
        mapping_section_tools = mapping_section["tools"]
        # make sure our mapper tool was mapped using Edam correctly...
        assert [x for x in mapping_section_tools if x == "mapper"]

        tool_panels = self.galaxy_interactor.get("tool_panels")
        tool_panels.raise_for_status()
        panel_views = tool_panels.json()
        default = panel_views["default_panel_view"]
        assert default == "ontology:edam_topics"
        views = panel_views["views"]
        assert len(views) > 1
        assert isinstance(views, dict)
        edam_panel_view = views["ontology:edam_topics"]
        assert edam_panel_view["view_type"] == "ontology"
