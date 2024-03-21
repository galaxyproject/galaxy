import os
import time

from galaxy_test.driver import integration_util
from galaxy_test.driver.uses_shed import UsesShed

THIS_DIR = os.path.dirname(__file__)
PANEL_VIEWS_DIR_1 = os.path.join(THIS_DIR, "panel_views_1")


class TestPanelViewsFromDirectoryIntegration(integration_util.IntegrationTestCase):
    framework_tool_and_types = True
    allow_tool_conf_override = False

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["panel_views_dir"] = PANEL_VIEWS_DIR_1

    def test_section_copy(self):
        index = self.galaxy_interactor.get("tool_panels/filter")
        index_panel = index.json()
        sections = get_sections(index_panel)
        section_names = [s["name"] for s in sections]
        assert len(section_names) == 1
        assert "For Tours" in section_names

    def test_custom_label_order(self):
        index = self.galaxy_interactor.get("tool_panels/my-custom")
        verify_my_custom(index)

    def test_filtering_sections_by_tool_id(self):
        index = self.galaxy_interactor.get("tool_panels/custom_2")
        index.raise_for_status()
        index_panel = index.json()
        sections = get_sections(index_panel)
        assert len(sections) == 1
        section = sections[0]
        tools = section["tools"]
        assert len(tools) == 3, len(tools)

    def test_filtering_sections_by_tool_id_regex(self):
        index = self.galaxy_interactor.get("tool_panels/custom_3")
        verify_custom_regex_filtered(index)

    def test_filtering_root_by_type(self):
        index = self.galaxy_interactor.get("tool_panels/custom_4")
        index.raise_for_status()
        index_panel = index.json()
        assert len(index_panel) == 2
        # Labels are filtered out...
        assert model_classes(index_panel) == ["Tool", "Tool"]
        assert list(index_panel.keys()) == ["empty_list", "count_list"]

    def test_custom_section_def(self):
        index = self.galaxy_interactor.get("tool_panels/custom_6")
        index.raise_for_status()
        index_panel = index.json()
        assert len(index_panel) == 1
        assert model_classes(index_panel) == ["ToolSection"]
        section = list(index_panel.values())[0]
        section_elems = section["tools"]
        assert len(section_elems) == 4
        assert [section_elems[1], section_elems[3]] == ["empty_list", "count_list"]
        assert [section_elems[0]["id"], section_elems[2]["id"]] == ["the-start", "the-middle"]
        assert [section_elems[0]["model_class"], section_elems[2]["model_class"]] == [
            "ToolSectionLabel",
            "ToolSectionLabel",
        ]

    def test_section_embed(self):
        index = self.galaxy_interactor.get("tool_panels/custom_5")
        verify_custom_embed(index)

    def test_section_embed_filtering(self):
        index = self.galaxy_interactor.get("tool_panels/custom_7")
        index.raise_for_status()
        index_panel = index.json()
        assert len(index_panel) == 1
        assert model_classes(index_panel) == ["ToolSection"]
        section = list(index_panel.values())[0]
        section_elems = section["tools"]
        assert len(section_elems) == 5
        assert section_elems[0:3] == ["multi_data_optional", "paths_as_file", "param_text_option"]
        assert section_elems[4] == "Filter1"
        assert section_elems[3]["model_class"] == "ToolSectionLabel"

    def test_section_reference_by_name(self):
        index = self.galaxy_interactor.get("tool_panels/custom_8")
        verify_custom_embed(index)

    def test_section_alias(self):
        index = self.galaxy_interactor.get("tool_panels/custom_9")
        verify_custom_regex_filtered(index)

    def test_expand_section_aliases(self):
        index = self.galaxy_interactor.get("tool_panels/custom_10")
        index.raise_for_status()
        index_panel = index.json()
        assert len(index_panel) == 2
        assert model_classes(index_panel) == ["ToolSection", "ToolSection"]

    def test_global_filters(self):
        index = self.galaxy_interactor.get("tool_panels/custom_11")
        verify_custom_regex_filtered(index)

    def test_global_filters_on_integrated_panel(self):
        index = self.galaxy_interactor.get("tool_panels/custom_12")
        index.raise_for_status()
        index_panel = index.json()
        sections = get_sections(index_panel)
        assert len(sections) == 2
        assert "test" in index_panel
        section = index_panel["test"]
        assert section["id"] == "test"
        tools = section["tools"]
        assert len(tools) == 2, len(tools)

    def test_only_latest_version_in_panel(self):
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True, view="custom_13"))
        index.raise_for_status()
        index_as_list = index.json()
        sections = [x for x in index_as_list if x["model_class"] == "ToolSection"]
        assert len(sections) == 1
        section = sections[0]
        assert section["id"] == "test_section_multi"
        tools = section["elems"]
        assert len(tools) == 1, len(tools)
        assert tools[0]["version"] == "0.2"


