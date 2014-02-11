"""
"""
import os
import imp
import unittest

utility = imp.load_source( 'utility', os.path.join( os.path.dirname( __file__ ), '../../util/utility.py' ) )
log = utility.set_up_filelogger( __name__ + '.log' )
utility.add_galaxy_lib_to_path( 'test/unit/web/base' )

from galaxy.web.base.pluginframework import PageServingPluginManager

import mock

# ----------------------------------------------------------------------------- globals
contents1 = """${what} ${you} ${say}"""

# -----------------------------------------------------------------------------
class PageServingPluginManager_TestCase( unittest.TestCase ):

    def test_plugin_load( self ):
        """should attempt load if criteria met"""
        mock_app_dir = mock.MockDir({
            'plugins'   : {
                'plugin1'   : {
                    'templates' : {},
                    'static'    : {}
                },
                'plugin2'   : {
                    'static'    : {}
                },
                'plugin3'   : {
                    'templates' : {}
                },
                'not_a_plugin1'     : 'blerbler',
                'not_a_plugin2'     : {},
            }
        })
        mock_app = mock.MockApp( mock_app_dir.root_path )
        plugin_mgr = PageServingPluginManager( mock_app, 'test', directories_setting='plugins' )

        app_path = mock_app_dir.root_path
        expected_plugins_path = os.path.join( app_path, 'plugins' )

        self.assertEqual( plugin_mgr.base_url, 'test' )
        self.assertItemsEqual( plugin_mgr.directories, [ expected_plugins_path ] )
        self.assertItemsEqual( plugin_mgr.plugins.keys(), [ 'plugin1', 'plugin2', 'plugin3' ] )

        plugin1 = plugin_mgr.plugins[ 'plugin1' ]
        self.assertEqual( plugin1.name, 'plugin1' )
        self.assertEqual( plugin1.path, os.path.join( expected_plugins_path, 'plugin1' ) )
        self.assertEqual( plugin1.base_url, '/'.join([ plugin_mgr.base_url, plugin1.name ]) )
        self.assertTrue( plugin1.serves_static )
        self.assertEqual( plugin1.static_path, os.path.join( plugin1.path, 'static' ) )
        self.assertEqual( plugin1.static_url, '/'.join([ plugin1.base_url, 'static' ]) )
        self.assertTrue( plugin1.serves_templates )
        self.assertEqual( plugin1.template_path, os.path.join( plugin1.path, 'templates' ) )
        self.assertEqual( plugin1.template_lookup.__class__.__name__, 'TemplateLookup' )

        plugin2 = plugin_mgr.plugins[ 'plugin2' ]
        self.assertEqual( plugin2.name, 'plugin2' )
        self.assertEqual( plugin2.path, os.path.join( expected_plugins_path, 'plugin2' ) )
        self.assertEqual( plugin2.base_url, '/'.join([ plugin_mgr.base_url, plugin2.name ]) )
        self.assertTrue( plugin2.serves_static )
        self.assertEqual( plugin2.static_path, os.path.join( plugin2.path, 'static' ) )
        self.assertEqual( plugin2.static_url, '/'.join([ plugin2.base_url, 'static' ]) )
        self.assertFalse( plugin2.serves_templates )

        plugin3 = plugin_mgr.plugins[ 'plugin3' ]
        self.assertEqual( plugin3.name, 'plugin3' )
        self.assertEqual( plugin3.path, os.path.join( expected_plugins_path, 'plugin3' ) )
        self.assertEqual( plugin3.base_url, '/'.join([ plugin_mgr.base_url, plugin3.name ]) )
        self.assertFalse( plugin3.serves_static )
        self.assertTrue( plugin3.serves_templates )
        self.assertEqual( plugin1.template_path, os.path.join( plugin1.path, 'templates' ) )
        self.assertEqual( plugin1.template_lookup.__class__.__name__, 'TemplateLookup' )

        mock_app_dir.remove()

    def test_plugin_static_map( self ):
        """"""
        mock_app_dir = mock.MockDir({
            'plugins'   : {
                'plugin1'   : {
                    'templates' : {},
                    'static'    : {}
                }
            }
        })
        mock_app = mock.MockApp( mock_app_dir.root_path )
        plugin_mgr = PageServingPluginManager( mock_app, 'test', directories_setting='plugins' )

        app_path = mock_app_dir.root_path
        expected_plugins_path = os.path.join( app_path, 'plugins' )
        self.assertItemsEqual( plugin_mgr.plugins.keys(), [ 'plugin1' ] )
        plugin = plugin_mgr.plugins[ 'plugin1' ]
        self.assertEqual( plugin_mgr.get_static_urls_and_paths(), [( plugin.static_url, plugin.static_path )] )

        mock_app_dir.remove()

    def test_plugin_templates( self ):
        """"""
        mock_app_dir = mock.MockDir({
            'plugins'   : {
                'plugin1'   : {
                    'templates' : {
                        'test.mako' : contents1
                    },
                }
            }
        })
        mock_app = mock.MockApp( mock_app_dir.root_path )
        plugin_mgr = PageServingPluginManager( mock_app, 'test', directories_setting='plugins' )

        app_path = mock_app_dir.root_path
        expected_plugins_path = os.path.join( app_path, 'plugins' )
        self.assertItemsEqual( plugin_mgr.plugins.keys(), [ 'plugin1' ] )

        plugin = plugin_mgr.plugins[ 'plugin1' ]
        rendered = plugin_mgr.fill_template( mock.MockTrans(), plugin, 'test.mako',
            what='Hey', you='Ho', say='HeyHey HoHo' )
        self.assertEqual( rendered, 'Hey Ho HeyHey HoHo' )

        mock_app_dir.remove()


if __name__ == '__main__':
    unittest.main()
