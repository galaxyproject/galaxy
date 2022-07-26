import os

from galaxy_test.driver import integration_util

THIS_DIR = os.path.dirname(__file__)
PANEL_VIEWS_DIR_1 = os.path.join(THIS_DIR, "panel_views_1")


class PanelViewsFromDirectoryIntegrationTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True
    allow_tool_conf_override = False

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["panel_views_dir"] = PANEL_VIEWS_DIR_1

    def test_section_copy(self):
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True, view="filter"))
        index_as_list = index.json()
        sections = [x for x in index_as_list if x["model_class"] == "ToolSection"]
        section_names = [s["name"] for s in sections]
        assert len(section_names) == 1
        assert "For Tours" in section_names

    def test_custom_label_order(self):
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True, view="my-custom"))
        verify_my_custom(index)

    def test_filtering_sections_by_tool_id(self):
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True, view="custom_2"))
        index.raise_for_status()
        index_as_list = index.json()
        sections = [x for x in index_as_list if x["model_class"] == "ToolSection"]
        assert len(sections) == 1
        section = sections[0]
        tools = section["elems"]
        assert len(tools) == 3, len(tools)

    def test_filtering_sections_by_tool_id_regex(self):
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True, view="custom_3"))
        verify_custom_regex_filtered(index)

    def test_filtering_root_by_type(self):
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True, view="custom_4"))
        index.raise_for_status()
        index_as_list = index.json()
        assert len(index_as_list) == 2
        # Labels are filtered out...
        assert model_classes(index_as_list) == ["Tool", "Tool"]
        assert element_ids(index_as_list) == ["empty_list", "count_list"]

    def test_custom_section_def(self):
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True, view="custom_6"))
        index.raise_for_status()
        index_as_list = index.json()
        assert len(index_as_list) == 1
        assert model_classes(index_as_list) == ["ToolSection"]
        section = index_as_list[0]
        section_elems = section["elems"]
        assert len(section_elems) == 4, model_classes(section_elems)
        assert model_classes(section_elems) == ["ToolSectionLabel", "Tool", "ToolSectionLabel", "Tool"]
        assert element_ids(section_elems) == ["the-start", "empty_list", "the-middle", "count_list"]

    def test_section_embed(self):
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True, view="custom_5"))
        verify_custom_embed(index)

    def test_section_embed_filtering(self):
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True, view="custom_7"))
        index.raise_for_status()
        index_as_list = index.json()
        assert len(index_as_list) == 1
        assert model_classes(index_as_list) == ["ToolSection"]
        section = index_as_list[0]
        section_elems = section["elems"]
        assert len(section_elems) == 5, model_classes(section_elems)
        assert model_classes(section_elems) == ["Tool", "Tool", "Tool", "ToolSectionLabel", "Tool"]
        elem_ids = element_ids(section_elems)
        assert elem_ids[0:3] == ["multi_data_optional", "paths_as_file", "param_text_option"]
        assert elem_ids[4] == "Filter1"

    def test_section_reference_by_name(self):
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True, view="custom_8"))
        verify_custom_embed(index)

    def test_section_alias(self):
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True, view="custom_9"))
        verify_custom_regex_filtered(index)

    def test_expand_section_aliases(self):
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True, view="custom_10"))
        index.raise_for_status()
        index_as_list = index.json()
        assert len(index_as_list) == 2
        assert model_classes(index_as_list) == ["ToolSection", "ToolSection"]

    def test_global_filters(self):
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True, view="custom_11"))
        verify_custom_regex_filtered(index)

    def test_global_filters_on_integrated_panel(self):
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True, view="custom_12"))
        index.raise_for_status()
        index_as_list = index.json()
        sections = [x for x in index_as_list if x["model_class"] == "ToolSection"]
        assert len(sections) == 2
        section = sections[0]
        assert section["id"] == "test"
        tools = section["elems"]
        assert len(tools) == 2, len(tools)


class PanelViewsFromConfigIntegrationTestCase(integration_util.IntegrationTestCase):

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
        index = self.galaxy_interactor.get("tools", data=dict(in_panel=True))
        verify_my_custom(index)


def verify_my_custom(index):
    index.raise_for_status()
    index_as_list = index.json()
    sections = [x for x in index_as_list if x["model_class"] == "ToolSection"]
    assert len(sections) == 0

    assert len(index_as_list) == 5
    assert model_classes(index_as_list) == ["ToolSectionLabel", "Tool", "ToolSectionLabel", "Tool", "ToolSectionLabel"]


def verify_custom_embed(index):
    # custom_5 / custom_8
    index.raise_for_status()
    index_as_list = index.json()
    assert len(index_as_list) == 1
    assert model_classes(index_as_list) == ["ToolSection"]
    section = index_as_list[0]
    assert section["name"] == "My New Section"
    assert section["id"] == "my-new-section"
    section_elems = section["elems"]
    assert len(section_elems) == 5, model_classes(section_elems)
    assert model_classes(section_elems) == ["Tool", "Tool", "Tool", "Tool", "Tool"]
    assert element_ids(section_elems) == [
        "multi_data_optional",
        "paths_as_file",
        "param_text_option",
        "column_param",
        "Filter1",
    ]


def verify_custom_regex_filtered(index):
    # custom_3 / custom_9
    index.raise_for_status()
    index_as_list = index.json()
    sections = [x for x in index_as_list if x["model_class"] == "ToolSection"]
    assert len(sections) == 1
    section = sections[0]
    tools = section["elems"]
    assert len(tools) == 2, len(tools)


def element_ids(elements):
    return [x["id"] for x in elements]


def model_classes(elements):
    return [x["model_class"] for x in elements]