class TestPanelViewsWithShedTools(integration_util.IntegrationTestCase, UsesShed):
    framework_tool_and_types = True
    allow_tool_conf_override = False

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["panel_views_dir"] = PANEL_VIEWS_DIR_1

    def test_only_latest_version_in_panel_fastp(self):
        FASTP_REPO = {"name": "fastp", "owner": "iuc", "tool_panel_section_id": "test_section_multi"}
        OLD_CHANGESET = "1d8fe9bc4cb0"
        NEW_CHANGESET = "dbf9c561ef29"
        self.install_repository(**FASTP_REPO, changeset=OLD_CHANGESET)
        self.install_repository(**FASTP_REPO, changeset=NEW_CHANGESET)

        # give the toolbox a moment to reload after repo installation
        time.sleep(5)
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True, view="custom_13"))
        index.raise_for_status()
        index_as_list = index.json()
        sections = [x for x in index_as_list if x["model_class"] == "ToolSection"]
        assert len(sections) == 1
        section = sections[0]
        assert section["id"] == "test_section_multi"
        tools = section["elems"]
        assert len(tools) == 2, len(tools)
        fastp = tools[0]
        assert fastp["id"] == "toolshed.g2.bx.psu.edu/repos/iuc/fastp/fastp/0.20.1+galaxy0"
        assert fastp["tool_shed_repository"]["changeset_revision"] == NEW_CHANGESET


class TestPanelViewsFromConfigIntegration(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["panel_views"] = [
            {
                "id": "my-custom",
                "name": "My Custom",
                "type": "generic",
                "items": [
                    {
                        "type": "label",
                        "text": "The Start",
                    },
                    {
                        "type": "tool",
                        "id": "empty_list",
                    },
                    {
                        "type": "label",
                        "text": "The Middle",
                    },
                    {
                        "type": "tool",
                        "id": "count_list",
                    },
                    {
                        "type": "label",
                        "text": "The End",
                    },
                ],
            }
        ]
        config["default_panel_view"] = "my-custom"

    def test_custom_label_order(self):
        index = self.galaxy_interactor.get("tool_panels/default_panel_view")
        verify_my_custom(index)


def verify_my_custom(index):
    index.raise_for_status()
    index_panel = index.json()
    sections = get_sections(index_panel)
    assert len(sections) == 0

    assert len(index_panel) == 5
    assert model_classes(index_panel) == ["ToolSectionLabel", "Tool", "ToolSectionLabel", "Tool", "ToolSectionLabel"]


def verify_custom_embed(index):
    # custom_5 / custom_8
    index.raise_for_status()
    index_panel = index.json()
    assert len(index_panel) == 1
    assert model_classes(index_panel) == ["ToolSection"]
    assert "my-new-section" in index_panel
    section = index_panel["my-new-section"]
    assert section["name"] == "My New Section"
    assert section["id"] == "my-new-section"
    section_elems = section["tools"]
    assert len(section_elems) == 5
    assert section_elems == [
        "multi_data_optional",
        "paths_as_file",
        "param_text_option",
        "column_param",
        "Filter1",
    ]


def verify_custom_regex_filtered(index):
    # custom_3 / custom_9
    index.raise_for_status()
    index_panel = index.json()
    sections = get_sections(index_panel)
    assert len(sections) == 1
    section = sections[0]
    tools = section["tools"]
    assert len(tools) == 2, len(tools)


def get_sections(index_panel):
    return [x for _, x in index_panel.items() if x["model_class"] == "ToolSection"]


def model_classes(elements):
    return [x["model_class"] for _, x in elements.items()]
