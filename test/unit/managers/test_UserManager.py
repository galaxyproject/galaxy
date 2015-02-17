#!/usr/bin/env python
"""
"""
import sys
import os
import pprint
import unittest

__GALAXY_ROOT__ = os.getcwd() + '/../../../'
sys.path.insert( 1, __GALAXY_ROOT__ + 'lib' )

from galaxy import eggs
eggs.require( 'SQLAlchemy >= 0.4' )
import sqlalchemy

from galaxy import model
from galaxy import exceptions
from galaxy.util.bunch import Bunch

import mock
from test_ModelManager import BaseTestCase


# =============================================================================
admin_email = 'admin@admin.admin'
admin_users = admin_email
default_password = '123456'
user2_data = dict( email='user2@user2.user2', username='user2', password=default_password )
user3_data = dict( email='user3@user3.user3', username='user3', password=default_password )


# =============================================================================
class UserManagerTestCase( BaseTestCase ):

    def test_framework( self ):
        self.log( "(for testing) should have admin_user, and admin_user is current" )
        self.assertEqual( self.trans.user, self.admin_user )

    def test_base( self ):
        self.log( "should be able to create a user" )
        user2 = self.user_mgr.create( self.trans, **user2_data )
        self.assertIsInstance( user2, model.User )
        self.assertIsNotNone( user2.id )
        self.assertEqual( user2.email, user2_data[ 'email' ] )
        self.assertEqual( user2.password, default_password )

        user3 = self.user_mgr.create( self.trans, **user3_data )

        self.log( "should be able to query" )
        users = self.trans.sa_session.query( model.User ).all()
        self.assertEqual( self.user_mgr.list( self.trans ), users )

        self.assertEqual( self.user_mgr.by_id( self.trans, user2.id ), user2 )
        self.assertEqual( self.user_mgr.by_ids( self.trans, [ user3.id, user2.id ] ), [ user3, user2 ] )

        self.log( "should be able to limit and offset" )
        self.assertEqual( self.user_mgr.list( self.trans, limit=1 ), users[0:1] )
        self.assertEqual( self.user_mgr.list( self.trans, offset=1 ), users[1:] )
        self.assertEqual( self.user_mgr.list( self.trans, limit=1, offset=1 ), users[1:2] )

        self.assertEqual( self.user_mgr.list( self.trans, limit=0 ), [] )
        self.assertEqual( self.user_mgr.list( self.trans, offset=3 ), [] )

        self.log( "should be able to order" )
        self.assertEqual( self.user_mgr.list( self.trans, order_by=( sqlalchemy.desc( model.User.create_time ) ) ),
            [ user3, user2, self.admin_user ] )

    def test_invalid_create( self ):
        user2 = self.user_mgr.create( self.trans, **user2_data )

        self.log( "emails must be unique" )
        self.assertRaises( exceptions.Conflict, self.user_mgr.create,
            self.trans, **dict( email='user2@user2.user2', username='user2a', password=default_password ) )
        self.log( "usernames must be unique" )
        self.assertRaises( exceptions.Conflict, self.user_mgr.create,
            self.trans, **dict( email='user2a@user2.user2', username='user2', password=default_password ) )

    def test_email_queries( self ):
        user2 = self.user_mgr.create( self.trans, **user2_data )
        user3 = self.user_mgr.create( self.trans, **user3_data )

        self.log( "should be able to query by email" )
        self.assertEqual( self.user_mgr.by_email( self.trans, user2_data[ 'email' ] ), user2 )

        #note: sorted by email alpha
        users = self.trans.sa_session.query( model.User ).all()
        self.assertEqual( self.user_mgr.by_email_like( self.trans, '%@%' ), [ self.admin_user, user2, user3 ] )

    def test_admin( self ):
        user2 = self.user_mgr.create( self.trans, **user2_data )
        user3 = self.user_mgr.create( self.trans, **user3_data )

        self.log( "should be able to test whether admin" )
        self.assertTrue( self.user_mgr.is_admin( self.trans, self.admin_user ) )
        self.assertFalse( self.user_mgr.is_admin( self.trans, user2 ) )
        self.assertEqual( self.user_mgr.admins( self.trans ), [ self.admin_user ] )
        self.assertRaises( exceptions.AdminRequiredException, self.user_mgr.error_unless_admin, self.trans, user2 )
        self.assertEqual( self.user_mgr.error_unless_admin( self.trans, self.admin_user ), self.admin_user )

    def test_anonymous( self ):
        anon = None
        user2 = self.user_mgr.create( self.trans, **user2_data )

        self.log( "should be able to tell if a user is anonymous" )
        self.assertRaises( exceptions.AuthenticationFailed, self.user_mgr.error_if_anonymous, self.trans, anon )
        self.assertEqual( self.user_mgr.error_if_anonymous( self.trans, user2 ), user2 )

    def test_current( self ):
        user2 = self.user_mgr.create( self.trans, **user2_data )
        user3 = self.user_mgr.create( self.trans, **user3_data )

        self.log( "should be able to tell if a user is the current (trans) user" )
        self.assertEqual( self.user_mgr.current_user( self.trans ), self.admin_user )
        self.assertNotEqual( self.user_mgr.current_user( self.trans ), user2 )

    def test_api_keys( self ):
        user2 = self.user_mgr.create( self.trans, **user2_data )
        user3 = self.user_mgr.create( self.trans, **user3_data )

        self.log( "should return None if no APIKey has been created" )
        self.assertEqual( self.user_mgr.valid_api_key( self.trans, user2 ), None )

        self.log( "should be able to generate and retrieve valid api key" )
        user2_api_key = self.user_mgr.create_api_key( self.trans, user2 )
        self.assertIsInstance( user2_api_key, basestring )
        self.assertEqual( self.user_mgr.valid_api_key( self.trans, user2 ).key, user2_api_key )

        self.log( "should return the most recent (i.e. most valid) api key" )
        user2_api_key_2 = self.user_mgr.create_api_key( self.trans, user2 )
        self.assertEqual( self.user_mgr.valid_api_key( self.trans, user2 ).key, user2_api_key_2 )


# =============================================================================
if __name__ == '__main__':
    # or more generally, nosetests test_resourcemanagers.py -s -v
    unittest.main()
