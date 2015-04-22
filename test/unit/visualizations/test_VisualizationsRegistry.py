"""
"""
import os
import imp
import unittest
import re

test_utils = imp.load_source( 'test_utils',
    os.path.join( os.path.dirname( __file__), '../unittest_utils/utility.py' ) )
import galaxy_mock

from galaxy import model
from galaxy.visualization.plugins.registry import VisualizationsRegistry

# -----------------------------------------------------------------------------
glx_dir = test_utils.get_galaxy_root()
template_cache_dir = os.path.join( glx_dir, 'database', 'compiled_templates' )
vis_reg_path = 'config/plugins/visualizations'

config1 = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE visualization SYSTEM "../../visualization.dtd">
<visualization name="scatterplot">
    <data_sources>
        <data_source>
            <model_class>HistoryDatasetAssociation</model_class>
            <test type="isinstance" test_attr="datatype" result_type="datatype">tabular.Tabular</test>
            <to_param param_attr="id">dataset_id</to_param>
        </data_source>
    </data_sources>
    <params>
        <param type="dataset" var_name_in_template="hda" required="true">dataset_id</param>
    </params>
    <template>scatterplot.mako</template>
</visualization>
"""

ipython_config = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE interactive_environment SYSTEM "../../interactive_environments.dtd">
<interactive_environment name="IPython">
    <data_sources>
        <data_source>
            <model_class>HistoryDatasetAssociation</model_class>
            <test type="isinstance" test_attr="datatype" result_type="datatype">tabular.Tabular</test>
            <test type="isinstance" test_attr="datatype" result_type="datatype">data.Text</test>
            <to_param param_attr="id">dataset_id</to_param>
        </data_source>
    </data_sources>
    <params>
        <param type="dataset" var_name_in_template="hda" required="true">dataset_id</param>
    </params>
    <template>ipython.mako</template>
</interactive_environment>
"""
ipython_template = """\
${ ie_request }-${ get_api_key() }
"""


