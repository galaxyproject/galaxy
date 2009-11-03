import galaxy.model
from galaxy.model.orm import *
from galaxy.model.mapping import context as sa_session
from base.twilltestcase import *

not_logged_in_as_admin_security_msg = 'You must be logged in as an administrator to access this feature.'
logged_in_as_admin_security_msg = 'You must be an administrator to access this feature.'
not_logged_in_security_msg = 'You must be logged in to create/submit sequencing requests'
form_one_name = "Request Form"
form_two_name = "Sample Form"
request_type_name = 'Test Requestype'
sample_states = [  ( 'New', 'Sample entered into the system' ), 
                   ( 'Received', 'Sample tube received' ), 
                   ( 'Done', 'Sequence run complete' ) ]
address1 = dict(  short_desc="Office",
                  name="James+Bond",
                  institution="MI6" ,
                  address1="MI6+Headquarters",
                  address2="",
                  city="London",
                  state="London",
                  postal_code="007",
                  country="United+Kingdom",
                  phone="007-007-0007" )


def get_latest_form(form_name):
    fdc_list = sa_session.query( galaxy.model.FormDefinitionCurrent ) \
                         .filter( galaxy.model.FormDefinitionCurrent.table.c.deleted==False ) \
                         .order_by( galaxy.model.FormDefinitionCurrent.table.c.create_time.desc() )
    for fdc in fdc_list:
        sa_session.refresh( fdc.latest_form )
        if form_name == fdc.latest_form.name:
            return fdc.latest_form
    return None


