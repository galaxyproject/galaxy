from unittest import TestCase

from galaxy import model
from galaxy.util import bunch
from galaxy.tools.parameters import basic
from galaxy.tools.parameters import dataset_matcher

from elementtree.ElementTree import XML

import tools_support
from .test_data_parameters import MockHistoryDatasetAssociation


class DatasetMatcherTestCase( TestCase, tools_support.UsesApp ):

    def test_hda_accessible( self ):
        # Cannot access errored or discard datasets.
        self.mock_hda.dataset.state = model.Dataset.states.ERROR
        assert not self.test_context.hda_accessible( self.mock_hda )

        self.mock_hda.dataset.state = model.Dataset.states.DISCARDED
        assert not self.test_context.hda_accessible( self.mock_hda )

        # Can access datasets in other states.
        self.mock_hda.dataset.state = model.Dataset.states.OK
        assert self.test_context.hda_accessible( self.mock_hda )

        self.mock_hda.dataset.state = model.Dataset.states.QUEUED
        assert self.test_context.hda_accessible( self.mock_hda )

        # Cannot access dataset if security agent says no.
        self.app.security_agent.can_access_dataset = lambda roles, dataset: False
        assert not self.test_context.hda_accessible( self.mock_hda )

    def test_selected( self ):
        self.test_context.value = []
        assert not self.test_context.selected( self.mock_hda )

        self.test_context.value = [ self.mock_hda ]
        assert self.test_context.selected( self.mock_hda )

    def test_hda_mismatches( self ):
        # Datasets not visible are not "valid" for param.
        self.mock_hda.visible = False
        assert not self.test_context.hda_match( self.mock_hda )

        # Datasets that don't match datatype are not valid.
        self.mock_hda.visible = True
        self.mock_hda.datatype_matches = False
        assert not self.test_context.hda_match( self.mock_hda )

    def test_valid_hda_direct_match( self ):
        # Datasets that visible and matching are valid
        self.mock_hda.visible = True
        self.mock_hda.datatype_matches = True
        hda_match = self.test_context.hda_match( self.mock_hda, check_implicit_conversions=False )
        assert hda_match

        # Match is not a conversion and so matching hda is the same hda
        # supplied.
        assert not hda_match.implicit_conversion
        assert hda_match.hda == self.mock_hda

    def test_valid_hda_implicit_convered( self ):
        # Find conversion returns an HDA to an already implicitly converted
        # dataset.
        self.mock_hda.datatype_matches = False
        converted_hda = model.HistoryDatasetAssociation()
        self.mock_hda.conversion_destination = ( "tabular", converted_hda )
        hda_match = self.test_context.hda_match( self.mock_hda )

        assert hda_match
        assert hda_match.implicit_conversion
        assert hda_match.hda == converted_hda
        assert hda_match.target_ext == "tabular"

    def test_hda_match_implicit_can_convert( self ):
        # Find conversion returns a target extension to convert to, but not
        # a previously implicitly converted dataset.
        self.mock_hda.datatype_matches = False
        self.mock_hda.conversion_destination = ( "tabular", None )
        hda_match = self.test_context.hda_match( self.mock_hda )

        assert hda_match
        assert hda_match.implicit_conversion
        assert hda_match.hda == self.mock_hda
        assert hda_match.target_ext == "tabular"

    def test_hda_match_properly_skips_conversion( self ):
        self.mock_hda.datatype_matches = False
        self.mock_hda.conversion_destination = ( "tabular", bunch.Bunch() )
        hda_match = self.test_context.hda_match( self.mock_hda, check_implicit_conversions=False )
        assert not hda_match

    def test_data_destination_tools_require_public( self ):
        self.tool.tool_type = "data_destination"

        # Public datasets okay and valid
        self.app.security_agent.dataset_is_public = lambda dataset: True
        hda_match = self.test_context.hda_match( self.mock_hda )
        assert hda_match

        # Non-public datasets not valid
        self.app.security_agent.dataset_is_public = lambda dataset: False
        hda_match = self.test_context.hda_match( self.mock_hda )
        assert not hda_match

    def test_filtered_hda_matched_key( self ):
        self.filtered_param = True
        data1_val = model.HistoryDatasetAssociation()
        data1_val.dbkey = "hg18"
        self.other_values = { "data1": data1_val }
        assert self.test_context.filter_value == "hg18"

        # mock_hda is hg19, other is hg18 so should not be "valid hda"
        hda_match = self.test_context.hda_match( self.mock_hda )
        assert not hda_match

    def test_filtered_hda_unmatched_key( self ):
        self.filtered_param = True
        data1_val = model.HistoryDatasetAssociation()
        data1_val.dbkey = "hg19"
        self.other_values = { "data1": data1_val }

        # Other param value and this dataset both hg19, should be valid
        hda_match = self.test_context.hda_match( self.mock_hda )
        assert hda_match

    def setUp( self ):
        self.setup_app()
        self.mock_hda = MockHistoryDatasetAssociation()
        self.tool = bunch.Bunch(
            app=self.app,
            tool_type="default",
        )
        self.current_user_roles = []
        self.other_values = {}

        # Reset lazily generated stuff
        self.filtered_param = False
        self._test_context = None
        self.param = None

    @property
    def test_context( self ):
        if self._test_context is None:
            option_xml = ""
            if self.filtered_param:
                option_xml = '''<options><filter type="data_meta" ref="data1" key="dbkey" /></options>'''
            param_xml = XML( '''<param name="data2" type="data" ext="txt">%s</param>''' % option_xml )
            self.param = basic.DataToolParameter(
                tool=self.tool,
                elem=param_xml,
            )

            self._test_context = dataset_matcher.DatasetMatcher(
                trans=bunch.Bunch(
                    app=self.app,
                    get_current_user_roles=lambda: self.current_user_roles,
                    workflow_building_mode=True,
                ),
                param=self.param,
                value=[ ],
                other_values=self.other_values
            )

        return self._test_context
