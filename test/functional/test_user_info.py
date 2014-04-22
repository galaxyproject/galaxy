from base.twilltestcase import *
from base.test_db_util import *

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
        name = "Student"
        desc = "This is Student user info form's description"
        form_type = get_user_info_form_definition()
        self.create_form( name=name,
                          description=desc,
                          form_type=form_type,
                          num_fields=0,
                          strings_displayed=[ 'Create a new form definition' ],
                          strings_displayed_after_submit=[ name, desc, form_type ] )
        tmp_form = get_form( 'Student' )
        # Add fields to the form
        field_dicts = [ dict( label='Affiliation',
                              desc='The type of  organization you are affiliated with',
                              type='SelectField',
                              required='optional',
                              selectlist=[ 'Educational', 'Research', 'Commercial' ],
                              name='affiliation' ),
                        dict( label='Name of Organization',
                              desc='',
                              type='TextField',
                              required='optional',
                              name='name_of_oganization' ),
                        dict( label='Contact for feedback',
                              desc='',
                              type='CheckboxField',
                              required='optional',
                              name='contact_for_feedback' ) ]
        self.edit_form( id=self.security.encode_id( tmp_form.current.id ),
                        field_dicts=field_dicts,
                        field_index=len( tmp_form.fields ),
                        strings_displayed=[ 'Edit form definition "Student"' ],
                        strings_displayed_after_submit=[ "The form 'Student' has been updated with the changes." ] )
        # Get the form_definition object for later tests
        global form_one
        form_one = get_form( 'Student' )
        assert form_one is not None, 'Problem retrieving form named "Student" from the database'
        assert len( form_one.fields ) == len( tmp_form.fields ) + len( field_dicts )
        # Create the second form
        name = "Researcher"
        desc = "This is Researcher user info form's description"
        self.create_form( name=name,
                          description=desc,
                          form_type=form_type,
                          num_fields=0,
                          strings_displayed=[ 'Create a new form definition' ],
                          strings_displayed_after_submit=[ name, desc, form_type ] )
        tmp_form = get_form( 'Researcher' )
        # Add fields to the form
        self.edit_form( id=self.security.encode_id( tmp_form.current.id ),
                        field_dicts=field_dicts,
                        field_index=len( tmp_form.fields ),
                        strings_displayed=[ 'Edit form definition "Researcher"' ],
                        strings_displayed_after_submit=[ "The form 'Researcher' has been updated with the changes." ] )
        # Get the form_definition object for later tests
        global form_two
        form_two = get_form( 'Researcher' )
        assert form_two is not None, 'Problem retrieving form named "Researcher" from the database'
        assert len( form_two.fields ) == len( tmp_form.fields ) + len( field_dicts )

    def test_010_user_reqistration_multiple_user_info_forms( self ):
        """Testing user registration with multiple user info forms"""
        # Logged in as admin_user
        self.logout()
        # Create a new user with 'Student' user info form.  The user_info_values will be the values
        # filled into the fields defined in field_dicts above ( 'Educational' -> 'Affiliation,
        # 'Penn State' -> 'Name of Organization', '1' -> 'Contact for feedback' )
        email = 'test11@bx.psu.edu'
        password = 'testuser'
        username = 'test11'
        user_info_values=[ ( 'affiliation', 'Educational' ), 
                           ( 'name_of_oganization', 'Penn State' ), 
                           ( 'contact_for_feedback', '1' ) ]
        self.create_user_with_info( cntrller='admin',
                                    email=email,
                                    password=password,
                                    username=username, 
                                    user_type_fd_id=self.security.encode_id( form_one.id ), 
                                    user_info_values=user_info_values,
                                    strings_displayed=[ "Create account", "User type" ] )
        global regular_user11
        regular_user11 = get_user( email )
        assert regular_user11 is not None, 'Problem retrieving user with email "%s" from the database' % email
        global regular_user11_private_role
        regular_user11_private_role = get_private_role( regular_user11 )
        self.logout()
        self.login( email=regular_user11.email, username=username )
        global form_checkbox_field3_string
        form_checkbox_field3_string = '<input type="checkbox" id="contact_for_feedback" name="contact_for_feedback" value="true" checked="checked">'
        self.edit_user_info( cntrller='user',
                             strings_displayed=[ "Manage User Information",
                                                 user_info_values[0][1],
                                                 user_info_values[1][1],
                                                 form_checkbox_field3_string ] )

    def test_015_user_reqistration_single_user_info_forms( self ):
        """Testing user registration with a single user info form"""
        # Logged in as regular_user_11
        self.logout()
        self.login( email=admin_user.email )
        # Delete the 'Researcher' user info form
        self.mark_form_deleted( self.security.encode_id( form_two.current.id ) )
        # Create a new user with 'Student' user info form.  The user_info_values will be the values
        # filled into the fields defined in field_dicts above ( 'Educational' -> 'Affiliation,
        # 'Penn State' -> 'Name of Organization', '1' -> 'Contact for feedback' )
        email = 'test12@bx.psu.edu'
        password = 'testuser'
        username = 'test12'
        user_info_values=[ ( 'affiliation', 'Educational' ), 
                           ( 'name_of_oganization', 'Penn State' ), 
                           ( 'contact_for_feedback', '1' ) ]
        self.create_user_with_info( cntrller='admin',
                                    email=email,
                                    password=password,
                                    username=username, 
                                    user_type_fd_id=self.security.encode_id( form_one.id ), 
                                    user_info_values=user_info_values,
                                    strings_displayed=[ "Create account", "User type" ] )
        global regular_user12
        regular_user12 = get_user( email )
        assert regular_user12 is not None, 'Problem retrieving user with email "%s" from the database' % email
        global regular_user12_private_role
        regular_user12_private_role = get_private_role( regular_user12 )
        self.logout()
        self.login( email=regular_user12.email, username=username )
        self.edit_user_info( cntrller='user',
                             strings_displayed=[ "Manage User Information",
                                                 user_info_values[0][1],
                                                 user_info_values[1][1],
                                                 form_checkbox_field3_string ] )

    def test_020_edit_user_info( self ):
        """Testing editing user info as a regular user"""
        # Logged in as regular_user_12
        # Test changing email and user name - first try an invalid user name
        regular_user12 = get_user( 'test12@bx.psu.edu' )
        self.edit_user_info( cntrller='user',
                             new_email='test12_new@bx.psu.edu',
                             new_username='test12_new',
                             strings_displayed_after_submit=[ "Public names must be at least four characters" ] )
        # Now try a valid user name
        self.edit_user_info( cntrller='user',
                             new_email='test12_new@bx.psu.edu',
                             new_username='test12-new',
                             strings_displayed_after_submit=[ 'The login information has been updated with the changes' ] )
        # Since we changed the user's account. make sure the user's private role was changed accordingly
        if not get_private_role( regular_user12 ):
            raise AssertionError, "The private role for %s was not correctly set when their account (email) was changed" % regular_user12.email
        # Test changing password
        self.edit_user_info( cntrller='user',
                             password='testuser',
                             new_password='testuser#',\
                             strings_displayed_after_submit=[ 'The password has been changed' ] )
        self.logout()
        refresh( regular_user12 )
        # Test logging in with new email and password
        self.login( email=regular_user12.email, password='testuser#' )
        # Test editing the user info
        new_user_info_values=[ ( 'affiliation', 'Educational' ), 
                               ( 'name_of_oganization', 'Penn State' ) ]
        self.edit_user_info( cntrller='user',
                             info_values=new_user_info_values,
                             strings_displayed_after_submit=[ "The user information has been updated with the changes" ] )

    def test_999_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to pass"""
        # Logged in as regular_user_12
        self.logout()
        self.login( email=admin_user.email )
        ##################
        # Mark all forms deleted that have not yet been marked deleted ( form_two has )
        ##################
        for form in [ form_one ]:
            self.mark_form_deleted( self.security.encode_id( form.current.id ) )
        ###############
        # Purge private roles
        ###############
        for role in [ regular_user11_private_role, regular_user12_private_role ]:
            self.mark_role_deleted( self.security.encode_id( role.id ), role.name )
            self.purge_role( self.security.encode_id( role.id ), role.name )
            # Manually delete the role from the database
            refresh( role )
            delete_obj( role )
        ###############
        # Purge appropriate users
        ###############
        for user in [ regular_user11, regular_user12 ]:
            self.mark_user_deleted( user_id=self.security.encode_id( user.id ), email=user.email )
            refresh( user )
            self.purge_user( self.security.encode_id( user.id ), user.email )
            refresh( user )
            delete_user_roles( user )
            delete_obj( user )
