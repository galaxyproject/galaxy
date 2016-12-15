"""
"""
from __future__ import print_function

import json
import os
import sys
import unittest

import sqlalchemy
from six import string_types

from galaxy.managers.users import UserManager

unit_root = os.path.abspath( os.path.join( os.path.dirname( __file__ ), os.pardir ) )
sys.path.insert( 1, unit_root )
from unittest_utils import galaxy_mock

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
        self.user_manager = UserManager( self.app )

    def set_up_trans( self ):
        self.admin_user = self.user_manager.create( email=admin_email, username='admin', password=default_password )
        self.trans.set_user( self.admin_user )
        self.trans.set_history( None )

    def tearDown( self ):
        self.log( '.' * 20, 'end test', self, '\n' )

    def log( self, *args, **kwargs ):
        print( *args, **kwargs )

    # ---- additional test types
    TYPES_NEEDING_NO_SERIALIZERS = ( string_types, bool, type( None ), int, float )

    def assertKeys( self, obj, key_list ):
        self.assertEqual( sorted( obj.keys() ), sorted( key_list ) )

    def assertHasKeys( self, obj, key_list ):
        for key in key_list:
            if key not in obj:
                self.fail( 'Missing key: ' + key )
        else:
            self.assertTrue( True, 'keys found in object' )

    def assertNullableBasestring( self, item ):
        if not isinstance( item, ( string_types, type( None ) ) ):
            self.fail( 'Non-nullable basestring: ' + str( type( item ) ) )
        # TODO: len mod 8 and hex re
        self.assertTrue( True, 'is nullable basestring: ' + str( item ) )

    def assertEncodedId( self, item ):
        if not isinstance( item, string_types ):
            self.fail( 'Non-string: ' + str( type( item ) ) )
        # TODO: len mod 8 and hex re
        self.assertTrue( True, 'is id: ' + item )

    def assertNullableEncodedId( self, item ):
        if item is None:
            self.assertTrue( True, 'nullable id is None' )
        else:
            self.assertEncodedId( item )

    def assertDate( self, item ):
        if not isinstance( item, string_types ):
            self.fail( 'Non-string: ' + str( type( item ) ) )
        # TODO: no great way to parse this fully (w/o python-dateutil)
        # TODO: re?
        self.assertTrue( True, 'is date: ' + item )

    def assertUUID( self, item ):
        if not isinstance( item, string_types ):
            self.fail( 'Non-string: ' + str( type( item ) ) )
        # TODO: re for d4d76d69-80d4-4ed7-80c7-211ebcc1a358
        self.assertTrue( True, 'is uuid: ' + item )

    def assertORMFilter( self, item, msg=None ):
        if not isinstance( item, sqlalchemy.sql.elements.BinaryExpression ):
            self.fail( 'Not an orm filter: ' + str( type( item ) ) )
        self.assertTrue( True, msg or ( 'is an orm filter: ' + str( item ) ) )

    def assertFnFilter( self, item, msg=None ):
        if not item or not callable( item ):
            self.fail( 'Not a fn filter: ' + str( type( item ) ) )
        self.assertTrue( True, msg or ( 'is a fn filter: ' + str( item ) ) )

    def assertIsJsonifyable( self, item ):
        # TODO: use galaxy's override
        self.assertIsInstance( json.dumps( item ), string_types )


class CreatesCollectionsMixin( object ):

    def build_element_identifiers( self, elements ):
        identifier_list = []
        for element in elements:
            src = 'hda'
            # if isinstance( element, model.DatasetCollection ):
            #    src = 'collection'#?
            # elif isinstance( element, model.LibraryDatasetDatasetAssociation ):
            #    src = 'ldda'#?
            encoded_id = self.trans.security.encode_id( element.id )
            identifier_list.append( dict( src=src, name=element.name, id=encoded_id ) )
        return identifier_list


# =============================================================================
if __name__ == '__main__':
    # or more generally, nosetests test_resourcemanagers.py -s -v
    unittest.main()
