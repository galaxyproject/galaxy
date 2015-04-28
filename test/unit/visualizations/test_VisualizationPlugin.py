"""
"""
import os
import imp
import unittest

test_utils = imp.load_source( 'test_utils',
    os.path.join( os.path.dirname( __file__), '..', 'unittest_utils', 'utility.py' ) )
import galaxy_mock

from galaxy.visualization.plugins import plugin as vis_plugin
from galaxy.visualization.plugins import resource_parser

# -----------------------------------------------------------------------------
glx_dir = test_utils.get_galaxy_root()
template_cache_dir = os.path.join( glx_dir, 'database', 'compiled_templates' )
addtional_templates_dir = os.path.join( glx_dir, 'config', 'plugins', 'visualizations', 'common', 'templates' )
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
class VisualizationsPlugin_TestCase( unittest.TestCase ):

    def test_default_init( self ):
        """
        """
        vis_dir = galaxy_mock.MockDir({
            'config' : {
                'vis1.xml' : ''
            },
            'static'    : {},
            'templates' : {},
        })
        config = dict()
        plugin = vis_plugin.VisualizationPlugin( galaxy_mock.MockApp(), vis_dir.root_path,
            'myvis', config )
        self.assertEqual( plugin.name, 'myvis' )
        self.assertEqual( plugin.path, vis_dir.root_path )
        self.assertEqual( plugin.config, {} )
        self.assertEqual( plugin.base_url, 'myvis' )
        # static
        self.assertTrue( plugin.serves_static )
        self.assertEqual( plugin.static_path, vis_dir.root_path + '/static' )
        self.assertEqual( plugin.static_url, 'myvis/static' )
        # template
        self.assertTrue( plugin.serves_templates )
        self.assertEqual( plugin.template_path, vis_dir.root_path + '/templates' )
        self.assertEqual( plugin.template_lookup.__class__.__name__, 'TemplateLookup' )
        # resource parser
        self.assertIsInstance( plugin.resource_parser, resource_parser.ResourceParser )

    def test_init_with_context( self ):
        """
        """
        vis_dir = galaxy_mock.MockDir({
            'config' : {
                'vis1.xml' : ''
            },
            'static'    : {},
            'templates' : {},
        })
        config = dict()
        context = dict(
            base_url='u/wot/m8',
            template_cache_dir='template_cache',
            additional_template_paths=[ 'one' ]
        )
        plugin = vis_plugin.VisualizationPlugin( galaxy_mock.MockApp(), vis_dir.root_path,
            'myvis', config, context=context )
        self.assertEqual( plugin.base_url, 'u/wot/m8/myvis' )
        # static
        self.assertEqual( plugin.static_url, 'u/wot/m8/myvis/static' )
        # template
        self.assertEqual( plugin.template_lookup.__class__.__name__, 'TemplateLookup' )

    def test_init_without_static_or_templates( self ):
        """
        """
        vis_dir = galaxy_mock.MockDir({
            'config' : {
                'vis1.xml' : ''
            }
        })
        plugin = vis_plugin.VisualizationPlugin( galaxy_mock.MockApp(), vis_dir.root_path,
            'myvis', dict() )
        self.assertFalse( plugin.serves_static )
        self.assertFalse( plugin.serves_templates )
        # not sure what this would do, but...

# -----------------------------------------------------------------------------
# TODO: config parser tests (in separate file)

if __name__ == '__main__':
    unittest.main()