class TestFormsAndRequests( TwillTestCase ):
    def test_000_create_form( self ):
        """Testing creating a new form and editing it"""
        self.logout()
        self.login( email='test@bx.psu.edu' )
        # create a form
        global form_one_name
        desc = "This is Form One's description"
        formtype = galaxy.model.FormDefinition.types.REQUEST
        self.create_form( name=form_one_name, desc=desc, formtype=formtype, num_fields=0 )
        # Get the form_definition object for later tests
        form_one = get_latest_form(form_one_name)
        assert form_one is not None, 'Problem retrieving form named "%s" from the database' % name
        # edit form & add few more fields
        new_name = "Request Form (Renamed)"
        new_desc = "This is Form One's Re-described"
        self.edit_form( form_one.id, form_one.name, new_form_name=new_name, new_form_desc=new_desc )
        self.home()
        self.visit_page( 'forms/manage' )
        self.check_page_for_string( new_name )
        self.check_page_for_string( new_desc )
        form_one_name = new_name
    def test_005_add_form_fields( self ):
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
        form_one = get_latest_form(form_one_name)
        self.form_add_field(form_one.id, form_one.name, form_one.desc, form_one.type, field_index=len(form_one.fields), fields=fields)
        form_one_latest = get_latest_form(form_one_name)        
        assert len(form_one_latest.fields) == len(form_one.fields)+len(fields)
    def test_015_create_sample_form( self ):
        """Testing creating another form (for samples)"""
        global form_two_name
        desc = "This is Form One's description"
        formtype = 'Sequencing Sample Form'
        self.create_form( name=form_two_name, desc=desc, formtype=formtype )
        self.home()
        self.visit_page( 'forms/manage' )
        self.check_page_for_string( form_two_name )
        self.check_page_for_string( desc )
        self.check_page_for_string( formtype )
    def test_020_create_request_type( self ):
        """Testing creating a new requestype"""
        request_form = get_latest_form(form_one_name)
        sample_form = get_latest_form(form_two_name)
        self.create_request_type(request_type_name, "test request type", 
                                 str(request_form.id), str(sample_form.id), sample_states )
        global request_type
        request_type = sa_session.query( galaxy.model.RequestType ) \
                                 .filter( and_( galaxy.model.RequestType.table.c.name==request_type_name ) ) \
                                 .order_by( desc( galaxy.model.RequestType.table.c.create_time ) ) \
                                 .first()
        assert request_type is not None, 'Problem retrieving request type named "%s" from the database' % request_type_name
    def test_025_create_address_and_library( self ):
        """Testing address & library creation"""
        # first create a regular user
        self.logout()
        self.login( email='test1@bx.psu.edu' )
        self.logout()
        self.login( email='test@bx.psu.edu' )
        # first create a library for the request so that it can be submitted later
        lib_name = 'TestLib001'
        self.create_library( lib_name, '' )
        self.visit_page( 'library_admin/browse_libraries' )
        self.check_page_for_string( lib_name )
        # Get the library object for later tests
        global library_one
        library_one = sa_session.query( galaxy.model.Library ) \
                                .filter( and_( galaxy.model.Library.table.c.name==lib_name,
                                               galaxy.model.Library.table.c.deleted==False ) ) \
                                .first()
        assert library_one is not None, 'Problem retrieving library named "%s" from the database' % lib_name
        global admin_user
        admin_user = sa_session.query( galaxy.model.User ) \
                               .filter( galaxy.model.User.table.c.email=='test@bx.psu.edu' ) \
                               .first()
        assert admin_user is not None, 'Problem retrieving user with email "test@bx.psu.edu" from the database'
        # Get the admin user's private role for later use
        global admin_user_private_role
        admin_user_private_role = None
        for role in admin_user.all_roles():
            if role.name == admin_user.email and role.description == 'Private Role for %s' % admin_user.email:
                admin_user_private_role = role
                break
        if not admin_user_private_role:
            raise AssertionError( "Private role not found for user '%s'" % admin_user.email )
        global regular_user1
        regular_user1 = sa_session.query( galaxy.model.User ) \
                                  .filter( galaxy.model.User.table.c.email=='test1@bx.psu.edu' ) \
                                  .first()
        assert regular_user1 is not None, 'Problem retrieving user with email "test1@bx.psu.edu" from the database'
        # Get the regular user's private role for later use
        global regular_user1_private_role
        regular_user1_private_role = None
        for role in regular_user1.all_roles():
            if role.name == regular_user1.email and role.description == 'Private Role for %s' % regular_user1.email:
                regular_user1_private_role = role
                break
        if not regular_user1_private_role:
            raise AssertionError( "Private role not found for user '%s'" % regular_user1.email )
        # Set permissions on the library, sort for later testing
        permissions_in = [ k for k, v in galaxy.model.Library.permitted_actions.items() ]
        permissions_out = []
        # Role one members are: admin_user, regular_user1.  Each of these users will be permitted to
        # LIBRARY_ADD, LIBRARY_MODIFY, LIBRARY_MANAGE for library items.
        self.set_library_permissions( str( library_one.id ), library_one.name, str( regular_user1_private_role.id ), permissions_in, permissions_out )
        # create a folder in the library
        root_folder = library_one.root_folder
        name = "Folder One"
        self.add_folder( 'library_admin', str( library_one.id ), str( root_folder.id ), name=name, description='' )
        global folder_one
        folder_one = sa_session.query( galaxy.model.LibraryFolder ) \
                               .filter( and_( galaxy.model.LibraryFolder.table.c.parent_id==root_folder.id,
                                              galaxy.model.LibraryFolder.table.c.name==name ) ) \
                               .first()
        assert folder_one is not None, 'Problem retrieving library folder named "%s" from the database' % name
        self.home()
        self.visit_url( '%s/library_admin/browse_library?obj_id=%s' % ( self.url, str( library_one.id ) ) )
        self.check_page_for_string( name )
        # create address
        self.logout()
        self.login( email='test1@bx.psu.edu' )
        self.home()
        url_str = '%s/user/new_address?short_desc=%s&name=%s&institution=%s&address1=%s&address2=%s&city=%s&state=%s&postal_code=%s&country=%s&phone=%s' \
                   % ( self.url, address1[ 'short_desc' ], address1[ 'name' ], address1[ 'institution' ], 
                       address1[ 'address1' ], address1[ 'address2' ], address1[ 'city' ], address1[ 'state' ], 
                       address1[ 'postal_code' ], address1[ 'country' ], address1[ 'phone' ] )
        self.visit_url( url_str )
        self.check_page_for_string( 'Address <b>%s</b> has been added' % address1[ 'short_desc' ] )
        global regular_user
        regular_user = sa_session.query( galaxy.model.User ) \
                                 .filter( galaxy.model.User.table.c.email=='test1@bx.psu.edu' ) \
                                 .first()
        global user_address
        user_address = sa_session.query( galaxy.model.UserAddress ) \
                                 .filter( and_( galaxy.model.UserAddress.table.c.desc==address1[ 'short_desc' ],
                                                galaxy.model.UserAddress.table.c.deleted==False ) ) \
                                 .first()    
    def test_030_create_request( self ):
        """Testing creating, editing and submitting a request as a regular user"""
        # login as a regular user
        self.logout()
        self.login( email='test1@bx.psu.edu' )
        # set field values
        fields = ['option1', str(user_address.id), 'field three value'] 
        # create the request
        request_name, request_desc = 'Request One', 'Request One Description'
        self.create_request(request_type.id, request_name, request_desc, library_one.id, 'none', fields)
        global request_one
        request_one = sa_session.query( galaxy.model.Request ) \
                                .filter( and_( galaxy.model.Request.table.c.name==request_name,
                                               galaxy.model.Request.table.c.deleted==False ) ) \
                                .first()        
        # check if the request's state is now set to 'unsubmitted'
        assert request_one.state is not request_one.states.UNSUBMITTED, "The state of the request '%s' should be set to '%s'" \
            % ( request_one.name, request_one.states.UNSUBMITTED )
        # sample fields
        samples = [ ( 'Sample One', [ 'S1 Field 0 Value' ] ),
                    ( 'Sample Two', [ 'S2 Field 0 Value' ] ) ]
        # add samples to this request
        self.add_samples( request_one.id, request_one.name, samples )
        # edit this request
        fields = ['option2', str(user_address.id), 'field three value (edited)'] 
        self.edit_request(request_one.id, request_one.name, request_one.name+' (Renamed)', 
                          request_one.desc+' (Re-described)', library_one.id, folder_one.id, fields)
        sa_session.refresh( request_one )
        # check if the request is showing in the 'unsubmitted' filter
        self.home()
        self.visit_url( '%s/requests/list?show_filter=Unsubmitted' % self.url )
        self.check_page_for_string( request_one.name )
        # submit the request
        self.submit_request( request_one.id, request_one.name )
        sa_session.refresh( request_one )
        # check if the request is showing in the 'submitted' filter
        self.home()
        self.visit_url( '%s/requests/list?show_filter=Submitted' % self.url )
        self.check_page_for_string( request_one.name )
        # check if the request's state is now set to 'submitted'
        assert request_one.state is not request_one.states.SUBMITTED, "The state of the request '%s' should be set to '%s'" \
            % ( request_one.name, request_one.states.SUBMITTED )
    def test_035_request_lifecycle( self ):
        """Testing request lifecycle as it goes through all the states"""
        # goto admin manage requests page
        self.logout()
        self.login( email='test@bx.psu.edu' )
        self.home()
        self.visit_page( 'requests_admin/list' )
        self.check_page_for_string( request_one.name )
        self.visit_url( "%s/requests_admin/list?sort=-create_time&operation=show_request&id=%s" \
                        % ( self.url, self.security.encode_id( request_one.id ) ))
        self.check_page_for_string( 'Sequencing Request "%s"' % request_one.name )
        # set bar codes for the samples
        bar_codes = [ '1234567890', '0987654321' ]
        self.add_bar_codes( request_one.id, request_one.name, bar_codes )
        # change the states of all the samples of this request
        for sample in request_one.samples:
            self.change_sample_state( sample.name, sample.id, request_type.states[1].id, request_type.states[1].name )
            self.change_sample_state( sample.name, sample.id, request_type.states[2].id, request_type.states[2].name )
        self.home()
        sa_session.refresh( request_one )
        # check if the request's state is now set to 'complete'
        self.visit_url('%s/requests_admin/list?show_filter=Complete' % self.url)
        self.check_page_for_string( request_one.name )
        assert request_one.state is not request_one.states.COMPLETE, "The state of the request '%s' should be set to '%s'" \
            % ( request_one.name, request_one.states.COMPLETE )
    def test_40_admin_create_request_on_behalf_of_regular_user( self ):
        """Testing creating and submitting a request as an admin on behalf of a regular user"""
        self.logout()
        self.login( email='test@bx.psu.edu' )
        request_name = "RequestTwo"
        # simulate request creation
        url_str = '%s/requests_admin/new?create=True&create_request_button=Save&select_request_type=%i&select_user=%i&name=%s&library_id=%i&folder_id=%i&refresh=True&field_2=%s&field_0=%s&field_1=%i' \
                  % ( self.url, request_type.id, regular_user.id, request_name, library_one.id, library_one.root_folder.id, "field_2_value", 'option1', user_address.id )
        self.home()
        self.visit_url( url_str )
        self.check_page_for_string( "The new request named %s has been created" % request_name )
        global request_two
        request_two = sa_session.query( galaxy.model.Request ) \
                                .filter( and_( galaxy.model.Request.table.c.name==request_name,
                                               galaxy.model.Request.table.c.deleted==False ) ) \
                                .first()        
        # check if the request is showing in the 'unsubmitted' filter
        self.home()
        self.visit_url( '%s/requests_admin/list?show_filter=Unsubmitted' % self.url )
        self.check_page_for_string( request_two.name )
        # check if the request's state is now set to 'unsubmitted'
        assert request_two.state is not request_two.states.UNSUBMITTED, "The state of the request '%s' should be set to '%s'" \
            % ( request_two.name, request_two.states.UNSUBMITTED )
        # sample fields
        samples = [ ( 'Sample One', [ 'S1 Field 0 Value' ] ),
                    ( 'Sample Two', [ 'S2 Field 0 Value' ] ) ]
        # add samples to this request
        self.add_samples( request_two.id, request_two.name, samples )
        # submit the request
        self.submit_request( request_two.id, request_two.name )
        sa_session.refresh( request_two )
        # check if the request is showing in the 'submitted' filter
        self.home()
        self.visit_url( '%s/requests_admin/list?show_filter=Submitted' % self.url )
        self.check_page_for_string( request_two.name )
        # check if the request's state is now set to 'submitted'
        assert request_two.state is not request_two.states.SUBMITTED, "The state of the request '%s' should be set to '%s'" \
            % ( request_two.name, request_two.states.SUBMITTED )
        # check if both the requests is showing in the 'All' filter
        self.home()
        self.visit_url( '%s/requests_admin/list?show_filter=All' % self.url )
        self.check_page_for_string( request_one.name )
        self.check_page_for_string( request_two.name )
