"""
Unit tests for ``galaxy.web.base.pluginframework.PluginManager``
"""
import logging
import os
import sys
import unittest

from galaxy.web.base.pluginframework import PluginManager

unit_root = os.path.abspath( os.path.join( os.path.dirname( __file__ ), os.pardir, os.pardir ) )
sys.path.insert( 1, unit_root )
from unittest_utils import galaxy_mock

log = logging.getLogger( __name__ )


class PluginManager_TestCase( unittest.TestCase ):

    def test_rel_path_search( self ):
        """should be able to search given rel. path"""
        mock_app_dir = galaxy_mock.MockDir({
            'plugins': {
                'plugin1': {},
                'plugin2': {},
                'file1': 'blerbler'
            }
        })
        mock_app = galaxy_mock.MockApp( root=mock_app_dir.root_path )
        plugin_mgr = PluginManager( mock_app, directories_setting='plugins' )

        app_path = mock_app_dir.root_path
        expected_plugins_path = os.path.join( app_path, 'plugins' )

        self.assertEqual( plugin_mgr.directories, [ expected_plugins_path ] )
        self.assertEqual( sorted(plugin_mgr.plugins.keys()), [ 'plugin1', 'plugin2' ] )
        self.assertEqual( plugin_mgr.plugins[ 'plugin1' ].name, 'plugin1' )
        self.assertEqual( plugin_mgr.plugins[ 'plugin1' ].path, os.path.join( expected_plugins_path, 'plugin1' ) )
        self.assertEqual( plugin_mgr.plugins[ 'plugin2' ].name, 'plugin2' )
        self.assertEqual( plugin_mgr.plugins[ 'plugin2' ].path, os.path.join( expected_plugins_path, 'plugin2' ) )

        mock_app_dir.remove()

    def test_abs_path_search( self ):
        """should be able to search given abs. path"""
        mock_app_dir = galaxy_mock.MockDir({})
        mock_plugin_dir = galaxy_mock.MockDir({
            'plugin1': {},
            'plugin2': {},
            'file1': 'blerbler'
        })
        mock_app = galaxy_mock.MockApp( root=mock_app_dir.root_path )
        plugin_mgr = PluginManager( mock_app, directories_setting=mock_plugin_dir.root_path )
        expected_plugins_path = mock_plugin_dir.root_path

        self.assertEqual( plugin_mgr.directories, [ expected_plugins_path ] )
        self.assertEqual( sorted(plugin_mgr.plugins.keys()), [ 'plugin1', 'plugin2' ] )
        self.assertEqual( plugin_mgr.plugins[ 'plugin1' ].name, 'plugin1' )
        self.assertEqual( plugin_mgr.plugins[ 'plugin1' ].path, os.path.join( expected_plugins_path, 'plugin1' ) )
        self.assertEqual( plugin_mgr.plugins[ 'plugin2' ].name, 'plugin2' )
        self.assertEqual( plugin_mgr.plugins[ 'plugin2' ].path, os.path.join( expected_plugins_path, 'plugin2' ) )

    def test_multiple_dirs( self ):
        """should search in multiple directories"""
        mock_app_dir = galaxy_mock.MockDir({
            'plugins': {
                'plugin1': {},
                'plugin2': {},
                'file1': 'blerbler'
            }
        })
        mock_abs_plugin_dir = galaxy_mock.MockDir({
            'plugin3': {},
            'plugin4': {},
            'file2': 'blerbler'
        })
        mock_app = galaxy_mock.MockApp( root=mock_app_dir.root_path )
        directories_setting = ','.join([ 'plugins', mock_abs_plugin_dir.root_path ])
        plugin_mgr = PluginManager( mock_app, directories_setting=directories_setting )

        app_path = mock_app_dir.root_path
        expected_plugins_rel_path = os.path.join( app_path, 'plugins' )
        expected_plugins_abs_path = mock_abs_plugin_dir.root_path

        self.assertEqual( sorted(plugin_mgr.directories), sorted([ expected_plugins_rel_path, expected_plugins_abs_path ]) )
        self.assertEqual( sorted(plugin_mgr.plugins.keys()), [ 'plugin1', 'plugin2', 'plugin3', 'plugin4' ] )
        self.assertEqual( plugin_mgr.plugins[ 'plugin1' ].name, 'plugin1' )
        self.assertEqual( plugin_mgr.plugins[ 'plugin1' ].path, os.path.join( expected_plugins_rel_path, 'plugin1' ) )
        self.assertEqual( plugin_mgr.plugins[ 'plugin2' ].name, 'plugin2' )
        self.assertEqual( plugin_mgr.plugins[ 'plugin2' ].path, os.path.join( expected_plugins_rel_path, 'plugin2' ) )
        self.assertEqual( plugin_mgr.plugins[ 'plugin3' ].name, 'plugin3' )
        self.assertEqual( plugin_mgr.plugins[ 'plugin3' ].path, os.path.join( expected_plugins_abs_path, 'plugin3' ) )
        self.assertEqual( plugin_mgr.plugins[ 'plugin4' ].name, 'plugin4' )
        self.assertEqual( plugin_mgr.plugins[ 'plugin4' ].path, os.path.join( expected_plugins_abs_path, 'plugin4' ) )


if __name__ == '__main__':
    unittest.main()
