import galaxy.model
from galaxy.model.orm import *
from base.twilltestcase import *
from base.test_db_util import *

sample_states = [  ( 'New', 'Sample entered into the system' ), 
                   ( 'Received', 'Sample tube received' ), 
                   ( 'Done', 'Sequence run complete' ) ]
address_dict = dict( short_desc="Office",
                     name="James+Bond",
                     institution="MI6" ,
                     address="MI6+Headquarters",
                     city="London",
                     state="London",
                     postal_code="007",
                     country="United+Kingdom",
                     phone="007-007-0007" )

class TestFormsAndRequests( TwillTestCase ):
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
    def test_005_create_required_groups_and_roles( self ):
        """Testing creating all required groups and roles for this script"""
        # Logged in as admin_user
        # Create role_one
        name = 'Role One'
        description = "This is Role One's description"
        user_ids = [ str( admin_user.id ), str( regular_user1.id ), str( regular_user3.id ) ]
        self.create_role( name=name,
                          description=description,
                          in_user_ids=user_ids,
                          in_group_ids=[],
                          create_group_for_role='no',
                          private_role=admin_user.email )
        # Get the role object for later tests
        global role_one
        role_one = get_role_by_name( name )
        # Create group_one
        name = 'Group One'
        self.create_group( name=name, in_user_ids=[ str( regular_user1.id ) ], in_role_ids=[ str( role_one.id ) ] )
        # Get the group object for later tests
        global group_one
        group_one = get_group_by_name( name )
        assert group_one is not None, 'Problem retrieving group named "Group One" from the database'
        # NOTE: To get this to work with twill, all select lists on the ~/admin/role page must contain at least
        # 1 option value or twill throws an exception, which is: ParseError: OPTION outside of SELECT
        # Due to this bug in twill, we create the role, we bypass the page and visit the URL in the
        # associate_users_and_groups_with_role() method.
        #
        #create role_two
        name = 'Role Two'
        description = 'This is Role Two'
        user_ids = [ str( admin_user.id ) ]
        group_ids = [ str( group_one.id ) ]
        private_role = admin_user.email
        self.create_role( name=name,
                          description=description,
                          in_user_ids=user_ids,
                          in_group_ids=group_ids,
                          private_role=private_role )
        # Get the role object for later tests
        global role_two
        role_two = get_role_by_name( name )
        assert role_two is not None, 'Problem retrieving role named "Role Two" from the database'
    def test_010_create_form( self ):
        """Testing creating a new form and editing it"""
        self.logout()
        self.login( email=admin_user.email )
        # create a form
        name = "Request Form"
        desc = "This is Form One's description"
        formtype = galaxy.model.FormDefinition.types.REQUEST
        self.create_form( name=name, desc=desc, formtype=formtype, num_fields=0 )
        # Get the form_definition object for later tests
        global form_one
        form_one = get_form( name )
        assert form_one is not None, 'Problem retrieving form named "%s" from the database' % name
        # edit form & add few more fields
        new_name = "Request Form (Renamed)"
        new_desc = "This is Form One's Re-described"
        self.edit_form( form_one.current.id, form_one.name, new_form_name=new_name, new_form_desc=new_desc )
        self.home()
        self.visit_page( 'forms/manage' )
        self.check_page_for_string( new_name )
        self.check_page_for_string( new_desc )
        form_one = get_form( new_name )
    def test_015_add_form_fields( self ):
        """Testing adding fields to a form definition"""
        fields = [dict(name='Test field name one',
                       desc='Test field description one',
                       type='SelectField',
                       required='optional',
                       selectlist=['option1', 'option2']),
                  dict(name='Test field name two',
                       desc='Test field description two',
                       type='AddressField',
                       required='optional'),
                  dict(name='Test field name three',
                       desc='Test field description three',
                       type='TextField',
                       required='required')]
        self.form_add_field( form_one.current.id,
                             form_one.name,
                             form_one.desc,
                             form_one.type, 
                             field_index=len( form_one.fields ),
                             fields=fields )
        form_one_latest = get_form( form_one.name )
        assert len( form_one_latest.fields ) == len( form_one.fields ) + len( fields )
    def test_020_create_sample_form( self ):
        """Testing creating another form (for samples)"""
        name = "Sample Form"
        desc = "This is Form Two's description"
        formtype = galaxy.model.FormDefinition.types.SAMPLE
        form_layout_name = 'Layout Grid One'
        self.create_form( name=name, desc=desc, formtype=formtype, form_layout_name=form_layout_name )
        global form_two
        form_two = get_form( name )
        assert form_two is not None, "Error retrieving form %s from db" % name
        self.home()
        self.visit_page( 'forms/manage' )
        self.check_page_for_string( form_two.name )
        self.check_page_for_string( desc )
        self.check_page_for_string( formtype )
    def test_025_create_request_type( self ):
        """Testing creating a new requestype"""
        request_form = get_form( form_one.name )
        sample_form = get_form( form_two.name )
        name = 'Test Requestype'
        self.create_request_type( name, "test sequencer configuration", str( request_form.id ), str( sample_form.id ), sample_states )
        global request_type1
        request_type1 = get_request_type_by_name( name )
        assert request_type1 is not None, 'Problem retrieving sequencer configuration named "%s" from the database' % name
        # Set permissions
        permissions_in = [ k for k, v in galaxy.model.RequestType.permitted_actions.items() ]
        permissions_out = []
        # Role one members are: admin_user, regular_user1, regular_user3.  Each of these users will be permitted for
        # REQUEST_TYPE_ACCESS on this request_type
        self.request_type_permissions( self.security.encode_id( request_type1.id ),
                                       request_type1.name,
                                       str( role_one.id ),
                                       permissions_in,
                                       permissions_out )
        # Make sure the request_type1 is not accessible by regular_user2 since regular_user2 does not have Role1.
        self.logout()
        self.login( email=regular_user2.email )
        self.visit_url( '%s/requests_common/new?cntrller=requests&select_request_type=True' % self.url )
        try:
            self.check_page_for_string( 'There are no sequencer configurations created for a new request.' )
            raise AssertionError, 'The request_type %s is accessible by %s when it should be restricted' % ( request_type1.name, regular_user2.email )
        except:
            pass
        self.logout()
        self.login( email=admin_user.email )
    def test_030_create_address_and_library( self ):
        """Testing address & library creation"""
        # ( 9/17/10 placed by gvk ) Hey, RC, why is this test here? The library is never used later in this script.
        # first create a library for the request so that it can be submitted later
        name = "TestLib001"
        description = "TestLib001 description"
        synopsis = "TestLib001 synopsis"
        self.create_library( name=name, description=description, synopsis=synopsis )
        # Get the library object for later tests
        global library_one
        library_one = get_library( name, description, synopsis )
        assert library_one is not None, 'Problem retrieving library named "%s" from the database' % name
        # Make sure library_one is public
        assert 'access library' not in [ a.action for a in library_one.actions ], 'Library %s is not public when first created' % library_one.name
        # Set permissions on the library, sort for later testing.
        permissions_in = [ k for k, v in galaxy.model.Library.permitted_actions.items() ]
        permissions_out = []
        # Role one members are: admin_user, regular_user1, regular_user3.  Each of these users will be permitted for
        # LIBRARY_ACCESS, LIBRARY_ADD, LIBRARY_MODIFY, LIBRARY_MANAGE on this library and it's contents.
        self.library_permissions( self.security.encode_id( library_one.id ),
                                  library_one.name,
                                  str( role_one.id ),
                                  permissions_in,
                                  permissions_out )
        # Make sure the library is accessible by admin_user
        self.visit_url( '%s/library/browse_libraries' % self.url )
        self.check_page_for_string( library_one.name )
        # Make sure the library is not accessible by regular_user2 since regular_user2 does not have Role1.
        self.logout()
        self.login( email=regular_user2.email )
        self.visit_url( '%s/library/browse_libraries' % self.url )
        try:
            self.check_page_for_string( library_one.name )
            raise AssertionError, 'Library %s is accessible by %s when it should be restricted' % ( library_one.name, regular_user2.email )
        except:
            pass
        self.logout()
        self.login( email=admin_user.email )
        # create folder
        root_folder = library_one.root_folder
        name = "Root Folder's Folder One"
        description = "This is the root folder's Folder One"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library_one.id ),
                         self.security.encode_id( root_folder.id ),
                         name=name,
                         description=description )
        global folder_one
        folder_one = get_folder( root_folder.id, name, description )
        assert folder_one is not None, 'Problem retrieving library folder named "%s" from the database' % name
        # create address
        self.logout()
        self.login( email=regular_user1.email )
        self.add_user_address( regular_user1.id, address_dict )
        global user_address1
        user_address1 = get_user_address( regular_user1, address_dict[ 'short_desc' ] )    
    def test_035_create_request( self ):
        """Testing creating, editing and submitting a request as a regular user"""
        # login as a regular user
        self.logout()
        self.login( email=regular_user1.email )
        # set field values
        fields = ['option1', str(user_address1.id), 'field three value'] 
        # create the request
        name = 'Request One'
        desc = 'Request One Description'
        self.create_request(request_type1.id, name, desc, fields)
        global request_one
        request_one = get_request_by_name( name )        
        # check if the request's state is now set to 'new'
        assert request_one.state is not request_one.states.NEW, "The state of the request '%s' should be set to '%s'" \
            % ( request_one.name, request_one.states.NEW )
        # sample fields
        samples = [ ( 'Sample One', [ 'S1 Field 0 Value' ] ),
                    ( 'Sample Two', [ 'S2 Field 0 Value' ] ) ]
        # add samples to this request
        self.add_samples( request_one.id, request_one.name, samples )
        # edit this request
        fields = ['option2', str(user_address1.id), 'field three value (edited)'] 
        self.edit_request(request_one.id, request_one.name, request_one.name+' (Renamed)', 
                          request_one.desc+' (Re-described)', fields)
        refresh( request_one )
        # check if the request is showing in the 'new' filter
        self.check_request_grid(state=request_one.states.NEW, request_name=request_one.name)
        # submit the request
        self.submit_request( request_one.id, request_one.name )
        refresh( request_one )
        # check if the request is showing in the 'submitted' filter
        self.check_request_grid(state=request_one.states.SUBMITTED, request_name=request_one.name)
        # check if the request's state is now set to 'submitted'
        assert request_one.state is not request_one.states.SUBMITTED, "The state of the request '%s' should be set to '%s'" \
            % ( request_one.name, request_one.states.SUBMITTED )
    def test_040_request_lifecycle( self ):
        """Testing request lifecycle as it goes through all the states"""
        # goto admin manage requests page
        self.logout()
        self.login( email=admin_user.email )
        self.check_request_admin_grid(state=request_one.states.SUBMITTED, request_name=request_one.name)
        self.visit_url( "%s/requests_admin/list?operation=show&id=%s" \
                        % ( self.url, self.security.encode_id( request_one.id ) ))
        self.check_page_for_string( 'Sequencing Request "%s"' % request_one.name )
        # set bar codes for the samples
        bar_codes = [ '1234567890', '0987654321' ]
        self.add_bar_codes( request_one.id, request_one.name, bar_codes, request_one.samples )
        # change the states of all the samples of this request
        for sample in request_one.samples:
            self.change_sample_state( request_one.id, request_one.name, sample.name, sample.id, request_type1.states[1].id, request_type1.states[1].name )
            self.change_sample_state( request_one.id, request_one.name, sample.name, sample.id, request_type1.states[2].id, request_type1.states[2].name )
        self.home()
        refresh( request_one )
        self.logout()
        self.login( email=regular_user1.email )
        # check if the request's state is now set to 'complete'
        self.check_request_grid(state='Complete', request_name=request_one.name)
        assert request_one.state is not request_one.states.COMPLETE, "The state of the request '%s' should be set to '%s'" \
            % ( request_one.name, request_one.states.COMPLETE )
    def test_045_admin_create_request_on_behalf_of_regular_user( self ):
        """Testing creating and submitting a request as an admin on behalf of a regular user"""
        self.logout()
        self.login( email=admin_user.email )
        name = "RequestTwo"
        # TODO: fix this test so it is no longer simulated.
        # simulate request creation
        url_str = '%s/requests_common/new?cntrller=requests_admin&create_request_button=Save&select_request_type=%i&select_user=%i&name=%s&refresh=True&field_2=%s&field_0=%s&field_1=%i' \
                  % ( self.url, request_type1.id, regular_user1.id, name, "field_2_value", 'option1', user_address1.id )
        self.home()
        self.visit_url( url_str )
        self.check_page_for_string( "The new request named <b>%s</b> has been created" % name )
        global request_two
        request_two = get_request_by_name( name )      
        # check if the request is showing in the 'new' filter
        self.check_request_admin_grid(state=request_two.states.NEW, request_name=request_two.name)
        # check if the request's state is now set to 'new'
        assert request_two.state is not request_two.states.NEW, "The state of the request '%s' should be set to '%s'" \
            % ( request_two.name, request_two.states.NEW )
        # sample fields
        samples = [ ( 'Sample One', [ 'S1 Field 0 Value' ] ),
                    ( 'Sample Two', [ 'S2 Field 0 Value' ] ) ]
        # add samples to this request
        self.add_samples( request_two.id, request_two.name, samples )
        # submit the request
        self.submit_request_as_admin( request_two.id, request_two.name )
        refresh( request_two )
        # check if the request is showing in the 'submitted' filter
        self.check_request_admin_grid(state=request_two.states.SUBMITTED, request_name=request_two.name)
        # check if the request's state is now set to 'submitted'
        assert request_two.state is not request_two.states.SUBMITTED, "The state of the request '%s' should be set to '%s'" \
            % ( request_two.name, request_two.states.SUBMITTED )
        # check if both the requests is showing in the 'All' filter
        self.check_request_admin_grid(state='All', request_name=request_one.name)
        self.check_request_admin_grid(state='All', request_name=request_two.name)
    def test_050_reject_request( self ):
        '''Testing rejecting a request'''
        self.logout()
        self.login( email=admin_user.email )
        self.reject_request( request_two.id, request_two.name, "Rejection test comment" )
        refresh( request_two )
        # check if the request is showing in the 'rejected' filter
        self.check_request_admin_grid(state=request_two.states.REJECTED, request_name=request_two.name)
        # check if the request's state is now set to 'submitted'
        assert request_two.state is not request_two.states.REJECTED, "The state of the request '%s' should be set to '%s'" \
            % ( request_two.name, request_two.states.REJECTED )
    def test_055_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to pass"""
        # Logged in as admin_user
        ##################
        # Delete request_type permissions
        ##################
        for request_type in [ request_type1 ]:
            delete_request_type_permissions( request_type.id )
        ##################
        # Mark all request_types deleted
        ##################
        for request_type in [ request_type1 ]:
            mark_obj_deleted( request_type )
        ##################
        # Mark all requests deleted
        ##################
        for request in [ request_one, request_two ]:
            mark_obj_deleted( request )
        ##################
        # Mark all forms deleted
        ##################
        for form in [ form_one, form_two ]:
            self.mark_form_deleted( self.security.encode_id( form.current.id ) )
        ##################
        # Mark all user_addresses deleted
        ##################
        for user_address in [ user_address1 ]:
            mark_obj_deleted( user_address )
        ##################
        # Purge all libraries
        ##################
        for library in [ library_one ]:
            self.delete_library_item( 'library_admin',
                                      self.security.encode_id( library.id ),
                                      self.security.encode_id( library.id ),
                                      library.name,
                                      item_type='library' )
            self.purge_library( self.security.encode_id( library.id ), library.name )
        ##################
        # Delete all non-private roles
        ##################
        for role in [ role_one, role_two ]:
            self.mark_role_deleted( self.security.encode_id( role.id ), role.name )
            self.purge_role( self.security.encode_id( role.id ), role.name )
            # Manually delete the role from the database
            refresh( role )
            delete( role )
        ##################
        # Delete all groups
        ##################
        for group in [ group_one ]:
            self.mark_group_deleted( self.security.encode_id( group.id ), group.name )
            self.purge_group( self.security.encode_id( group.id ), group.name )
            # Manually delete the group from the database
            refresh( group )
            delete( group )
