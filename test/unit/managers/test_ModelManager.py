"""
"""
from __future__ import print_function

import sys
import os
import pprint
import unittest
import json

__GALAXY_ROOT__ = os.getcwd() + '/../../../'
sys.path.insert( 1, __GALAXY_ROOT__ + 'lib' )

from galaxy import eggs
eggs.require( 'SQLAlchemy >= 0.4' )
import sqlalchemy

from galaxy import model
from galaxy import exceptions
from galaxy.util.bunch import Bunch

import mock
from galaxy.managers.users import UserManager

from galaxy.managers import base

# =============================================================================
admin_email = 'admin@admin.admin'
admin_users = admin_email
default_password = '123456'

#def setUpModule():
#    print '=' * 20, 'begin module'
#
#def tearDownModule():
#    print '=' * 20, 'end module'


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
        self.trans = mock.MockTrans( admin_users=admin_users )
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
    TYPES_NEEDING_NO_SERIALIZERS = ( basestring, bool, type( None ), int, float )

    def assertKeys( self, obj, key_list ):
        self.assertEqual( sorted( obj.keys() ), sorted( key_list ) )

    def assertHasKeys( self, obj, key_list ):
        for key in key_list:
            if key not in obj:
                self.fail( 'Missing key: ' + key )
        else:
            self.assertTrue( True, 'keys found in object' )

    def assertNullableBasestring( self, item ):
        if not isinstance( item, ( basestring, type( None ) ) ):
            self.fail( 'Non-nullable basestring: ' + str( type( item ) ) )
        # TODO: len mod 8 and hex re
        self.assertTrue( True, 'is nullable basestring: ' + str( item ) )

    def assertEncodedId( self, item ):
        if not isinstance( item, basestring ):
            self.fail( 'Non-string: ' + str( type( item ) ) )
        # TODO: len mod 8 and hex re
        self.assertTrue( True, 'is id: ' + item )

    def assertNullableEncodedId( self, item ):
        if item is None:
            self.assertTrue( True, 'nullable id is None' )
        else:
            self.assertEncodedId( item )

    def assertDate( self, item ):
        if not isinstance( item, basestring ):
            self.fail( 'Non-string: ' + str( type( item ) ) )
        # TODO: no great way to parse this fully (w/o python-dateutil)
        # TODO: re?
        self.assertTrue( True, 'is date: ' + item )

    def assertUUID( self, item ):
        if not isinstance( item, basestring ):
            self.fail( 'Non-string: ' + str( type( item ) ) )
        # TODO: re for d4d76d69-80d4-4ed7-80c7-211ebcc1a358
        self.assertTrue( True, 'is uuid: ' + item )

    def assertORMFilter( self, item, msg=None ):
        if not isinstance( item, sqlalchemy.sql.elements.BinaryExpression ):
            self.fail( 'Not an orm filter: ' + str( type( item ) ) )
        # TODO: re for d4d76d69-80d4-4ed7-80c7-211ebcc1a358
        self.assertTrue( True, msg or ( 'is an orm filter: ' + item ) )

    def assertIsJsonifyable( self, item ):
        # TODO: use galaxy's override
        self.assertIsInstance( json.dumps( item ), basestring )


# =============================================================================
if __name__ == '__main__':
    # or more generally, nosetests test_resourcemanagers.py -s -v
    unittest.main()
