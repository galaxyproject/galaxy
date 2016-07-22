import json
from requests import put
from base import api

TEST_USER_EMAIL = "user_for_users_index_test@bx.psu.edu"


class UsersApiTestCase( api.ApiTestCase ):

    def test_index( self ):
        self._setup_user( TEST_USER_EMAIL )
        all_users_response = self._get( "users", admin=True )
        self._assert_status_code_is( all_users_response, 200 )
        all_users = all_users_response.json()
        # New user is in list
        assert len( [ u for u in all_users if u[ "email" ] == TEST_USER_EMAIL ] ) == 1
        # Request made from admin user, so should at least self and this
        # new user.
        assert len( all_users ) > 1

    def test_index_only_self_for_nonadmins( self ):
        self._setup_user( TEST_USER_EMAIL )
        with self._different_user():
            all_users_response = self._get( "users" )
            # Non admin users can only see themselves
            assert len( all_users_response.json() ) == 1

    def test_show( self ):
        user = self._setup_user( TEST_USER_EMAIL )
        with self._different_user( email=TEST_USER_EMAIL ):
            show_response = self.__show( user )
            self._assert_status_code_is( show_response, 200 )
            self.__assert_matches_user( user, show_response.json() )

    def test_update( self ):
        new_name = 'linnaeus'
        user = self._setup_user( TEST_USER_EMAIL )
        not_the_user = self._setup_user( 'email@example.com' )
        with self._different_user( email=TEST_USER_EMAIL ):

            # working
            update_response = self.__update( user, username=new_name )
            self._assert_status_code_is( update_response, 200 )
            update_json = update_response.json()
            self.assertEqual( update_json[ 'username' ], new_name )

            # too short
            update_response = self.__update( user, username='mu' )
            self._assert_status_code_is( update_response, 400 )

            # not them
            update_response = self.__update( not_the_user, username=new_name )
            self._assert_status_code_is( update_response, 403 )

            # non-existent
            no_user_id = self.security.encode_id( 100 )
            update_url = self._api_url( "users/%s" % ( no_user_id ), use_key=True )
            update_response = put( update_url, data=json.dumps( dict( username=new_name ) ) )
            self._assert_status_code_is( update_response, 404 )

    def test_admin_update( self ):
        new_name = 'flexo'
        user = self._setup_user( TEST_USER_EMAIL )

        update_url = self._api_url( "users/%s" % ( user[ "id" ] ), params=dict( key=self.master_api_key ) )
        update_response = put( update_url, data=json.dumps( dict( username=new_name ) ) )
        self._assert_status_code_is( update_response, 200 )
        update_json = update_response.json()
        self.assertEqual( update_json[ 'username' ], new_name )

    def __show( self, user ):
        return self._get( "users/%s" % ( user[ 'id' ] ) )

    def __update( self, user, **new_data ):
        update_url = self._api_url( "users/%s" % ( user[ "id" ] ), use_key=True )
        # TODO: Awkward json.dumps required here because of https://trello.com/c/CQwmCeG6
        body = json.dumps( new_data )
        return put( update_url, data=body )

    def __assert_matches_user( self, userA, userB ):
        self._assert_has_keys( userB, "id", "username", "total_disk_usage" )
        assert userA[ "id" ] == userB[ "id" ]
        assert userA[ "username" ] == userB[ "username" ]