# -----------------------------------------------------------------------------
class VisualizationsRegistry_TestCase( unittest.TestCase ):

    # ------------------------------------------------------------------------- vis plugin discovery
    def test_plugin_load_from_repo( self ):
        """should attempt load if criteria met"""
        mock_app = galaxy_mock.MockApp( root=glx_dir )
        plugin_mgr = VisualizationsRegistry( mock_app,
            directories_setting=vis_reg_path,
            template_cache_dir=template_cache_dir )

        expected_plugins_path = os.path.join( glx_dir, vis_reg_path )
        self.assertEqual( plugin_mgr.base_url, 'visualizations' )
        self.assertItemsEqual( plugin_mgr.directories, [ expected_plugins_path ] )

        scatterplot = plugin_mgr.plugins[ 'scatterplot' ]
        self.assertEqual( scatterplot.name, 'scatterplot' )
        self.assertEqual( scatterplot.path, os.path.join( expected_plugins_path, 'scatterplot' ) )
        self.assertEqual( scatterplot.base_url, '/'.join([ plugin_mgr.base_url, scatterplot.name ]) )
        self.assertTrue(  scatterplot.serves_static )
        self.assertEqual( scatterplot.static_path, os.path.join( scatterplot.path, 'static' ) )
        self.assertEqual( scatterplot.static_url, '/'.join([ scatterplot.base_url, 'static' ]) )
        self.assertTrue(  scatterplot.serves_templates )
        self.assertEqual( scatterplot.template_path, os.path.join( scatterplot.path, 'templates' ) )
        self.assertEqual( scatterplot.template_lookup.__class__.__name__, 'TemplateLookup' )

        trackster = plugin_mgr.plugins[ 'trackster' ]
        self.assertEqual( trackster.name, 'trackster' )
        self.assertEqual( trackster.path, os.path.join( expected_plugins_path, 'trackster' ) )
        self.assertEqual( trackster.base_url, '/'.join([ plugin_mgr.base_url, trackster.name ]) )
        self.assertFalse( trackster.serves_static )
        self.assertFalse( trackster.serves_templates )

    def test_plugin_load( self ):
        """"""
        mock_app_dir = galaxy_mock.MockDir({
            'plugins'   : {
                'vis1'          : {
                    'config' : {
                        'vis1.xml' : config1
                    },
                    'static'    : {},
                    'templates' : {},
                },
                'vis2'          : {
                    'config' : {
                        'vis2.xml' : config1
                    }
                },
                'not_a_vis1'    : {
                    'config' : {
                        'vis1.xml' : 'blerbler'
                    },
                },
                'not_a_vis1'    : {
                    # no config
                    'static'    : {},
                    'templates' : {},
                },
                # empty
                'not_a_vis2'    : {},
                'not_a_vis3'    : 'blerbler',
                # bad config
                'not_a_vis4'          : {
                    'config' : {
                        'not_a_vis4.xml' : 'blerbler'
                    }
                },
            }
        })
        mock_app = galaxy_mock.MockApp( root=mock_app_dir.root_path )
        plugin_mgr = VisualizationsRegistry( mock_app,
            directories_setting='plugins',
            template_cache_dir='bler' )

        expected_plugins_path = os.path.join( mock_app_dir.root_path, 'plugins' )
        expected_plugin_names = [ 'vis1', 'vis2' ]

        self.assertEqual( plugin_mgr.base_url, 'visualizations' )
        self.assertItemsEqual( plugin_mgr.directories, [ expected_plugins_path ] )
        self.assertItemsEqual( plugin_mgr.plugins.keys(), expected_plugin_names )

        vis1 = plugin_mgr.plugins[ 'vis1' ]
        self.assertEqual( vis1.name, 'vis1' )
        self.assertEqual( vis1.path, os.path.join( expected_plugins_path, 'vis1' ) )
        self.assertEqual( vis1.base_url, '/'.join([ plugin_mgr.base_url, vis1.name ]) )
        self.assertTrue(  vis1.serves_static )
        self.assertEqual( vis1.static_path, os.path.join( vis1.path, 'static' ) )
        self.assertEqual( vis1.static_url, '/'.join([ vis1.base_url, 'static' ]) )
        self.assertTrue(  vis1.serves_templates )
        self.assertEqual( vis1.template_path, os.path.join( vis1.path, 'templates' ) )
        self.assertEqual( vis1.template_lookup.__class__.__name__, 'TemplateLookup' )

        vis2 = plugin_mgr.plugins[ 'vis2' ]
        self.assertEqual( vis2.name, 'vis2' )
        self.assertEqual( vis2.path, os.path.join( expected_plugins_path, 'vis2' ) )
        self.assertEqual( vis2.base_url, '/'.join([ plugin_mgr.base_url, vis2.name ]) )
        self.assertFalse( vis2.serves_static )
        self.assertFalse( vis2.serves_templates )

        mock_app_dir.remove()

    def test_interactive_environ_plugin_load( self ):
        """
        """
        mock_app_dir = galaxy_mock.MockDir({
            'plugins'   : {
                'ipython' : {
                    'config' : {
                        'ipython.xml' : ipython_config
                    },
                    'templates' : {
                        'ipython.mako': ipython_template
                    }
                },
            }
        })
        mock_app = galaxy_mock.MockApp( root=mock_app_dir.root_path )
        plugin_mgr = VisualizationsRegistry( mock_app,
            directories_setting='plugins',
            template_cache_dir=mock_app_dir.root_path )

        expected_plugins_path = os.path.join( mock_app_dir.root_path, 'plugins' )
        expected_plugin_names = [ 'ipython' ]

        self.assertEqual( plugin_mgr.base_url, 'visualizations' )
        self.assertItemsEqual( plugin_mgr.directories, [ expected_plugins_path ] )
        self.assertItemsEqual( plugin_mgr.plugins.keys(), expected_plugin_names )

        ipython = plugin_mgr.plugins[ 'ipython' ]
        config = ipython.config

        self.assertEqual( ipython.name, 'ipython' )
        self.assertEqual( config.get( 'plugin_type' ), 'interactive_environment' )

        # get_api_key needs a user, fill_template a trans
        user = model.User( email="blah@bler.blah", password="dockerDockerDOCKER" )
        trans = galaxy_mock.MockTrans( user=user )
        # use a mock request factory - this will be written into the filled template to show it was used
        ipython.INTENV_REQUEST_FACTORY = lambda t, p: 'mock'
        # should return the (new) api key for the above user (see the template above)
        response = ipython._fill_template( trans )
        response.strip()
        self.assertIsInstance( response, basestring )
        self.assertTrue( '-' in response )
        ie_request, api_key = response.split( '-' )

        self.assertEqual( ie_request, 'mock' )

        match = re.match( r'[a-f0-9]{32}', api_key )
        self.assertIsNotNone( match )
        self.assertEqual( match.span(), ( 0, 32 ) )

        mock_app_dir.remove()


# TODO: config parser tests (in separate file)

if __name__ == '__main__':
    unittest.main()
