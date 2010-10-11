import galaxy.model
from galaxy.model.orm import *
from base.twilltestcase import *
from base.test_db_util import *

sample_states = [  ( 'New', 'Sample entered into the system' ), 
                   ( 'Received', 'Sample tube received' ), 
                   ( 'Done', 'Sequence run complete' ) ]
address_dict = dict( short_desc="Office",
                     name="James Bond",
                     institution="MI6" ,
                     address="MI6 Headquarters",
                     city="London",
                     state="London",
                     postal_code="007",
                     country="United Kingdom",
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
    def test_010_create_request_form( self ):
        """Testing creating a request form definition, editing the name and description and adding fields"""
        # Logged in as admin_user
        # Create a form definition
        tmp_name = "Temp form"
        tmp_desc = "Temp form description"
        form_type = galaxy.model.FormDefinition.types.REQUEST
        self.create_form( name=tmp_name,
                          desc=tmp_desc,
                          form_type=form_type,
                          num_fields=0,
                          strings_displayed=[ 'Create a new form definition' ],
                          strings_displayed_after_submit=[ tmp_name, tmp_desc, form_type ] )
        tmp_form = get_form( tmp_name )
        # Edit the name and description of the form definition, and add 3 fields.
        new_name = "Request Form"
        new_desc = "Request Form description"
        global test_field_name1
        test_field_name1 = 'Test field name one'
        global test_field_name2
        test_field_name2 = 'Test field name two'
        global test_field_name3
        test_field_name3 = 'Test field name three'
        field_dicts = [ dict( name=test_field_name1,
                             desc='Test field description one',
                             type='SelectField',
                             required='optional',
                             selectlist=[ 'option1', 'option2' ] ),
                        dict( name=test_field_name2,
                              desc='Test field description two',
                              type='AddressField',
                              required='optional' ),
                        dict( name=test_field_name3,
                              desc='Test field description three',
                              type='TextField',
                              required='required' ) ]
        self.edit_form( id=self.security.encode_id( tmp_form.current.id ),
                        new_form_name=new_name,
                        new_form_desc=new_desc,
                        field_dicts=field_dicts,
                        field_index=len( tmp_form.fields ),
                        strings_displayed=[ 'Edit form definition "%s"' % tmp_name ],
                        strings_displayed_after_submit=[ "The form '%s' has been updated with the changes." % new_name ] )
        # Get the form_definition object for later tests
        global form_one
        form_one = get_form( new_name )
        assert form_one is not None, 'Problem retrieving form named "%s" from the database' % new_name
        assert len( form_one.fields ) == len( tmp_form.fields ) + len( field_dicts )
    def test_015_create_sample_form( self ):
        """Testing creating sample form definition"""
        name = "Sample Form"
        desc = "This is Form Two's description"
        form_type = galaxy.model.FormDefinition.types.SAMPLE
        form_layout_name = 'Layout Grid One'
        self.create_form( name=name,
                          desc=desc,
                          form_type=form_type,
                          form_layout_name=form_layout_name,
                          strings_displayed=[ 'Create a new form definition' ],
                          strings_displayed_after_submit=[ "The form '%s' has been updated with the changes." % name ] )
        global form_two
        form_two = get_form( name )
        assert form_two is not None, "Error retrieving form %s from db" % name
    def test_020_create_request_type( self ):
        """Testing creating a request_type"""
        request_form = get_form( form_one.name )
        sample_form = get_form( form_two.name )
        name = 'Test Requestype'
        self.create_request_type( name,
                                  "test sequencer configuration",
                                  str( request_form.id ),
                                  str( sample_form.id ),
                                  sample_states,
                                  strings_displayed=[ 'Create a new sequencer configuration' ],
                                  strings_displayed_after_submit=[ "Sequencer configuration <b>%s</b> has been created" % name ] )
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
        self.visit_url( '%s/requests_common/create_request?cntrller=requests&request_type=True' % self.url )
        try:
            self.check_page_for_string( 'There are no sequencer configurations created for a new request.' )
            raise AssertionError, 'The request_type %s is accessible by %s when it should be restricted' % ( request_type1.name, regular_user2.email )
        except:
            pass
        self.logout()
        self.login( email=admin_user.email )
    def test_025_create_request( self ):
        """Testing creating a sequence run request"""
        # logged in as admin_user
        # Create a user_address
        self.logout()
        self.login( email=regular_user1.email )
        self.add_user_address( regular_user1.id, address_dict )
        global user_address1
        user_address1 = get_user_address( regular_user1, address_dict[ 'short_desc' ] )
        # Set field values - the tuples in the field_values list include the field_value, and True if refresh_on_change
        # is required for that field.
        field_value_tuples = [ ( 'option1', False ), ( str( user_address1.id ), True ), ( 'field three value', False ) ] 
        # Create the request
        name = 'Request One'
        desc = 'Request One Description'
        self.create_request( cntrller='requests',
                             request_type_id=self.security.encode_id( request_type1.id ),
                             name=name,
                             desc=desc,
                             field_value_tuples=field_value_tuples,
                             strings_displayed=[ 'Create a new request',
                                                 test_field_name1,
                                                 test_field_name2,
                                                 test_field_name3 ],
                             strings_displayed_after_submit=[ name, desc ] )
        global request_one
        request_one = get_request_by_name( name )        
        # Make sure the request's state is now set to NEW
        assert request_one.state is not request_one.states.NEW, "The state of the request '%s' should be set to '%s'" \
            % ( request_one.name, request_one.states.NEW )
        # Sample fields - the tuple represents a sample name and a list of sample form field values
        sample_value_tuples = [ ( 'Sample One', [ 'S1 Field 0 Value' ] ),
                                ( 'Sample Two', [ 'S2 Field 0 Value' ] ) ]
        strings_displayed_after_submit = [ 'Unsubmitted' ]
        for sample_name, field_values in sample_value_tuples:
            strings_displayed_after_submit.append( sample_name )
            for field_value in field_values:
                strings_displayed_after_submit.append( field_value )
        # Add samples to the request
        self.add_samples( cntrller='requests',
                          request_id=self.security.encode_id( request_one.id ),
                          request_name=request_one.name,
                          sample_value_tuples=sample_value_tuples,
                          strings_displayed=[ 'Sequencing Request "%s"' % request_one.name,
                                              'There are no samples.' ],
                          strings_displayed_after_submit=strings_displayed_after_submit )
    def test_030_edit_basic_request_info( self ):
        """Testing editing the basic information of a sequence run request"""
        # logged in as regular_user1
        fields = [ 'option2', str( user_address1.id ), 'field three value (edited)' ]
        new_name=request_one.name + ' (Renamed)'
        new_desc=request_one.desc + ' (Re-described)'
        self.edit_basic_request_info( request_id=self.security.encode_id( request_one.id ),
                                      cntrller='requests',
                                      name=request_one.name,
                                      new_name=new_name, 
                                      new_desc=new_desc,
                                      new_fields=fields,
                                      strings_displayed=[ 'Edit sequencing request "%s"' % request_one.name ],
                                      strings_displayed_after_submit=[ new_name, new_desc ] )
        refresh( request_one )
        # check if the request is showing in the 'new' filter
        self.check_request_grid( cntrller='requests',
                                 state=request_one.states.NEW,
                                 strings_displayed=[ request_one.name ] )
    def test_035_submit_request( self ):
        """Testing editing a sequence run request"""
        # logged in as regular_user1
        self.submit_request( cntrller='requests',
                             request_id=self.security.encode_id( request_one.id ),
                             request_name=request_one.name,
                             strings_displayed_after_submit=[ 'The request has been submitted.' ] )
        refresh( request_one )
        # Make sure the request is showing in the 'submitted' filter
        self.check_request_grid( cntrller='requests',
                                 state=request_one.states.SUBMITTED,
                                 strings_displayed=[ request_one.name ] )
        # Make sure the request's state is now set to 'submitted'
        assert request_one.state is not request_one.states.SUBMITTED, "The state of the request '%s' should be set to '%s'" \
            % ( request_one.name, request_one.states.SUBMITTED )
    def test_040_request_lifecycle( self ):
        """Testing request life-cycle as it goes through all the states"""
        # logged in as regular_user1
        """
        TODO: debug this test case...
        self.logout()
        self.login( email=admin_user.email )
        self.check_request_grid( cntrller='requests_admin',
                                 state=request_one.states.SUBMITTED,
                                 strings_displayed=[ request_one.name ] )
        self.visit_url( "%s/requests_common/manage_request?cntrller=requests&id=%s" % ( self.url, self.security.encode_id( request_one.id ) ) )
        self.check_page_for_string( 'Sequencing Request "%s"' % request_one.name )
        # Set bar codes for the samples
        bar_codes = [ '1234567890', '0987654321' ]
        strings_displayed_after_submit=[ 'Changes made to the samples are saved.' ]
        for bar_code in bar_codes:
            strings_displayed_after_submit.append( bar_code )
        self.add_bar_codes( request_id=self.security.encode_id( request_one.id ),
                            request_name=request_one.name,
                            bar_codes=bar_codes,
                            samples=request_one.samples,
                            strings_displayed_after_submit=strings_displayed_after_submit )
        # Change the states of all the samples of this request to ultimately be COMPLETE
        for sample in request_one.samples:
            self.change_sample_state( request_id=self.security.encode_id( request_one.id ),
                                      request_name=request_one.name,
                                      sample_name=sample.name,
                                      sample_id=self.security.encode_id( sample.id ),
                                      new_sample_state_id=request_type1.states[1].id,
                                      new_state_name=request_type1.states[1].name )
            self.change_sample_state( request_id=self.security.encode_id( request_one.id ),
                                      request_name=request_one.name,
                                      sample_name=sample.name,
                                      sample_id=self.security.encode_id( sample.id ),
                                      new_sample_state_id=request_type1.states[2].id,
                                      new_state_name=request_type1.states[2].name )
        refresh( request_one )
        self.logout()
        self.login( email=regular_user1.email )
        # check if the request's state is now set to 'complete'
        self.check_request_grid( cntrller='requests',
                                 state='Complete',
                                 strings_displayed=[ request_one.name ] )
        assert request_one.state is not request_one.states.COMPLETE, "The state of the request '%s' should be set to '%s'" \
            % ( request_one.name, request_one.states.COMPLETE )
        """
    def test_045_admin_create_request_on_behalf_of_regular_user( self ):
        """Testing creating and submitting a request as an admin on behalf of a regular user"""
        # Logged in as regular_user1
        self.logout()
        self.login( email=admin_user.email )
        # Create the request
        name = "RequestTwo"
        desc = 'Request Two Description'
        # Set field values - the tuples in the field_values list include the field_value, and True if refresh_on_change
        # is required for that field.
        field_value_tuples = [ ( 'option2', False ), ( str( user_address1.id ), True ), ( 'field_2_value', False ) ] 
        self.create_request( cntrller='requests_admin',
                             request_type_id=self.security.encode_id( request_type1.id ),
                             other_users_id=self.security.encode_id( regular_user1.id ),
                             name=name,
                             desc=desc,
                             field_value_tuples=field_value_tuples,
                             strings_displayed=[ 'Create a new request',
                                                 test_field_name1,
                                                 test_field_name2,
                                                 test_field_name3 ],
                             strings_displayed_after_submit=[ "The request has been created" ] )
        global request_two
        request_two = get_request_by_name( name )      
        # Make sure the request is showing in the 'new' filter
        self.check_request_grid( cntrller='requests_admin',
                                 state=request_two.states.NEW,
                                 strings_displayed=[ request_two.name ] )
        # Make sure the request's state is now set to 'new'
        assert request_two.state is not request_two.states.NEW, "The state of the request '%s' should be set to '%s'" \
            % ( request_two.name, request_two.states.NEW )
        # Sample fields - the tuple represents a sample name and a list of sample form field values
        sample_value_tuples = [ ( 'Sample One', [ 'S1 Field 0 Value' ] ),
                                ( 'Sample Two', [ 'S2 Field 0 Value' ] ) ]
        strings_displayed_after_submit = [ 'Unsubmitted' ]
        for sample_name, field_values in sample_value_tuples:
            strings_displayed_after_submit.append( sample_name )
            for field_value in field_values:
                strings_displayed_after_submit.append( field_value )
        # Add samples to the request
        self.add_samples( cntrller='requests_admin',
                          request_id=self.security.encode_id( request_two.id ),
                          request_name=request_two.name,
                          sample_value_tuples=sample_value_tuples,
                          strings_displayed=[ 'Sequencing Request "%s"' % request_two.name,
                                              'There are no samples.' ],
                          strings_displayed_after_submit=strings_displayed_after_submit )
        # Submit the request
        self.submit_request( cntrller='requests_admin',
                             request_id=self.security.encode_id( request_two.id ),
                             request_name=request_two.name,
                             strings_displayed_after_submit=[ 'The request has been submitted.' ] )
        refresh( request_two )
        # Make sure the request is showing in the 'submitted' filter
        self.check_request_grid( cntrller='requests_admin',
                                 state=request_two.states.SUBMITTED,
                                 strings_displayed=[ request_two.name ] )
        # Make sure the request's state is now set to 'submitted'
        assert request_two.state is not request_two.states.SUBMITTED, "The state of the request '%s' should be set to '%s'" \
            % ( request_two.name, request_two.states.SUBMITTED )
        # Make sure both requests are showing in the 'All' filter
        self.check_request_grid( cntrller='requests_admin',
                                 state='All',
                                 strings_displayed=[ request_one.name, request_two.name ] )
    def test_050_reject_request( self ):
        """Testing rejecting a request"""
        # Logged in as admin_user
        self.reject_request( request_id=self.security.encode_id( request_two.id ),
                             request_name=request_two.name,
                             comment="Rejection test comment",
                             strings_displayed=[ 'Reject Sequencing Request "%s"' % request_two.name ],
                             strings_displayed_after_submit=[ 'Request (%s) has been rejected.' % request_two.name ] )
        refresh( request_two )
        # Make sure the request is showing in the 'rejected' filter
        self.check_request_grid( cntrller='requests_admin',
                                 state=request_two.states.REJECTED,
                                 strings_displayed=[ request_two.name ] )
        # Make sure the request's state is now set to REJECTED
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
