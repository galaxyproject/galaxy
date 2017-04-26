"""
"""
import logging
import os
import sys
import types
import unittest

from galaxy.web.base.pluginframework import HookPluginManager

unit_root = os.path.abspath( os.path.join( os.path.dirname( __file__ ), os.pardir, os.pardir ) )
sys.path.insert( 1, unit_root )
from unittest_utils import galaxy_mock

log = logging.getLogger( __name__ )

# ----------------------------------------------------------------------------- globals
loading_point = HookPluginManager.loading_point_filename

contents1 = """
import os

def bler( x, y=3 ):
    return ( x, y )
"""

contents2 = """
raise Exception( 'Bler' )
"""

contents3 = """
import contents1

def blah( w ):
    return tuple( [ w ] + list( contents1.bler( 2 ) ) )
"""

contents4 = """
from galaxy import util

def blah( s ):
    return util.listify( s )
"""

contents5 = """
def hook_blah( s ):
    return s.title()

def hook_filter_test( s ):
    s += ' one'
    return s
"""

contents6 = """
def hook_blah( s ):
    return s.upper()

def hook_filter_test( s ):
    s += ' two'
    return s
"""

contents7 = """
def hook_blah( s ):
    raise Exception( 'bler' )

def hook_filter_test( s ):
    raise Exception( 'bler' )
"""


