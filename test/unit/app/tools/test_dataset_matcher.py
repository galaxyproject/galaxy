from unittest import TestCase

from galaxy import model
from galaxy.app_unittest_utils.tools_support import UsesApp
from galaxy.tools.parameters import (
    basic,
    dataset_matcher,
)
from galaxy.util import (
    bunch,
    XML,
)
from .test_data_parameters import MockHistoryDatasetAssociation


class MockTool:
    def __init__(self, app):
        self.app = app
        self.tool_type = "default"
        self.valid_input_states = model.Dataset.valid_input_states


class DatasetMatcherTestCase(TestCase, UsesApp):
    def test_hda_mismatches(self):
        # Datasets not visible are not "valid" for param.
        self.mock_hda.visible = False
        assert not self.test_context.hda_match(self.mock_hda)

        # Datasets that don't match datatype are not valid.
        self.mock_hda.visible = True
        self.mock_hda.extension = "data"
        self.mock_hda.conversion_destination = (False, None, None)
        assert not self.test_context.hda_match(self.mock_hda)

    def test_valid_hda_direct_match(self):
        # Datasets that visible and matching are valid
        self.mock_hda.visible = True
        self.mock_hda.extension = "txt"
        hda_match = self.test_context.hda_match(self.mock_hda, check_implicit_conversions=False)
        assert hda_match

        # Match is not a conversion and so matching hda is the same hda
        # supplied.
        assert not hda_match.implicit_conversion
        assert hda_match.hda == self.mock_hda

    def test_valid_hda_implicit_convered(self):
        # Find conversion returns an HDA to an already implicitly converted
        # dataset.
        self.mock_hda.extension = "data"
        converted_hda = model.HistoryDatasetAssociation()
        self.mock_hda.conversion_destination = (False, "tabular", converted_hda)
        hda_match = self.test_context.hda_match(self.mock_hda)

        assert hda_match
        assert hda_match.implicit_conversion
        assert hda_match.hda == converted_hda
        assert hda_match.target_ext == "tabular"

    def test_hda_match_implicit_can_convert(self):
        # Find conversion returns a target extension to convert to, but not
        # a previously implicitly converted dataset.
        self.mock_hda.extension = "data"
        self.mock_hda.conversion_destination = (False, "tabular", None)
        hda_match = self.test_context.hda_match(self.mock_hda)

        assert hda_match
        assert hda_match.implicit_conversion
        assert hda_match.hda == self.mock_hda
        assert hda_match.target_ext == "tabular"

    def test_hda_match_properly_skips_conversion(self):
        self.mock_hda.extension = "data"
        self.mock_hda.conversion_destination = (False, "tabular", bunch.Bunch())
        hda_match = self.test_context.hda_match(self.mock_hda, check_implicit_conversions=False)
        assert not hda_match

    def test_data_destination_tools_require_public(self):
        self.tool.tool_type = "data_destination"

        # Public datasets okay and valid
        self.app.security_agent.dataset_is_public = lambda dataset: True
        hda_match = self.test_context.hda_match(self.mock_hda)
        assert hda_match

        # Non-public datasets not valid
        self.app.security_agent.dataset_is_public = lambda dataset: False
        hda_match = self.test_context.hda_match(self.mock_hda)
        assert not hda_match

    def test_filtered_hda_matched_key(self):
        self.filtered_param = True
        data1_val = model.HistoryDatasetAssociation()
        data1_val.dbkey = "hg18"
        self.other_values = {"data1": data1_val}
        assert self.test_context.filter_values == {"hg18"}

        # mock_hda is hg19, other is hg18 so should not be "valid hda"
        hda_match = self.test_context.hda_match(self.mock_hda)
        assert not hda_match

    def test_filtered_hda_unmatched_key(self):
        self.filtered_param = True
        data1_val = model.HistoryDatasetAssociation()
        data1_val.dbkey = "hg19"
        self.other_values = {"data1": data1_val}

        # Other param value and this dataset both hg19, should be valid
        hda_match = self.test_context.hda_match(self.mock_hda)
        assert hda_match

    def test_metadata_filtered_hda_options_filter_attribute_matched_keys(self):
        self.metadata_filtered_param = True
        data1_val = model.HistoryDatasetAssociation()
        self.other_values = {"data1": data1_val}

        hda1 = MockHistoryDatasetAssociation()
        hda1.metadata = MockMetadata()
        hda1.metadata.foo = "bar"
        hda2 = MockHistoryDatasetAssociation()
        hda2.metadata = MockMetadata()
        hda2.metadata.foo = "baz"

        assert self.test_context.filter_values == {"baz", "bar"}

        hda_match = self.test_context.hda_match(hda1)
        assert hda_match

        hda_match = self.test_context.hda_match(hda2)
        assert hda_match

    def test_metadata_filtered_hda_options_filter_attribute_unmatched_key(self):
        self.metadata_filtered_param = True
        data1_val = model.HistoryDatasetAssociation()
        self.other_values = {"data1": data1_val}

        hda = MockHistoryDatasetAssociation()
        hda.metadata = MockMetadata()
        hda.metadata.foo = "no-match"

        assert self.test_context.filter_values == {"baz", "bar"}

        hda_match = self.test_context.hda_match(hda)
        assert not hda_match

    def setUp(self):
        self.setup_app()
        self.mock_hda = MockHistoryDatasetAssociation()
        self.tool = MockTool(self.app)
        self.current_user_roles = []
        self.other_values = {}

        # Reset lazily generated stuff
        self.filtered_param = False
        self.metadata_filtered_param = False
        self._test_context = None
        self.param = None

    @property
    def test_context(self):
        if self._test_context is None:
            option_xml = ""
            if self.filtered_param:
                option_xml = """<options><filter type="data_meta" ref="data1" key="dbkey" /></options>"""
            if self.metadata_filtered_param:
                option_xml = """
                    <options options_filter_attribute="metadata.foo">
                      <filter type="add_value" value="bar" />
                      <filter type="add_value" value="baz" />
                    </options>"""
            param_xml = XML("""<param name="data2" type="data" format="txt">%s</param>""" % option_xml)
            self.param = basic.DataToolParameter(
                self.tool,
                param_xml,
            )
            trans = bunch.Bunch(
                app=self.app,
                get_current_user_roles=lambda: self.current_user_roles,
                workflow_building_mode=True,
            )
            self._test_context = dataset_matcher.get_dataset_matcher_factory(trans).dataset_matcher(
                param=self.param, other_values=self.other_values
            )

        return self._test_context


class MockMetadata:
    def __init__(self):
        self.foo = None
