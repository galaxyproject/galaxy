from base.twilltestcase import TwillTestCase
from base.test_db_util import (
    get_user,
    get_private_role,
    get_latest_history_for_user,
    get_latest_hda,
)

history1 = None
admin_user = None


class TestTags( TwillTestCase ):

    # TODO: Add more functional test coverage for tags
    def test_000_initiate_users( self ):
        """Ensuring all required user accounts exist"""
        self.logout()
        self.login( email='test1@bx.psu.edu', username='regular-user1' )
        global regular_user1
        regular_user1 = get_user( 'test1@bx.psu.edu' )
        assert regular_user1 is not None, 'Problem retrieving user with email "test1@bx.psu.edu" from the database'
        global regular_user1_private_role
        regular_user1_private_role = get_private_role( regular_user1 )
        self.logout()
        self.login( email='test2@bx.psu.edu', username='regular-user2' )
        global regular_user2
        regular_user2 = get_user( 'test2@bx.psu.edu' )
        assert regular_user2 is not None, 'Problem retrieving user with email "test2@bx.psu.edu" from the database'
        global regular_user2_private_role
        regular_user2_private_role = get_private_role( regular_user2 )
        self.logout()
        self.login( email='test3@bx.psu.edu', username='regular-user3' )
        global regular_user3
        regular_user3 = get_user( 'test3@bx.psu.edu' )
        assert regular_user3 is not None, 'Problem retrieving user with email "test3@bx.psu.edu" from the database'
        global regular_user3_private_role
        regular_user3_private_role = get_private_role( regular_user3 )
        self.logout()
        self.login( email='test@bx.psu.edu', username='admin-user' )
        global admin_user
        admin_user = get_user( 'test@bx.psu.edu' )
        assert admin_user is not None, 'Problem retrieving user with email "test@bx.psu.edu" from the database'
        global admin_user_private_role
        admin_user_private_role = get_private_role( admin_user )

    def test_005_add_tag_to_history( self ):
        """Testing adding a tag to a history"""
        # Logged in as admin_user
        # Create a new, empty history named anonymous
        name = 'anonymous'
        self.new_history( name=name )
        global history1
        history1 = get_latest_history_for_user( admin_user )
        self.add_tag( self.security.encode_id( history1.id ),
                      'History',
                      'history.mako',
                      'hello' )
        self.get_tags( self.security.encode_id( history1.id ), 'History' )
        self.check_page_for_string( 'tags : {"hello": ""}' )

    def test_010_add_tag_to_history_item( self ):
        """Testing adding a tag to a history item"""
        # Logged in as admin_user
        self.upload_file( '1.bed' )
        latest_hda = get_latest_hda()
        self.add_tag( self.security.encode_id( latest_hda.id ),
                      'HistoryDatasetAssociation',
                      'edit_attributes.mako',
                      'goodbye' )
        self.check_hda_attribute_info( 'tags : {"goodbye"' )

    def test_999_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to to be valid"""
        # logged in as admin_user
        # Delete histories
        self.delete_history( id=self.security.encode_id( history1.id ) )