# -----------------------------------------------------------------------------
class HookPluginManager_TestCase( unittest.TestCase ):

    def test_loading_point( self ):
        """should attempt load on dirs containing loading_point file"""
        mock_app_dir = galaxy_mock.MockDir({
            'plugins': {
                'plugin1': {
                    loading_point: contents1
                },
                'not_a_plugin': 'blerbler'
            }
        })
        mock_app = galaxy_mock.MockApp( root=mock_app_dir.root_path )
        plugin_mgr = HookPluginManager( mock_app, directories_setting='plugins' )

        app_path = mock_app_dir.root_path
        expected_plugins_path = os.path.join( app_path, 'plugins' )

        self.assertEqual( plugin_mgr.directories, [ expected_plugins_path ] )
        self.assertEqual( list(plugin_mgr.plugins.keys()), [ 'plugin1' ] )

        plugin = plugin_mgr.plugins[ 'plugin1' ]
        self.assertEqual( plugin.name, 'plugin1' )
        self.assertEqual( plugin.path, os.path.join( expected_plugins_path, 'plugin1' ) )
        self.assertIsInstance( plugin.module, types.ModuleType )
        self.assertEqual( plugin.module.bler( 2 ), ( 2, 3 ) )

        mock_app_dir.remove()

    def test_bad_loading_points( self ):
        """should NOT attempt load on dirs NOT containing loading_point file"""
        mock_app_dir = galaxy_mock.MockDir({
            'plugins': {
                'plugin1': {},
                'plugin2': {
                    'plogin.py': 'wot'
                }
            }
        })
        mock_app = galaxy_mock.MockApp( root=mock_app_dir.root_path )
        plugin_mgr = HookPluginManager( mock_app, directories_setting='plugins' )

        app_path = mock_app_dir.root_path
        expected_plugins_path = os.path.join( app_path, 'plugins' )

        self.assertEqual( plugin_mgr.directories, [ expected_plugins_path ] )
        self.assertEqual( list(plugin_mgr.plugins.keys()), [] )

        mock_app_dir.remove()

    def test_bad_import( self ):
        """should error gracefully (skip) on bad import"""
        mock_app_dir = galaxy_mock.MockDir({
            'plugins': {
                'plugin1': {
                    loading_point: contents2
                }
            }
        })
        mock_app = galaxy_mock.MockApp( root=mock_app_dir.root_path )
        plugin_mgr = HookPluginManager( mock_app, directories_setting='plugins' )

        app_path = mock_app_dir.root_path
        expected_plugins_path = os.path.join( app_path, 'plugins' )

        self.assertEqual( plugin_mgr.directories, [ expected_plugins_path ] )
        self.assertEqual( list(plugin_mgr.plugins.keys()), [] )

        mock_app_dir.remove()

    def test_import_w_rel_import( self ):
        """should allow loading_point to rel. import other modules"""
        mock_app_dir = galaxy_mock.MockDir({
            'plugins': {
                'plugin1': {
                    'contents1.py': contents1,
                    loading_point: contents3
                }
            }
        })
        mock_app = galaxy_mock.MockApp( root=mock_app_dir.root_path )
        plugin_mgr = HookPluginManager( mock_app, directories_setting='plugins', skip_bad_plugins=False )

        app_path = mock_app_dir.root_path
        expected_plugins_path = os.path.join( app_path, 'plugins' )

        self.assertEqual( plugin_mgr.directories, [ expected_plugins_path ] )
        self.assertEqual( list(plugin_mgr.plugins.keys()), [ 'plugin1' ] )

        plugin = plugin_mgr.plugins[ 'plugin1' ]
        self.assertEqual( plugin.name, 'plugin1' )
        self.assertEqual( plugin.path, os.path.join( expected_plugins_path, 'plugin1' ) )
        self.assertIsInstance( plugin.module, types.ModuleType )
        self.assertEqual( plugin.module.blah( 1 ), ( 1, 2, 3 ) )

        mock_app_dir.remove()

    def test_import_w_galaxy_import( self ):
        """should allow loading_point to rel. import GALAXY modules"""
        mock_app_dir = galaxy_mock.MockDir({
            'plugins': {
                'plugin1': {
                    loading_point: contents4
                }
            }
        })
        mock_app = galaxy_mock.MockApp( root=mock_app_dir.root_path )
        plugin_mgr = HookPluginManager( mock_app, directories_setting='plugins', skip_bad_plugins=False )

        app_path = mock_app_dir.root_path
        expected_plugins_path = os.path.join( app_path, 'plugins' )

        self.assertEqual( plugin_mgr.directories, [ expected_plugins_path ] )
        self.assertEqual( list(plugin_mgr.plugins.keys()), [ 'plugin1' ] )

        plugin = plugin_mgr.plugins[ 'plugin1' ]
        self.assertEqual( plugin.name, 'plugin1' )
        self.assertEqual( plugin.path, os.path.join( expected_plugins_path, 'plugin1' ) )
        self.assertIsInstance( plugin.module, types.ModuleType )

        self.assertEqual( plugin.module.blah( 'one,two' ), [ 'one', 'two' ] )

        mock_app_dir.remove()

    def test_run_hooks( self ):
        """should run hooks of loaded plugins"""
        mock_app_dir = galaxy_mock.MockDir({
            'plugins': {
                'plugin1': {
                    loading_point: contents5
                },
                'plugin2': {
                    loading_point: contents6
                }
            }
        })
        mock_app = galaxy_mock.MockApp( root=mock_app_dir.root_path )
        plugin_mgr = HookPluginManager( mock_app, directories_setting='plugins', skip_bad_plugins=False )
        self.assertEqual( sorted(plugin_mgr.plugins.keys()), [ 'plugin1', 'plugin2' ] )

        return_val_dict = plugin_mgr.run_hook( 'blah', 'one two check' )
        self.assertEqual( return_val_dict, { 'plugin1': 'One Two Check', 'plugin2': 'ONE TWO CHECK' } )

        result = plugin_mgr.filter_hook( 'filter_test', 'check' )
        self.assertEqual( result, 'check one two' )

        mock_app_dir.remove()

    def test_hook_errs( self ):
        """should fail gracefully if hook fails (and continue with other plugins)"""
        mock_app_dir = galaxy_mock.MockDir({
            'plugins': {
                'plugin1': {
                    loading_point: contents5
                },
                'plugin2': {
                    loading_point: contents6
                },
                'plugin3': {
                    loading_point: contents7
                }
            }
        })
        mock_app = galaxy_mock.MockApp( root=mock_app_dir.root_path )
        plugin_mgr = HookPluginManager( mock_app, directories_setting='plugins', skip_bad_plugins=False )
        self.assertEqual( sorted(plugin_mgr.plugins.keys()), [ 'plugin1', 'plugin2', 'plugin3' ] )

        return_val_dict = plugin_mgr.run_hook( 'blah', 'one two check' )
        self.assertEqual( return_val_dict, { 'plugin1': 'One Two Check', 'plugin2': 'ONE TWO CHECK' } )

        result = plugin_mgr.filter_hook( 'filter_test', 'check' )
        self.assertEqual( result, 'check one two' )

        mock_app_dir.remove()


if __name__ == '__main__':
    unittest.main()
