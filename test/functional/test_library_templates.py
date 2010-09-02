from base.twilltestcase import *
from base.test_db_util import *

class TestLibraryFeatures( TwillTestCase ):
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
    def test_005_create_library_templates( self ):
        """Testing creating several LibraryInformationTemplate form definitions"""
        # Logged in as admin_user
        for type in [ 'AddressField', 'CheckboxField', 'SelectField', 'TextArea', 'TextField', 'WorkflowField' ]:
            form_desc = '%s description' % type
            # Create form for library template
            self.create_single_field_type_form_definition( name=type,
                                                           desc=form_desc,
                                                           formtype=galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE,
                                                           field_type=type )
        # Get all of the new form definitions for later use
        global AddressField_form
        AddressField_form = get_form( 'AddressField' )
        global CheckboxField_form
        CheckboxField_form = get_form( 'CheckboxField' )
        global SelectField_form
        SelectField_form = get_form( 'SelectField' )
        global TextArea_form
        TextArea_form = get_form( 'TextArea' )
        global TextField_form
        TextField_form = get_form( 'TextField' )
        global WorkflowField_form
        WorkflowField_form = get_form( 'WorkflowField' )
    def test_010_create_libraries( self ):
        """Testing creating a new library for each template"""
        # Logged in as admin_user
        for index, form in enumerate( [ AddressField_form, CheckboxField_form, SelectField_form, TextArea_form, TextField_form, WorkflowField_form ] ):
            name = 'library%s' % str( index + 1 )
            description = '%s description' % name
            synopsis = '%s synopsis' % name
            self.create_library( name=name, description=description, synopsis=synopsis )
        # Get the libraries for later use
        global library1
        library1 = get_library( 'library1', 'library1 description', 'library1 synopsis' )
        global library2
        library2 = get_library( 'library2', 'library2 description', 'library2 synopsis' )
        global library3
        library3 = get_library( 'library3', 'library3 description', 'library3 synopsis' )
        global library4
        library4 = get_library( 'library4', 'library4 description', 'library4 synopsis' )
        global library5
        library5 = get_library( 'library5', 'library5 description', 'library5 synopsis' )
        global library6
        library6 = get_library( 'library6', 'library6 description', 'library6 synopsis' )
    def test_015_add_template_to_library1( self ):
        """Testing add an inheritable template containing an AddressField to library1"""
        # Logged in as admin_user
        # Add a template to library1
        self.add_library_template( 'library_admin',
                                   'library',
                                   self.security.encode_id( library1.id ),
                                   self.security.encode_id( AddressField_form.id ),
                                   AddressField_form.name )
    def test_020_add_folder_to_library1( self ):
        """Testing adding a root folder to library1"""
        # Logged in as admin_user
        # Add a root folder to library1
        folder = library1.root_folder
        name = "folder"
        description = "folder description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library1.id ),
                         self.security.encode_id( folder.id ),
                         name=name,
                         description=description )
        global folder1
        folder1 = get_folder( folder.id, name, description )
    def test_025_check_library1( self ):
        """Checking library1 and its root folder"""
        # Logged in as admin_user
        self.browse_library( 'library_admin',
                             self.security.encode_id( library1.id ),
                             check_str1=folder1.name,
                             check_str2=folder1.description )
        # Make sure the template and contents were inherited to folder1
        self.folder_info( 'library_admin',
                          self.security.encode_id( folder1.id ),
                          self.security.encode_id( library1.id ),
                          check_str1=AddressField_form.name,
                          check_str2='This is an inherited template and is not required to be used with this folder' )
    def test_030_add_dataset_to_library1_root_folder( self ):
        """
        Testing adding a new library dataset to library1's root folder, and adding a new UserAddress
        on the upload form.
        """
        # Logged in as admin_user
        # The AddressField template should be inherited to the library dataset upload form.  Passing
        # the value 'new' should submit the form via refresh_on_change and allow new UserAddress information
        # to be posted as part of the upload.
        self.add_library_dataset( 'library_admin',
                                  '1.bed',
                                  self.security.encode_id( library1.id ),
                                  self.security.encode_id( library1.root_folder.id ),
                                  library1.root_folder.name,
                                  file_type='bed',
                                  dbkey='hg18',
                                  root=True,
                                  template_refresh_field_name='field_0',
                                  template_refresh_field_contents='new',
                                  field_0_short_desc='Office',
                                  field_0_name='Dick',
                                  field_0_institution='PSU',
                                  field_0_address='32 O Street',
                                  field_0_city='Anywhere',
                                  field_0_state='AK',
                                  field_0_postal_code='0000000',
                                  field_0_country='USA' )
        global ldda1
        ldda1 = get_latest_ldda()
        assert ldda1 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda1 from the database'
        self.browse_library( 'library_admin',
                             self.security.encode_id( library1.id ),
                             check_str1='1.bed',
                             check_str2=admin_user.email )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library1.id ),
                             self.security.encode_id( library1.root_folder.id ),
                             self.security.encode_id( ldda1.id ),
                             ldda1.name,
                             check_str1='Dick' )
    def test_035_add_template_to_library2( self ):
        """ Testing add an inheritable template containing an CheckboxField to library2"""
        self.add_library_template( 'library_admin',
                                   'library',
                                   self.security.encode_id( library2.id ),
                                   self.security.encode_id( CheckboxField_form.id ),
                                   CheckboxField_form.name )
    def test_040_add_template_to_library3( self ):
        """ Testing add an inheritable template containing an SelectField to library3"""
        self.add_library_template( 'library_admin',
                                   'library',
                                   self.security.encode_id( library3.id ),
                                   self.security.encode_id( SelectField_form.id ),
                                   SelectField_form.name )
    def test_045_add_template_to_library4( self ):
        """ Testing add an inheritable template containing an TextArea to library4"""
        # Add an inheritable template to library4
        self.add_library_template( 'library_admin',
                                   'library',
                                   self.security.encode_id( library4.id ),
                                   self.security.encode_id( TextArea_form.id ),
                                   TextArea_form.name )
    def test_050_add_template_to_library5( self ):
        """ Testing add an inheritable template containing an TextField to library5"""
        # Add an inheritable template to library5
        self.add_library_template( 'library_admin',
                                   'library',
                                   self.security.encode_id( library5.id ),
                                   self.security.encode_id( TextField_form.id ),
                                   TextField_form.name )
    def test_055_add_template_to_library6( self ):
        """ Testing add an inheritable template containing an WorkflowField to library6"""
        # Add an inheritable template to library6
        self.add_library_template( 'library_admin',
                                   'library',
                                   self.security.encode_id( library6.id ),
                                   self.security.encode_id( WorkflowField_form.id ),
                                   WorkflowField_form.name )
    def test_999_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to pass"""
        # Logged in as admin_user
        ##################
        # Delete all form definitions
        ##################
        for form in [ AddressField_form, CheckboxField_form, SelectField_form, TextArea_form, TextField_form, WorkflowField_form ]:
            self.mark_form_deleted( self.security.encode_id( form.form_definition_current.id ) )
        ##################
        # Purge all libraries
        ##################
        for library in [ library1, library2, library3, library4, library5, library6 ]:
            self.delete_library_item( 'library_admin',
                                      self.security.encode_id( library.id ),
                                      self.security.encode_id( library.id ),
                                      library.name,
                                      item_type='library' )
            self.purge_library( self.security.encode_id( library.id ), library.name )
        ##################
        # Make sure all users are associated only with their private roles
        ##################
        for user in [ admin_user, regular_user1, regular_user2, regular_user3 ]:
            refresh( user )
            if len( user.roles) != 1:
                raise AssertionError( '%d UserRoleAssociations are associated with %s ( should be 1 )' % ( len( user.roles ), user.email ) )
        self.logout()
