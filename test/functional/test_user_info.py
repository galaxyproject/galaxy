from base.twilltestcase import *
from base.test_db_util import *

not_logged_in_as_admin_security_msg = 'You must be logged in as an administrator to access this feature.'
logged_in_as_admin_security_msg = 'You must be an administrator to access this feature.'
not_logged_in_security_msg = 'You must be logged in to create/submit sequencing requests'
global form_one_name
form_one_name = "Student"
global form_two_name
form_two_name = "Researcher"

class TestUserInfo( TwillTestCase ):
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
    def test_005_create_user_info_forms( self ):
        """Testing creating a new user info form and editing it"""
        # Logged in as admin_user
        # Create a the first form
        name = form_one_name
        desc = "This is Student user info form's description"
        formtype = get_user_info_form_definition()
        self.create_form( name=name, desc=desc, formtype=formtype, num_fields=0 )
        # Get the form_definition object for later tests
        form_one = get_form( form_one_name )
        assert form_one is not None, 'Problem retrieving form named "%s" from the database' % name
        # edit form & add few more fields
        fields = [dict(name='Affiliation',
                       desc='The type of  organization you are affiliated with',
                       type='SelectField',
                       required='optional',
                       selectlist=['Educational', 'Research', 'Commercial']),
                  dict(name='Name of Organization',
                       desc='',
                       type='TextField',
                       required='optional'),
                  dict(name='Contact for feedback',
                       desc='',
                       type='CheckboxField',
                       required='optional')]
        self.form_add_field( form_one.current.id,
                             form_one.name,
                             form_one.desc,
                             form_one.type,
                             field_index=len( form_one.fields ),
                             fields=fields)
        form_one_latest = get_form( form_one_name )        
        assert len( form_one_latest.fields ) == len( form_one.fields ) + len( fields )
        # create the second form
        name = form_two_name
        desc = "This is Researcher user info form's description"
        self.create_form( name=name, desc=desc, formtype=formtype, num_fields=0 )
        # Get the form_definition object for later tests
        form_two = get_form( form_two_name )
        assert form_two is not None, 'Problem retrieving form named "%s" from the database' % name
        # edit form & add few more fields
        fields = [dict(name='Affiliation',
                       desc='The type of  organization you are affiliated with',
                       type='SelectField',
                       required='optional',
                       selectlist=['Educational', 'Research', 'Commercial']),
                  dict(name='Name of Organization',
                       desc='',
                       type='TextField',
                       required='optional'),
                  dict(name='Contact for feedback',
                       desc='',
                       type='CheckboxField',
                       required='optional')]
        self.form_add_field( form_two.current.id,
                             form_two.name,
                             form_two.desc,
                             form_two.type,
                             field_index=len( form_one.fields ),
                             fields=fields )
        form_two_latest = get_form( form_two_name )
        assert len( form_two_latest.fields ) == len( form_two.fields ) + len( fields )
    def test_010_user_reqistration_multiple_user_info_forms( self ):
        ''' Testing user registration with multiple user info forms '''
        # Logged in as admin_user
        self.logout()
        # Create a new user with 'Student' user info form
        form_one = get_form(form_one_name)
        user_info_values=['Educational', 'Penn State', True]
        self.create_user_with_info( 'test11@bx.psu.edu',
                                    'testuser',
                                    'test11', 
                                    user_info_forms='multiple',
                                    user_info_form_id=form_one.id, 
                                    user_info_values=user_info_values )
        global regular_user11
        regular_user11 = get_user( 'test11@bx.psu.edu' )
        assert regular_user11 is not None, 'Problem retrieving user with email "test11@bx.psu.edu" from the database'
        global regular_user11_private_role
        regular_user11_private_role = get_private_role( regular_user11 )
        self.logout()
        self.login( email=regular_user11.email, username='regular-user11' )
        self.visit_url( "%s/user/show_info" % self.url )
        self.check_page_for_string( "Manage User Information" )
        self.check_page_for_string( user_info_values[0] )
        self.check_page_for_string( user_info_values[1] )
        self.check_page_for_string( '<input type="checkbox" name="field_2" value="true" checked>' )
    def test_015_user_reqistration_single_user_info_forms( self ):
        ''' Testing user registration with a single user info form '''
        # Logged in as regular_user_11
        self.logout()
        self.login( email=admin_user.email )
        # Delete the 'Researcher' user info form
        form_two_latest = get_form( form_two_name )
        mark_form_deleted( form_two_latest )
        self.visit_url( '%s/forms/manage?sort=create_time&f-deleted=True' % self.url )
        self.check_page_for_string( form_two_latest.name )
        # Create a new user with 'Student' user info form
        form_one = get_form( form_one_name )
        user_info_values=['Educational', 'Penn State', True]
        self.create_user_with_info( 'test12@bx.psu.edu', 'testuser', 'test12', 
                                    user_info_forms='single',
                                    user_info_form_id=form_one.id, 
                                    user_info_values=user_info_values )
        global regular_user12
        regular_user12 = get_user( 'test12@bx.psu.edu' )
        assert regular_user12 is not None, 'Problem retrieving user with email "test12@bx.psu.edu" from the database'
        global regular_user12_private_role
        regular_user12_private_role = get_private_role( regular_user12 )
        self.logout()
        self.login( email=regular_user12.email, username='regular-user12' )
        self.visit_url( "%s/user/show_info" % self.url )
        self.check_page_for_string( "Manage User Information" )
        self.check_page_for_string( user_info_values[0] )
        self.check_page_for_string( user_info_values[1] )
        self.check_page_for_string( '<input type="checkbox" name="field_2" value="true" checked>' )
    def test_020_edit_user_info( self ):
        """Testing editing user info as a regular user"""
        # Logged in as regular_user_12
        # Test changing email and user name - first try an invalid user name
        self.edit_login_info( new_email='test12_new@bx.psu.edu',
                              new_username='test12_new',
                              check_str1='User name must contain only letters, numbers and' )
        # Now try a valid user name
        self.edit_login_info( new_email='test12_new@bx.psu.edu',
                              new_username='test12-new',
                              check_str1='The login information has been updated with the changes' )
        # Since we changed the user's account. make sure the user's private role was changed accordingly
        if not get_private_role( regular_user12 ):
            raise AssertionError, "The private role for %s was not correctly set when their account (email) was changed" % regular_user12.email
        # Test changing password
        self.change_password( 'testuser', 'testuser#' )
        self.logout()
        refresh( regular_user12 )
        # Test logging in with new email and password
        self.login( email=regular_user12.email, password='testuser#' )
        # Test editing the user info
        self.edit_user_info( ['Research', 'PSU'] )
    def test_999_reset_data_for_later_test_runs( self ):
        # Logged in as regular_user_12
        self.logout()
        self.login( email=admin_user.email )
        ###############
        # Mark form_one as deleted ( form_two was marked deleted earlier )
        ###############
        form_latest = get_form( form_one_name )
        mark_form_deleted( form_latest )
        ###############
        # Manually delete the test_user11
        ###############
        self.mark_user_deleted( user_id=self.security.encode_id( regular_user11.id ), email=regular_user11.email )
        refresh( regular_user11 )
        self.purge_user( self.security.encode_id( regular_user11.id ), regular_user11.email )
        refresh( regular_user11 )
        # We should now only the the user and his private role
        delete_user_roles( regular_user11 )
        delete_obj( regular_user11 )
        ###############
        # Manually delete the test_user12
        ###############
        refresh( regular_user12 )
        self.mark_user_deleted( user_id=self.security.encode_id( regular_user12.id ), email=regular_user12.email )
        refresh( regular_user12 )
        self.purge_user( self.security.encode_id( regular_user12.id ), regular_user12.email )
        refresh( regular_user12 )
        # We should now only the the user and his private role
        delete_user_roles( regular_user12 )
        delete_obj( regular_user12 )
