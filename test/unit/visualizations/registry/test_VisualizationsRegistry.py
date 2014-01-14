"""
"""
import os
import imp
import unittest

utility = imp.load_source( 'utility', os.path.join( os.path.dirname( __file__ ), '../../util/utility.py' ) )
log = utility.set_up_filelogger( __name__ + '.log' )

relative_test_path = '/test/unit/visualizations/registry'
utility.add_galaxy_lib_to_path( relative_test_path )

from galaxy.visualization.registry import VisualizationsRegistry

base_mock = imp.load_source( 'mock',  os.path.join( os.path.dirname( __file__ ), '../../web/base/mock.py' ) )

# ----------------------------------------------------------------------------- globals
glx_dir = os.getcwd().replace( relative_test_path, '' )
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

# -----------------------------------------------------------------------------
class VisualizationsRegistry_TestCase( unittest.TestCase ):

    # ------------------------------------------------------------------------- vis plugin discovery
    def test_plugin_load_from_repo( self ):
        """should attempt load if criteria met"""
        mock_app = base_mock.MockApp( glx_dir )
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
        mock_app_dir = base_mock.MockDir({
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
        mock_app = base_mock.MockApp( mock_app_dir.root_path )
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


#TODO: config parser tests (in separate file)

if __name__ == '__main__':
    unittest.main()
