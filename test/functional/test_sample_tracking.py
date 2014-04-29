import galaxy.model
from galaxy.model.orm import *
from base.twilltestcase import *
from base.test_db_util import *


class TestFormsAndSampleTracking( TwillTestCase ):
    # ====== Setup Users, Groups & Roles required for this test suite ========= 

    def test_0000_initiate_users( self ):
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

    def test_0005_create_required_groups_and_roles( self ):
        """Testing creating all required groups and roles for this script"""
        # Logged in as admin_user
        # Create role1
        name = 'Role1'
        description = "This is Role1's description"
        user_ids = [ str( admin_user.id ), str( regular_user1.id ), str( regular_user3.id ) ]
        self.create_role( name=name,
                          description=description,
                          in_user_ids=user_ids,
                          in_group_ids=[],
                          create_group_for_role='no',
                          private_role=admin_user.email )
        # Get the role object for later tests
        global role1
        role1 = get_role_by_name( name )
        # Create group1
        name = 'Group1'
        self.create_group( name=name, in_user_ids=[ str( regular_user1.id ) ], in_role_ids=[ str( role1.id ) ] )
        # Get the group object for later tests
        global group1
        group1 = get_group_by_name( name )
        assert group1 is not None, 'Problem retrieving group named "Group1" from the database'
        # NOTE: To get this to work with twill, all select lists on the ~/admin/role page must contain at least
        # 1 option value or twill throws an exception, which is: ParseError: OPTION outside of SELECT
        # Due to this bug in twill, we create the role, we bypass the page and visit the URL in the
        # associate_users_and_groups_with_role() method.
        #
        #create role2
        name = 'Role2'
        description = 'This is Role2'
        user_ids = [ str( admin_user.id ) ]
        group_ids = [ str( group1.id ) ]
        private_role = admin_user.email
        self.create_role( name=name,
                          description=description,
                          in_user_ids=user_ids,
                          in_group_ids=group_ids,
                          private_role=private_role )
        # Get the role object for later tests
        global role2
        role2 = get_role_by_name( name )
        assert role2 is not None, 'Problem retrieving role named "Role2" from the database'

    def test_0010_create_library( self ):
        """Testing creating the target data library and folder"""
        # Logged in as admin_user
        for index in range( 0, 2 ):
            name = 'library%s' % str( index + 1 )
            description = '%s description' % name
            synopsis = '%s synopsis' % name
            self.create_library( name=name, description=description, synopsis=synopsis )
        # Get the libraries for later use
        global library1
        library1 = get_library( 'library1', 'library1 description', 'library1 synopsis' )
        assert library1 is not None, 'Problem retrieving library (library1) from the database'
        global library2
        library2 = get_library( 'library2', 'library2 description', 'library2 synopsis' )
        assert library2 is not None, 'Problem retrieving library (library2) from the database'
        # setup add_library_item permission to regular_user1
        # Set permissions on the library, sort for later testing.
        permissions_in = [ 'LIBRARY_ACCESS' ]
        permissions_out = []
        # Role1 members are: admin_user, regular_user1, regular_user3.  
        # Each of these users will be permitted for LIBRARY_ACCESS, LIBRARY_ADD on 
        # library1 and library2.
        for library in [ library1, library2 ]:
            self.library_permissions( self.security.encode_id( library.id ),
                                      library.name,
                                      str( role1.id ),
                                      permissions_in,
                                      permissions_out )

    def test_0015_create_folders( self ):
        # adding a folder
        for library in [ library1, library2 ]:
            name = "%s_folder1" % library.name
            description = "%s description" % name
            self.add_folder( 'library_admin',
                             self.security.encode_id( library.id ),
                             self.security.encode_id( library.root_folder.id ),
                             name=name,
                             description=description )
        global library1_folder1
        library1_folder1 = get_folder( library1.root_folder.id, 'library1_folder1', 'library1_folder1 description' )
        assert library1_folder1 is not None, 'Problem retrieving library folder named "library1_folder1" from the database'
        global library2_folder1
        library2_folder1 = get_folder( library2.root_folder.id, 'library2_folder1', 'library2_folder1 description' )
        assert library2_folder1 is not None, 'Problem retrieving library folder named "library2_folder1" from the database'
        # add folders 4 levels deep to library1_folder1
        # level 2
        name = "%s_folder2" % library2.name
        description = "%s description" % name
        self.add_folder( 'library_admin',
                         self.security.encode_id( library2.id ),
                         self.security.encode_id( library2_folder1.id ),
                         name=name,
                         description=description )
        global library2_folder2
        library2_folder2 = get_folder( library2_folder1.id, name, description )
        assert library2_folder2 is not None, 'Problem retrieving library folder named "%s" from the database' % name
        # level 3
        name = "%s_folder3" % library2.name
        description = "%s description" % name
        self.add_folder( 'library_admin',
                         self.security.encode_id( library2.id ),
                         self.security.encode_id( library2_folder2.id ),
                         name=name,
                         description=description )
        global library2_folder3
        library2_folder3 = get_folder( library2_folder2.id, name, description )
        assert library2_folder3 is not None, 'Problem retrieving library folder named "%s" from the database' % name
        # level 4
        name = "%s_folder4" % library2.name
        description = "%s description" % name
        self.add_folder( 'library_admin',
                         self.security.encode_id( library2.id ),
                         self.security.encode_id( library2_folder3.id ),
                         name=name,
                         description=description )
        global library2_folder4
        library2_folder4 = get_folder( library2_folder3.id, name, description )
        assert library2_folder4 is not None, 'Problem retrieving library folder named "%s" from the database' % name
        
    #
    # ====== Form definition test methods ================================================ 
    #

    def test_0020_create_request_form_definition( self ):
        """Testing creating a sequencing request form definition, editing the name and description and adding fields"""
        # Logged in as admin_user
        # Create a form definition
        tmp_name = "Temp form"
        tmp_desc = "Temp form description"
        form_type = galaxy.model.FormDefinition.types.REQUEST
        self.create_form( name=tmp_name,
                          description=tmp_desc,
                          form_type=form_type,
                          num_fields=0,
                          field_name='1_field_name',
                          strings_displayed=[ 'Create a new form definition' ],
                          strings_displayed_after_submit=[ tmp_name, tmp_desc, form_type ] )

    def test_0025_edit_request_form_fields( self ):
        # field names
        tmp_name = "Temp form"
        tmp_form = get_form( tmp_name )
        # Edit the name and description of the form definition, and add 3 fields.
        new_name = "Request Form"
        new_desc = "Request Form description"
        form_type = galaxy.model.FormDefinition.types.REQUEST
        # labels
        global request_field_label1
        request_field_label1 = 'Request form field1'
        global request_field_label2
        request_field_label2 = 'Request form field2'
        global request_field_label3
        request_field_label3 = 'Request form field3'
        global request_form_field_name1
        request_form_field_name1 = 'request_form_field1'
        global request_form_field_name2
        request_form_field_name2 = 'request_form_field2'
        global request_form_field_name3
        request_form_field_name3 = 'request_form_field3'
        field_dicts = [ dict( label=request_field_label1,
                              desc='Description of '+request_field_label1,
                              type='SelectField',
                              required='optional',
                              selectlist=[ 'option1', 'option2' ],
                              name=request_form_field_name1 ),
                        dict( label=request_field_label2,
                              desc='Description of '+request_field_label2,
                              type='AddressField',
                              required='optional',
                              name=request_form_field_name2 ),
                        dict( label=request_field_label3,
                              desc='Description of '+request_field_label3,
                              type='TextField',
                              required='required',
                              name=request_form_field_name3 ) ]
        self.edit_form( id=self.security.encode_id( tmp_form.current.id ),
                        new_form_name=new_name,
                        new_form_desc=new_desc,
                        field_dicts=field_dicts,
                        field_index=len( tmp_form.fields ),
                        strings_displayed=[ 'Edit form definition "%s"' % tmp_name ],
                        strings_displayed_after_submit=[ "The form '%s' has been updated with the changes." % new_name ] )
        # Get the form_definition object for later tests
        global request_form_definition1
        request_form_definition1 = get_form( new_name )
        assert request_form_definition1 is not None, 'Problem retrieving form named "%s" from the database' % new_name
        assert len( request_form_definition1.fields ) == len( tmp_form.fields ) + len( field_dicts )
        # check form view
        self.view_form( id=self.security.encode_id( request_form_definition1.current.id ),
                        form_name=new_name,
                        form_desc=new_desc,
                        form_type=form_type,
                        field_dicts=field_dicts )

    def test_0030_create_sample_form_definition( self ):
        """Testing creating sequencing sample form definition and adding fields"""
        name = "Sample Form"
        desc = "This is Sample Form's description"
        form_type = galaxy.model.FormDefinition.types.SAMPLE
        global sample_form_layout_grid_name
        sample_form_layout_grid_name = 'Layout Grid1'
        self.create_form( name=name,
                          description=desc,
                          form_type=form_type,
                          form_layout_name=sample_form_layout_grid_name,
                          num_fields=0,
                          field_name='1_field_name',
                          strings_displayed=[ 'Create a new form definition' ],
                          strings_displayed_after_submit=[ "The form '%s' has been updated with the changes." % name ] )

    def test_0035_add_fields_to_sample_form( self ):
        # now add fields to the sample form definition
        name = "Sample Form"
        desc = "This is Sample Form's description"
        form_type = galaxy.model.FormDefinition.types.SAMPLE
        tmp_form = get_form( name )
        global sample_field_label1
        sample_field_label1 = 'Sample form field1'
        global sample_field_label2
        sample_field_label2 = 'Sample form field2'
        global sample_field_label3
        sample_field_label3 = 'Sample form field3'
        field_dicts = [ dict( label=sample_field_label1,
                              desc='Description of '+sample_field_label1,
                              type='SelectField',
                              required='optional',
                              selectlist=[ 'option1', 'option2' ],
                              name='sample_form_field1' ),
                        dict( label=sample_field_label2,
                              desc='Description of '+sample_field_label2,
                              type='TextField',
                              required='optional',
                              name='sample_form_field2' ),
                        dict( label=sample_field_label3,
                              desc='Description of '+sample_field_label3,
                              type='TextField',
                              required='required',
                              name='sample_form_field3' ) ]
        self.edit_form( id=self.security.encode_id( tmp_form.current.id ),
                        new_form_name=name,
                        new_form_desc=desc,
                        field_dicts=field_dicts,
                        field_index=len( tmp_form.fields ),
                        strings_displayed=[ 'Edit form definition "%s"' % name ],
                        strings_displayed_after_submit=[ "The form '%s' has been updated with the changes." % name ] )
        global sample_form_definition1
        sample_form_definition1 = get_form( name )
        assert sample_form_definition1 is not None, "Error retrieving form %s from db" % name
        assert len( sample_form_definition1.fields ) == len( field_dicts )
        # check form view
        self.view_form( id=self.security.encode_id( sample_form_definition1.current.id ),
                        form_name=name,
                        form_desc=desc,
                        form_type=form_type,
                        form_layout_name=sample_form_layout_grid_name,
                        field_dicts=field_dicts )

    def test_0040_create_request_type( self ):
        """Testing creating a request_type"""
        name = 'Request type1'
        sample_states = [  ( 'New', 'Sample entered into the system' ), 
                           ( 'Received', 'Sample tube received' ),
                           ( 'Library Started', 'Sample library preparation' ), 
                           ( 'Run Started', 'Sequence run in progress' ), 
                           ( 'Done', 'Sequence run complete' ) ]
        self.create_request_type( name,
                                  name+" description",
                                  self.security.encode_id( request_form_definition1.id ),
                                  self.security.encode_id( sample_form_definition1.id ),
                                  sample_states,
                                  strings_displayed=[ 'Create a new request type' ],
                                  strings_displayed_after_submit=[ "The request type has been created." ] )
        global request_type1
        request_type1 = get_request_type_by_name( name )
        assert request_type1 is not None, 'Problem retrieving request type named "%s" from the database' % name
        # check view
        self.view_request_type( self.security.encode_id( request_type1.id ),
                                request_type1.name,
                                strings_displayed=[ request_form_definition1.name,
                                                    sample_form_definition1.name ],
                                sample_states=sample_states)

    def test_0045_set_request_type_permissions( self ):
        # Role1 members are: admin_user, regular_user1, regular_user3.  Each of these users will be permitted for
        # REQUEST_TYPE_ACCESS on this request_type
        permissions_in = [ k for k, v in galaxy.model.RequestType.permitted_actions.items() ]
        permissions_out = []
        self.request_type_permissions( self.security.encode_id( request_type1.id ),
                                       request_type1.name,
                                       str( role1.id ),
                                       permissions_in,
                                       permissions_out )
        # Make sure the request_type1 is not accessible by regular_user2 since regular_user2 does not have Role1.
        self.logout()
        self.login( email=regular_user2.email )
        self.visit_url( '%s/requests_common/create_request?cntrller=requests&request_type=True' % self.url )
        try:
            self.check_page_for_string( 'There are no request types created for a new request.' )
            raise AssertionError, 'The request_type %s is accessible by %s when it should be restricted' % ( request_type1.name, regular_user2.email )
        except:
            pass
        self.logout()
        self.login( email=admin_user.email )
    # ====== Sequencing request test methods - regular user perspective ================ 

    def test_0050_create_request( self ):
        """Testing creating a sequencing request as a regular user"""
        # logged in as admin_user
        # Create a user_address
        self.logout()
        self.login( email=regular_user1.email )
        # add new address for this user
        address_dict = dict( short_desc="Office",
                             name="James Bond",
                             institution="MI6" ,
                             address="MI6 Headquarters",
                             city="London",
                             state="London",
                             postal_code="007",
                             country="United Kingdom",
                             phone="007-007-0007" )
        self.add_user_address( self.security.encode_id( regular_user1.id ), address_dict )
        global user_address1
        user_address1 = get_user_address( regular_user1, address_dict[ 'short_desc' ] )
        # Set field values - the tuples in the field_values list include the field_value, and True if refresh_on_change
        # is required for that field.
        field_value_tuples = [ ( request_form_field_name1, 'option1', False ), 
                               ( request_form_field_name2, ( str( user_address1.id ), str( user_address1.id ) ), True ), 
                               ( request_form_field_name3, 'field3 value', False ) ] 
        # Create the request
        name = 'Request1'
        desc = 'Request1 Description'
        self.create_request( cntrller='requests',
                             request_type_id=self.security.encode_id( request_type1.id ),
                             name=name,
                             desc=desc,
                             field_value_tuples=field_value_tuples,
                             strings_displayed=[ 'Create a new sequencing request',
                                                 request_field_label1,
                                                 request_field_label2,
                                                 request_field_label3 ],
                             strings_displayed_after_submit=[ 'The sequencing request has been created.',
                                                              name, desc ] )
        global request1
        request1 = get_request_by_name( name )

    def test_0055_verify_request_details( self ):
        # Make sure the request's state is now set to NEW
        assert request1.state is not request1.states.NEW, "The state of the request '%s' should be set to '%s'" \
            % ( request1.name, request1.states.NEW )
        # check request page
        self.view_request( cntrller='requests',
                           request_id=self.security.encode_id( request1.id ),
                           strings_displayed=[ 'Sequencing request "%s"' % request1.name,
                                               'There are no samples.' ],
                           strings_not_displayed=[ request1.states.SUBMITTED,
                                                   request1.states.COMPLETE,
                                                   request1.states.REJECTED,
                                                   'Submit request' ] ) # this button should NOT show up as there are no samples yet
        # check if the request is showing in the 'new' filter
        self.check_request_grid( cntrller='requests',
                                 state=request1.states.NEW,
                                 strings_displayed=[ request1.name ] )
        self.view_request_history( cntrller='requests',
                                   request_id=self.security.encode_id( request1.id ),
                                   strings_displayed=[ 'History of sequencing request "%s"' % request1.name,
                                                       request1.states.NEW,
                                                       'Sequencing request created' ],
                                   strings_not_displayed=[ request1.states.SUBMITTED,
                                                           request1.states.COMPLETE,
                                                           request1.states.REJECTED ] )

    def test_0060_edit_basic_request_info( self ):
        """Testing editing the basic information and email settings of a sequencing request"""
        # logged in as regular_user1
        fields = [ ( request_form_field_name1, 'option2' ), 
                   ( request_form_field_name2, str( user_address1.id ) ), 
                   ( request_form_field_name3, 'field3 value (edited)' ) ]
        new_name=request1.name + ' (Renamed)'
        new_desc=request1.desc + ' (Re-described)'
        self.edit_basic_request_info( request_id=self.security.encode_id( request1.id ),
                                      cntrller='requests',
                                      name=request1.name,
                                      new_name=new_name, 
                                      new_desc=new_desc,
                                      new_fields=fields,
                                      strings_displayed=[ 'Edit sequencing request "%s"' % request1.name ],
                                      strings_displayed_after_submit=[ new_name, new_desc ] )
        refresh( request1 )
        # define the sample states when we want an email notification
        global email_notification_sample_states
        email_notification_sample_states = [ request1.type.states[2], request1.type.states[4] ] 
        # check email notification settings
        check_sample_states = []
        for state in email_notification_sample_states:
            check_sample_states.append( ( state.name, state.id, True ) )
        strings_displayed = [ 'Edit sequencing request "%s"' % request1.name,
                              'Email notification settings' ]
        additional_emails = [ 'test@.bx.psu.edu', 'test2@.bx.psu.edu' ]
        strings_displayed_after_submit = [ "The changes made to the email notification settings have been saved",
                                           '\r\n'.join( additional_emails ) ]
        self.edit_request_email_settings( cntrller='requests', 
                                          request_id=self.security.encode_id( request1.id ), 
                                          check_request_owner=True, 
                                          additional_emails='\r\n'.join( additional_emails ), 
                                          check_sample_states=check_sample_states, 
                                          strings_displayed=strings_displayed, 
                                          strings_displayed_after_submit=strings_displayed_after_submit )
        # lastly check the details in the request page
        strings_displayed = [ 'Sequencing request "%s"' % new_name,
                              new_desc ]
        for field in fields:
            strings_displayed.append( field[1] )        
        for state_name, id, is_checked in check_sample_states:
            strings_displayed.append( state_name )
        for email in additional_emails:
            strings_displayed.append( email )
        self.view_request( cntrller='requests',
                           request_id=self.security.encode_id( request1.id ),
                           strings_displayed=strings_displayed,
                           strings_not_displayed=[] )

    def test_0065_add_samples_to_request( self ):
        """Testing adding samples to request"""
        # logged in as regular_user1
        # Sample fields - the tuple represents a sample name and a list of sample form field values
        target_library_info = dict(library=self.security.encode_id(library2.id), 
                                   folder=self.security.encode_id(library2_folder1.id) )
        sample_value_tuples = \
        [ ( 'Sample1', target_library_info, [ 'option1', 'sample1 field2 value', 'sample1 field3 value' ] ),
          ( 'Sample2', target_library_info, [ 'option2', 'sample2 field2 value', 'sample2 field3 value' ] ),
          ( 'Sample3', target_library_info, [ 'option1', 'sample3 field2 value', 'sample3 field3 value' ] ) ]
        strings_displayed_after_submit = [ 'Unsubmitted' ]
        for sample_name, lib_info, field_values in sample_value_tuples:
            strings_displayed_after_submit.append( sample_name )
            strings_displayed_after_submit.append( library2.name )
            strings_displayed_after_submit.append( library2_folder1.name )
            # add the sample values too
            for values in field_values:
                strings_displayed_after_submit.append( values )
        # list folders that populates folder selectfield when a data library is selected
        folder_options = [ library2_folder1.name, library2_folder2.name, library2_folder3.name, library2_folder4.name ]        # Add samples to the request
        self.add_samples( cntrller='requests',
                          request_id=self.security.encode_id( request1.id ),
                          sample_value_tuples=sample_value_tuples,
                          folder_options=folder_options,
                          strings_displayed=[ 'Add samples to sequencing request "%s"' % request1.name,
                                              '<input type="text" name="sample_0_name" value="Sample_1" size="10"/>' ], # sample name input field
                          strings_displayed_after_submit=strings_displayed_after_submit )
        # check the new sample field values on the request page
        strings_displayed = [ 'Sequencing request "%s"' % request1.name,
                              'Submit request' ] # this button should appear now
        strings_displayed.extend( strings_displayed_after_submit )
        strings_displayed_count = []
        strings_displayed_count.append( ( library2.name, len( sample_value_tuples ) ) )
        strings_displayed_count.append( ( library2_folder1.name, len( sample_value_tuples ) ) )
        self.view_request( cntrller='requests',
                           request_id=self.security.encode_id( request1.id ),
                           strings_displayed=strings_displayed,
                           strings_displayed_count=strings_displayed_count )

    def test_0070_edit_samples_of_new_request( self ):
        """Testing editing the sample information of new request1"""
        # logged in as regular_user1
        # target data library - change it to library1
        target_library_info = dict(library=self.security.encode_id( library1.id ), 
                                   folder=self.security.encode_id( library1_folder1.id ) )
        new_sample_value_tuples = \
        [ ( 'Sample1_renamed', target_library_info, [ 'option2', 'sample1 field2 value edited', 'sample1 field3 value edited' ] ),
          ( 'Sample2_renamed', target_library_info, [ 'option1', 'sample2 field2 value edited', 'sample2 field3 value edited' ] ),
          ( 'Sample3_renamed', target_library_info, [ 'option2', 'sample3 field2 value edited', 'sample3 field3 value edited' ] ) ]
        strings_displayed_after_submit = [ 'Unsubmitted' ]
        for sample_name, lib_info, field_values in new_sample_value_tuples:
            strings_displayed_after_submit.append( sample_name )
            # add the sample values too
            for values in field_values:
                strings_displayed_after_submit.append( values )
        strings_displayed = [ 'Edit Current Samples of Sequencing Request "%s"' % request1.name,
                              '<input type="text" name="sample_0_name" value="Sample1" size="10"/>', # sample name input field
                              library2_folder1.name, # all the folders in library2 should show up in the folder selectlist 
                              library2_folder2.name, 
                              library2_folder3.name, 
                              library2_folder4.name ]
        # Add samples to the request
        self.edit_samples( cntrller='requests',
                           request_id=self.security.encode_id( request1.id ),
                           sample_value_tuples=new_sample_value_tuples,
                           strings_displayed=strings_displayed,
                           strings_displayed_after_submit=strings_displayed_after_submit )
        # check the changed sample field values on the request page
        strings_displayed = [ 'Sequencing request "%s"' % request1.name ]
        strings_displayed.extend( strings_displayed_after_submit )
        strings_displayed_count = []
        strings_displayed_count.append( ( library1.name, len( new_sample_value_tuples ) ) )
        strings_displayed_count.append( ( library1_folder1.name, len( new_sample_value_tuples ) ) )
        self.view_request( cntrller='requests',
                           request_id=self.security.encode_id( request1.id ),
                           strings_displayed=strings_displayed,
                           strings_displayed_count=strings_displayed_count )

    def test_0075_submit_request( self ):
        """Testing submitting a sequencing request"""
        # logged in as regular_user1
        self.submit_request( cntrller='requests',
                             request_id=self.security.encode_id( request1.id ),
                             request_name=request1.name,
                             strings_displayed_after_submit=[ 'The sequencing request has been submitted.' ] )
        refresh( request1 )
        # Make sure the request is showing in the 'submitted' filter
        self.check_request_grid( cntrller='requests',
                                 state=request1.states.SUBMITTED,
                                 strings_displayed=[ request1.name ] )
        # Make sure the request's state is now set to 'submitted'
        assert request1.state is not request1.states.SUBMITTED, "The state of the sequencing request '%s' should be set to '%s'" \
            % ( request1.name, request1.states.SUBMITTED )
        # the sample state should appear once for each sample
        strings_displayed_count = [ ( request1.type.states[0].name, len( request1.samples ) ) ]
        # after submission, these buttons should not appear 
        strings_not_displayed = [ 'Add sample', 'Submit request' ]
        # check the request page
        self.view_request( cntrller='requests',
                           request_id=self.security.encode_id( request1.id ),
                           strings_displayed=[ request1.states.SUBMITTED ],
                           strings_displayed_count=strings_displayed_count,
                           strings_not_displayed=strings_not_displayed )
        strings_displayed=[ 'History of sequencing request "%s"' % request1.name,
                            'Sequencing request submitted by %s' % regular_user1.email,
                            'Sequencing request created' ]
        strings_displayed_count = [ ( request1.states.SUBMITTED, 1 ) ]
        self.view_request_history( cntrller='requests',
                                   request_id=self.security.encode_id( request1.id ),
                                   strings_displayed=strings_displayed,
                                   strings_displayed_count=strings_displayed_count,
                                   strings_not_displayed=[ request1.states.COMPLETE,
                                                           request1.states.REJECTED ] )
    # ====== Sequencing request test methods - Admin perspective ================ 

    def test_0080_receive_request_as_admin( self ):
        """Testing receiving a sequencing request and assigning it barcodes"""
        # logged in as regular_user1
        self.logout()
        # login as a admin_user to assign bar codes to samples
        self.login( email=admin_user.email )
        self.check_request_grid( cntrller='requests_admin',
                                 state=request1.states.SUBMITTED,
                                 strings_displayed=[ request1.name ] )
        strings_displayed = [ request1.states.SUBMITTED,
                              'Reject this request',
                              'Add sample',
                              'Edit samples' ]
        self.view_request( cntrller='requests_admin',
                           request_id=self.security.encode_id( request1.id ),
                           strings_displayed=strings_displayed )

    def test_0085_add_bar_codes( self ):
        # Set bar codes for the samples
        bar_codes = [ '10001', '10002', '10003' ]
        strings_displayed_after_submit = [ 'Changes made to the samples have been saved.' ]
        strings_displayed_after_submit.extend( bar_codes )
        self.add_bar_codes( cntrller='requests_admin',
                            request_id=self.security.encode_id( request1.id ),
                            bar_codes=bar_codes,
                            strings_displayed=[ 'Edit Current Samples of Sequencing Request "%s"' % request1.name ],
                            strings_displayed_after_submit=strings_displayed_after_submit )
        # the second sample state should appear once for each sample
        strings_displayed_count = [ ( request1.type.states[1].name, len( request1.samples ) ),
                                    ( request1.type.states[0].name, 0 ) ]        
        # check the request page
        self.view_request( cntrller='requests_admin',
                           request_id=self.security.encode_id( request1.id ),
                           strings_displayed=bar_codes,
                           strings_displayed_count=strings_displayed_count )
        # the sample state descriptions of the future states should not appear
        # here the state names are not checked as all of them appear at the top of
        # the page like: state1 > state2 > state3
        strings_not_displayed=[ request1.type.states[2].desc,
                                request1.type.states[3].desc,
                                request1.type.states[4].desc ]
        # check history of each sample
        for sample in request1.samples:
            strings_displayed = [ 'History of sample "%s"' % sample.name,
                                  'Sequencing request submitted and sample state set to %s' % request1.type.states[0].name,
                                   request1.type.states[0].name,
                                   request1.type.states[1].name ]
            self.view_sample_history( cntrller='requests_admin',
                                      sample_id=self.security.encode_id( sample.id ),
                                      strings_displayed=strings_displayed,
                                      strings_not_displayed=strings_not_displayed )

    def test_0090_request_lifecycle( self ):
        """Testing request life-cycle as it goes through all the states"""
        # logged in as admin_user
        self.check_request_grid( cntrller='requests_admin',
                                 state=request1.states.SUBMITTED,
                                 strings_displayed=[ request1.name ] )
        strings_displayed=[ 'History of sequencing request "%s"' % request1.name ]
        # Change the states of all the samples of this request to ultimately be COMPLETE
        for index, state in enumerate( request_type1.states ):
            # start from the second state onwards
            if index > 1:
                # status message
                if index == len( request_type1.states ) - 1:
                    status_msg = 'All samples of this sequencing request are in the final sample state (%s).' % state.name
                else:
                    status_msg = 'All samples of this sequencing request are in the (%s) sample state. ' % state.name 
                # check email notification message
                email_msg = ''
                if state.id in [ email_state.id for email_state in email_notification_sample_states ]:
                    email_msg = 'Email notification failed as SMTP server not set in config file'
                self.change_sample_state( request_id=self.security.encode_id( request1.id ),
                                          sample_ids=[ sample.id for sample in request1.samples ],
                                          new_sample_state_id=self.security.encode_id( state.id ),
                                          strings_displayed=[ 'Edit Current Samples of Sequencing Request "%s"' % request1.name ],
                                          strings_displayed_after_submit = [ status_msg, email_msg ] )
                # check request history page
                if index == len( request_type1.states ) - 1:
                    strings_displayed.append( status_msg )
                else:
                    strings_displayed.append( status_msg )
                self.view_request_history( cntrller='requests_admin',
                                           request_id=self.security.encode_id( request1.id ),
                                           strings_displayed=strings_displayed,
                                           strings_not_displayed=[ request1.states.REJECTED ] )
        refresh( request1 )
        # check if the request's state is now set to 'complete'
        self.check_request_grid( cntrller='requests_admin',
                                 state='Complete',
                                 strings_displayed=[ request1.name ] )
        assert request1.state is not request1.states.COMPLETE, "The state of the sequencing request '%s' should be set to '%s'" \
            % ( request1.name, request1.states.COMPLETE )

    def test_0095_admin_create_request_on_behalf_of_regular_user( self ):
        """Testing creating and submitting a request as an admin on behalf of a regular user"""
        # Logged in as regular_user1
        self.logout()
        self.login( email=admin_user.email )
        # Create the request
        name = "Request2"
        desc = 'Request2 Description'
        # new address
        new_address_dict = dict( short_desc="Home",
                                 name="Sherlock Holmes",
                                 institution="None" ,
                                 address="221B Baker Street",
                                 city="London",
                                 state="London",
                                 postal_code="34534",
                                 country="United Kingdom",
                                 phone="007-007-0007" )
        # Set field values - the tuples in the field_values list include the field_value, and True if refresh_on_change
        # is required for that field.
        field_value_tuples = [ ( request_form_field_name1, 'option2', False ), 
                               ( request_form_field_name2, ( 'new', new_address_dict ) , True ), 
                               ( request_form_field_name3, 'field_2_value', False ) ] 
        self.create_request( cntrller='requests_admin',
                             request_type_id=self.security.encode_id( request_type1.id ),
                             other_users_id=self.security.encode_id( regular_user1.id ),
                             name=name,
                             desc=desc,
                             field_value_tuples=field_value_tuples,
                             strings_displayed=[ 'Create a new sequencing request',
                                                 request_field_label1,
                                                 request_field_label2,
                                                 request_field_label3 ],
                             strings_displayed_after_submit=[ "The sequencing request has been created.",
                                                              name, desc ] )
        global request2
        request2 = get_request_by_name( name )
        global user_address2
        user_address2 = get_user_address( regular_user1, new_address_dict[ 'short_desc' ] )
        # Make sure the request is showing in the 'new' filter
        self.check_request_grid( cntrller='requests_admin',
                                 state=request2.states.NEW,
                                 strings_displayed=[ request2.name ] )
        # Make sure the request's state is now set to 'new'
        assert request2.state is not request2.states.NEW, "The state of the request '%s' should be set to '%s'" \
            % ( request2.name, request2.states.NEW )

    def test_0100_add_samples_to_request( self ):
        target_library_info = dict( library=None, folder=None )
        # Sample fields - the tuple represents a sample name and a list of sample form field values
        sample_value_tuples = \
        [ ( 'Sample1', target_library_info, [ 'option1', 'sample1 field2 value', 'sample1 field3 value' ] ),
          ( 'Sample2', target_library_info, [ 'option2', 'sample2 field2 value', 'sample2 field3 value' ] ),
          ( 'Sample3', target_library_info, [ 'option1', 'sample3 field2 value', 'sample3 field3 value' ] ) ]
        strings_displayed_after_submit = [ 'Unsubmitted' ]
        for sample_name, lib_info, field_values in sample_value_tuples:
            strings_displayed_after_submit.append( sample_name )
            for values in field_values:
                strings_displayed_after_submit.append( values )
        # Add samples to the request
        self.add_samples( cntrller='requests_admin',
                          request_id=self.security.encode_id( request2.id ),
                          sample_value_tuples=sample_value_tuples,
                          strings_displayed=[ 'Add samples to sequencing request "%s"' % request2.name,
                                              '<input type="text" name="sample_0_name" value="Sample_1" size="10"/>' ], # sample name input field
                          strings_displayed_after_submit=strings_displayed_after_submit )
        # Submit the request
        self.submit_request( cntrller='requests_admin',
                             request_id=self.security.encode_id( request2.id ),
                             request_name=request2.name,
                             strings_displayed_after_submit=[ 'The sequencing request has been submitted.' ] )
        refresh( request2 )
        # Make sure the request is showing in the 'submitted' filter
        self.check_request_grid( cntrller='requests_admin',
                                 state=request2.states.SUBMITTED,
                                 strings_displayed=[ request2.name ] )
        # Make sure the request's state is now set to 'submitted'
        assert request2.state is not request2.states.SUBMITTED, "The state of the sequencing request '%s' should be set to '%s'" \
            % ( request2.name, request2.states.SUBMITTED )
        # Make sure both requests are showing in the 'All' filter
        self.check_request_grid( cntrller='requests_admin',
                                 state='All',
                                 strings_displayed=[ request1.name, request2.name ] )

    def test_0105_set_request_target_library( self ):
        # list folders that populates folder selectfield when a data library is selected
        folder_options = [ library2_folder1.name, library2_folder2.name, library2_folder3.name, library2_folder4.name ]
        # set the target data library to library2 using sample operation user interface
        self.change_sample_target_data_library( cntrller='requests',
                                                request_id=self.security.encode_id( request2.id ),
                                                sample_ids=[ sample.id for sample in request2.samples ],
                                                new_library_id=self.security.encode_id( library2.id ), 
                                                new_folder_id=self.security.encode_id( library2_folder1.id ),
                                                folder_options=folder_options,
                                                strings_displayed=[ 'Edit Current Samples of Sequencing Request "%s"' % request2.name ],
                                                strings_displayed_after_submit=[ 'Changes made to the samples have been saved.' ] )
        # check the changed target data library & folder on the request page
        strings_displayed_count = []
        strings_displayed_count.append( ( library2.name, len( request1.samples ) ) )
        strings_displayed_count.append( ( library2_folder1.name, len( request1.samples ) ) )
        strings_displayed = [ 'Sequencing request "%s"' % request2.name, regular_user1.email, request2.states.SUBMITTED ]
        select_target_library_message = "Select a target data library and folder for a sample before selecting its datasets to transfer from the external service"
        self.view_request( cntrller='requests',
                           request_id=self.security.encode_id( request2.id ),
                           strings_displayed=strings_displayed,
                           strings_not_displayed=[ select_target_library_message ],
                           strings_displayed_count=strings_displayed_count )

    def test_0110_reject_request( self ):
        """Testing rejecting a request"""
        # Logged in as admin_user
        rejection_reason="This is why the sequencing request was rejected."
        self.reject_request( request_id=self.security.encode_id( request2.id ),
                             request_name=request2.name,
                             comment=rejection_reason,
                             strings_displayed=[ 'Reject sequencing request "%s"' % request2.name ],
                             strings_displayed_after_submit=[ 'Sequencing request (%s) has been rejected.' % request2.name ] )
        refresh( request2 )
        # Make sure the request is showing in the 'rejected' filter
        self.check_request_grid( cntrller='requests_admin',
                                 state=request2.states.REJECTED,
                                 strings_displayed=[ request2.name ] )
        # Make sure the request's state is now set to REJECTED
        assert request2.state is not request2.states.REJECTED, "The state of the request '%s' should be set to '%s'" \
            % ( request2.name, request2.states.REJECTED )
        # The rejection reason should show up in the request page and the request history page
        rejection_message = 'Sequencing request marked rejected by %s. Reason: %s' % ( admin_user.email, rejection_reason )
        strings_displayed = [ request2.states.REJECTED, 
                              rejection_message ]
        self.view_request( cntrller='requests',
                           request_id=self.security.encode_id( request2.id ),
                           strings_displayed=strings_displayed )
        self.view_request_history( cntrller='requests',
                                   request_id=self.security.encode_id( request2.id ),
                                   strings_displayed=strings_displayed )
        # login as the regular user to make sure that the request2 is fully editable
        self.logout()
        self.login( email=regular_user1.email )
        strings_displayed=[ 'Sequencing request "%s"' % request2.name,
                            request1.states.REJECTED,
                            rejection_message ]
        visible_buttons = [ 'Add sample', 'Edit samples', 'Submit request' ]
        strings_displayed.extend( visible_buttons )
        self.view_request( cntrller='requests',
                           request_id=self.security.encode_id( request2.id ),
                           strings_displayed=strings_displayed,
                           strings_not_displayed=[ request1.states.SUBMITTED,
                                                   request1.states.COMPLETE,
                                                   request1.states.NEW] )

    def __test_0115_select_datasets_for_transfer( self ):
        """Testing selecting datasets for data transfer"""
        # Logged in as admin_user
        self.logout()
        self.login( email=admin_user.email )
        # Setup the dummy datasets for sample1 of request1
        sample_datasets = [ '/path/to/sample1_dataset1', 
                            '/path/to/sample1_dataset2',
                            '/path/to/sample1_dataset3' ] 
        sample_dataset_file_names = [ dataset.split( '/' )[-1] for dataset in sample_datasets ]
        global request1_sample1
        request1_sample1 = request1.get_sample( 'Sample1_renamed' )
        external_service = request1_sample1.external_service
        strings_displayed_after_submit = [ 'Datasets (%s) have been selected for sample (%s)' % \
                                           ( str( sample_dataset_file_names )[1:-1].replace( "'", "" ), request1_sample1.name ) ]
        strings_displayed = [ 'Select datasets to transfer from data directory configured for the sequencer' ]
        self.add_datasets_to_sample( request_id=self.security.encode_id( request2.id ),
                                     sample_id= self.security.encode_id( request1_sample1.id ),
                                     external_service_id=self.security.encode_id( external_serviceexternal_service.id ),
                                     sample_datasets=sample_datasets,
                                     strings_displayed=strings_displayed,
                                     strings_displayed_after_submit=strings_displayed_after_submit )
        assert len( request1_sample1.datasets ) == len( sample_datasets )
        # check the sample dataset info page
        for sample1_dataset in request1_sample1.datasets:
            strings_displayed = [ '"%s" Dataset' % request1_sample1.name,
                                  sample1_dataset.file_path,
                                  sample1_dataset.transfer_status.NOT_STARTED ]
            self.view_sample_dataset( sample_dataset_id=self.security.encode_id( sample1_dataset.id ),
                                      strings_displayed=strings_displayed )

    def __test_0120_manage_sample_datasets( self ):
        """Testing renaming, deleting and initiating transfer of sample datasets"""
        # Logged in as admin_user
        # Check renaming datasets
        new_sample_dataset_names = [ ( 'path', request1_sample1.datasets[0].name ), 
                                     ( 'to', request1_sample1.datasets[1].name+'/renamed' ),
                                     ( 'none', request1_sample1.datasets[2].name+'_renamed' ) ] 
        sample_dataset_ids = [ self.security.encode_id( dataset.id ) for dataset in request1_sample1.datasets ]
        strings_displayed = [ 'Rename datasets for Sample "%s"' % request1_sample1.name ]
        strings_displayed_after_submit = [ 'Changes saved successfully.' ]
        strings_displayed_after_submit.extend( [ new_name for prefix, new_name in new_sample_dataset_names ] )
        self.rename_sample_datasets( sample_id=self.security.encode_id( request1_sample1.id ),
                                     sample_dataset_ids=sample_dataset_ids,
                                     new_sample_dataset_names=new_sample_dataset_names,
                                     strings_displayed=strings_displayed )
        # Check deletion
        sample_dataset_ids = [ self.security.encode_id( request1_sample1.datasets[0].id ) ]
        strings_displayed = [ 'Manage "%s" datasets' % request1_sample1.name ]
        strings_displayed_after_submit = [ '%i datasets have been deleted.' % len( sample_dataset_ids ) ]
        strings_not_displayed = [ request1_sample1.datasets[0].name ]
        self.delete_sample_datasets( sample_id=self.security.encode_id( request1_sample1.id ),
                                     sample_dataset_ids=sample_dataset_ids,
                                     strings_displayed=strings_displayed,
                                     strings_displayed_after_submit=strings_displayed_after_submit,
                                     strings_not_displayed=strings_not_displayed )
        refresh( request1_sample1 )
        assert len( request1_sample1.datasets ) == ( len( new_sample_dataset_names )-1 )
        # Check data transfer
        # In this test we only test transfer initiation. For data transfer to complete 
        # successfully we need RabbitMQ setup. Since that is not possible in the functional 
        # tests framework, this checks if correct error message is displayed and the transfer 
        # status of the sample datasets remains at 'Not started' when the Transfer button is clicked.
        sample_dataset_ids = [ self.security.encode_id( dataset.id ) for dataset in request1_sample1.datasets ]
        strings_displayed = [ 'Manage "%s" datasets' % request1_sample1.name ]
        strings_displayed_count = [ ( galaxy.model.SampleDataset.transfer_status.NOT_STARTED, len( request1_sample1.datasets ) ) ]
        strings_displayed_after_submit = [ "Error in sequencer login information. Please set your API Key in your User Preferences to transfer datasets." ]
        strings_not_displayed = [ galaxy.model.SampleDataset.transfer_status.IN_QUEUE,
                                  galaxy.model.SampleDataset.transfer_status.TRANSFERRING,
                                  galaxy.model.SampleDataset.transfer_status.ADD_TO_LIBRARY,
                                  galaxy.model.SampleDataset.transfer_status.COMPLETE ]
        self.start_sample_datasets_transfer( sample_id=self.security.encode_id( request1_sample1.id ),
                                             sample_dataset_ids=sample_dataset_ids,
                                             strings_displayed=strings_displayed,
                                             strings_displayed_after_submit=strings_displayed_after_submit,
                                             strings_not_displayed=strings_not_displayed,
                                             strings_displayed_count=strings_displayed_count )
        # check the sample dataset info page
        for sample1_dataset in request1_sample1.datasets:
            strings_displayed = [ '"%s" Dataset' % request1_sample1.name,
                                  sample1_dataset.file_path,
                                  sample1_dataset.transfer_status.NOT_STARTED ]
            self.view_sample_dataset( sample_dataset_id=self.security.encode_id( sample1_dataset.id ),
                                      strings_displayed=strings_displayed )

    def test_999_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to pass"""
        # Logged in as admin_user
        self.logout()
        self.login( email=admin_user.email )
        ##################
        # Purge all libraries
        ##################
        for library in [ library1, library2 ]:
            self.delete_library_item( 'library_admin',
                                      self.security.encode_id( library.id ),
                                      self.security.encode_id( library.id ),
                                      library.name,
                                      item_type='library' )
            self.purge_library( self.security.encode_id( library.id ), library.name )             
        ##################
        # Mark all requests deleted and delete all their samples
        ##################
        for request in [ request1, request2 ]:
            # delete samples
            for sample in request.samples:
                # delete sample datasets
                for sample_dataset in sample.datasets:
                    delete_obj( sample_dataset )
                delete_obj( sample )
            mark_obj_deleted( request )
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
        # Mark all forms deleted
        ##################
        for form in [ request_form_definition1, sample_form_definition1 ]:
            self.mark_form_deleted( self.security.encode_id( form.current.id ) )
        ##################
        # Mark all user_addresses deleted
        ##################
        for user_address in [ user_address1, user_address2 ]:
            mark_obj_deleted( user_address )
        ##################
        # Delete all non-private roles
        ##################
        for role in [ role1, role2 ]:
            self.mark_role_deleted( self.security.encode_id( role.id ), role.name )
            self.purge_role( self.security.encode_id( role.id ), role.name )
            # Manually delete the role from the database
            refresh( role )
            delete_obj( role )
        ##################
        # Delete all groups
        ##################
        for group in [ group1 ]:
            self.mark_group_deleted( self.security.encode_id( group.id ), group.name )
            self.purge_group( self.security.encode_id( group.id ), group.name )
            # Manually delete the group from the database
            refresh( group )
            delete_obj( group )
