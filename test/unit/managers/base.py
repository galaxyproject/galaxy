#!/usr/bin/env python
"""
"""
from __future__ import print_function

import os
import imp
import unittest

test_utils = imp.load_source( 'test_utils',
    os.path.join( os.path.dirname( __file__), '../unittest_utils/utility.py' ) )
import galaxy_mock

from galaxy.managers.users import UserManager

# =============================================================================
admin_email = 'admin@admin.admin'
admin_users = admin_email
default_password = '123456'


# =============================================================================
class BaseTestCase( unittest.TestCase ):

    @classmethod
    def setUpClass( cls ):
        print( '\n', '-' * 20, 'begin class', cls )

    @classmethod
    def tearDownClass( cls ):
        print( '\n', '-' * 20, 'end class', cls )

    def __init__( self, *args ):
        unittest.TestCase.__init__( self, *args )

    def setUp( self ):
        self.log( '.' * 20, 'begin test', self )
        self.set_up_mocks()
        self.set_up_managers()
        self.set_up_trans()

    def set_up_mocks( self ):
        self.trans = galaxy_mock.MockTrans( admin_users=admin_users )
        self.app = self.trans.app

    def set_up_managers( self ):
        self.user_mgr = UserManager( self.app )

    def set_up_trans( self ):
        self.admin_user = self.user_mgr.create( self.trans,
            email=admin_email, username='admin', password=default_password )
        self.trans.set_user( self.admin_user )
        self.trans.set_history( None )

    def tearDown( self ):
        self.log( '.' * 20, 'end test', self, '\n' )

    def log( self, *args, **kwargs ):
        print( *args, **kwargs )

    # ---- additional test types
    def assertKeys( self, obj, key_list ):
        self.assertEqual( sorted( obj.keys() ), sorted( key_list ) )

    def assertHasKeys( self, obj, key_list ):
        for key in key_list:
            if key not in obj:
                self.fail( 'Missing key: ' + key )
        else:
            self.assertTrue( True, 'keys found in object' )


# =============================================================================
if __name__ == '__main__':
    # or more generally, nosetests test_resourcemanagers.py -s -v
    unittest.main()
