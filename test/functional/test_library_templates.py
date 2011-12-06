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
            field_name = type.lower()
            form_desc = '%s description' % type
            num_options = 0
            if type == 'SelectField':
                # Pass number of options we want in our SelectField
                num_options = 2
            # Create form for library template
            self.create_form( name=type,
                              description=form_desc,
                              form_type=galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE,
                              field_type=type,
                              num_options=num_options,
                              field_name=field_name )
        # Get all of the new form definitions for later use
        global AddressField_form
        AddressField_form = get_form( 'AddressField' )
        # NOTE: each of these names need to be the same as field_name defined above
        # for each type.
        global address_field_name
        address_field_name = 'addressfield'

        global CheckboxField_form
        CheckboxField_form = get_form( 'CheckboxField' )
        global checkbox_field_name
        checkbox_field_name = 'checkboxfield'

        global SelectField_form
        SelectField_form = get_form( 'SelectField' )
        global select_field_name
        select_field_name = 'selectfield'

        global TextArea_form
        TextArea_form = get_form( 'TextArea' )
        global textarea_name
        textarea_name = 'textarea'

        global TextField_form
        TextField_form = get_form( 'TextField' )
        global textfield_name
        textfield_name = 'textfield'

        global WorkflowField_form
        WorkflowField_form = get_form( 'WorkflowField' )
        global workflow_field_name
        workflow_field_name = 'workflowfield'

    def test_010_create_libraries( self ):
        """Testing creating a new library for each template"""
        # Logged in as admin_user
        # library1 -> AddressField
        # library2 -> CheckboxField
        # library3 -> SelectField
        # library4 -> TextArea
        # library5 -> TextField
        # library6 -> WorkflowField
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
        # Add a template containing an AddressField to library1
        self.add_template( cntrller='library_admin',
                           item_type='library',
                           form_type=galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE.replace( ' ', '+' ),
                           form_id=self.security.encode_id( AddressField_form.id ),
                           form_name=AddressField_form.name,
                           library_id=self.security.encode_id( library1.id ) )
    def test_020_add_folder_to_library1( self ):
        """Testing adding a folder to library1"""
        # Logged in as admin_user
        # Add a folder to library1
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
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ folder1.name, folder1.description ] )
        # Make sure the template and contents were inherited to folder1
        self.folder_info( cntrller='library_admin',
                          folder_id=self.security.encode_id( folder1.id ),
                          library_id=self.security.encode_id( library1.id ),
                          template_refresh_field_name=address_field_name,
                          strings_displayed=[ AddressField_form.name,
                                              'This is an inherited template and is not required to be used with this folder' ] )
    def test_030_add_dataset_to_folder1( self ):
        """Testing adding a ldda1 to folder1, and adding a new UserAddress on the upload form."""
        # Logged in as admin_user
        # The AddressField template should be inherited to the library dataset upload form.  Passing
        # the value 'new' should submit the form via refresh_on_change and allow new UserAddress information
        # to be posted as part of the upload.
        filename = '1.bed'
        ldda_message = '1.bed message'
        short_desc = 'Office'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library1.id ),
                                     folder_id=self.security.encode_id( folder1.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     template_refresh_field_name=address_field_name,
                                     ldda_message=ldda_message,
                                     template_refresh_field_contents='new',
                                     template_fields=[ ( '%s_short_desc' % address_field_name, short_desc ),
                                                       ( '%s_name' % address_field_name, 'Dick' ),
                                                       ( '%s_institution' % address_field_name, 'PSU' ),
                                                       ( '%s_address' % address_field_name, '32 O Street' ),
                                                       ( '%s_city' % address_field_name, 'Anywhere' ),
                                                       ( '%s_state' % address_field_name, 'AK' ),
                                                       ( '%s_postal_code' % address_field_name, '0000000' ),
                                                       ( '%s_country' % address_field_name, 'USA' ) ],
                                     strings_displayed=[ 'Upload files' ] )
        global user_address1
        user_address1 = get_user_address( admin_user, short_desc )
        assert user_address1 is not None, 'Problem retrieving user_address1 from the database'
        global ldda1
        ldda1 = get_latest_ldda_by_name( filename )
        assert ldda1 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda1 from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ ldda1.name, ldda1.message, 'bed' ] )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library1.id ),
                             self.security.encode_id( folder1.id ),
                             self.security.encode_id( ldda1.id ),
                             ldda1.name,
                             strings_displayed=[ 'Dick' ] )
    def test_035_edit_contents_of_ldda1_tempplate( self ):
        """Testing editing the contents of ldda1 AddressField template by adding a new user_address"""
        short_desc = 'Home'
        # Now add a new user_address to ldda1
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library1.id ),
                             self.security.encode_id( folder1.id ),
                             self.security.encode_id( ldda1.id ),
                             ldda1.name,
                             template_refresh_field_name=address_field_name,
                             template_refresh_field_contents='new',
                             template_fields=[ ( '%s_short_desc' % address_field_name, short_desc ),
                                               ( '%s_name' % address_field_name, 'Richard' ),
                                               ( '%s_institution' % address_field_name, 'PSU' ),
                                               ( '%s_address' % address_field_name, '32 O Street' ),
                                               ( '%s_city' % address_field_name, 'Anywhere' ),
                                               ( '%s_state' % address_field_name, 'AK' ),
                                               ( '%s_postal_code' % address_field_name, '0000000' ),
                                               ( '%s_country' % address_field_name, 'USA' ) ],
                             strings_displayed=[ short_desc ] )
        global user_address2
        user_address2 = get_user_address( admin_user, short_desc )
        assert user_address2 is not None, 'Problem retrieving user_address2 from the database'
    def test_040_edit_contents_of_folder1_template( self ):
        """Testing editing the contents of folder1 AddressField template"""
        # Make sure the template and contents were inherited to folder1
        self.folder_info( cntrller='library_admin',
                          folder_id=self.security.encode_id( folder1.id ),
                          library_id=self.security.encode_id( library1.id ),
                          template_refresh_field_name=address_field_name,
                          template_refresh_field_contents=str( user_address2.id ),
                          strings_displayed=[ AddressField_form.name,
                                              'This is an inherited template and is not required to be used with this folder' ],
                          strings_displayed_after_submit=[ 'Richard' ] )
    def test_045_add_dataset_to_folder1( self ):
        """Testing adding another ldda to folder1"""
        # The upload form should now inherit user_address2 on the upload form
        filename = '2.bed'
        ldda_message = '2.bed message'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library1.id ),
                                     folder_id=self.security.encode_id( folder1.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     template_refresh_field_name=address_field_name,
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'Upload files' ] )
        # Make sure user_address2 is associated with ldda.
        self.ldda_edit_info( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             folder_id=self.security.encode_id( folder1.id ),
                             ldda_id=self.security.encode_id( ldda1.id ),
                             ldda_name=ldda1.name,
                             template_refresh_field_name=address_field_name,
                             strings_displayed=[ user_address2.desc ] )
    def test_050_add_template_to_library2( self ):
        """ Testing add an inheritable template containing an CheckboxField to library2"""
        # Add a template containing an CheckboxField to library1
        self.add_template( cntrller='library_admin',
                           item_type='library',
                           form_type=galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE.replace( ' ', '+' ),
                           form_id=self.security.encode_id( CheckboxField_form.id ),
                           form_name=CheckboxField_form.name,
                           library_id=self.security.encode_id( library2.id ) )
        # Check the CheckboxField to make sure the template contents are inherited
        self.library_info( 'library_admin',
                            self.security.encode_id( library2.id ),
                            template_fields = [ ( checkbox_field_name, '1' ) ] )
    def test_055_add_folder2_to_library2( self ):
        """Testing adding a folder to library2"""
        # Logged in as admin_user
        # Add a folder to library2
        folder = library2.root_folder
        name = "folder"
        description = "folder description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library2.id ),
                         self.security.encode_id( folder.id ),
                         name=name,
                         description=description )
        global folder2
        folder2 = get_folder( folder.id, name, description )
    def test_060_check_library2( self ):
        """Checking library2 and its root folder"""
        # Logged in as admin_user
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library2.id ),
                             strings_displayed=[ folder2.name, folder2.description ] )
    def test_065_save_folder2_inherited_template( self ):
        """Saving the inherited template for folder2"""
        # Logged in as admin_user
        # Save the inherited template
        self.folder_info( cntrller='library_admin',
                          folder_id=self.security.encode_id( folder2.id ),
                          library_id=self.security.encode_id( library2.id ),
                          template_fields=[ ( checkbox_field_name, '1' ) ],
                          strings_displayed=[ CheckboxField_form.name,
                                              'This is an inherited template and is not required to be used with this folder' ] )
    def test_070_add_ldda_to_folder2( self ):
        """
        Testing adding a new library dataset to library2's folder, making sure the CheckboxField is
        checked on the upload form.
        """
        # Logged in as admin_user
        filename = '1.bed'
        ldda_message = '1.bed message'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library2.id ),
                                     folder_id=self.security.encode_id( folder2.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'CheckboxField', 'checked' ] )
        ldda = get_latest_ldda_by_name( filename )
        assert ldda is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library2.id ),
                             strings_displayed=[ ldda.name, ldda.message, 'bed' ] )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library2.id ),
                             self.security.encode_id( folder2.id ),
                             self.security.encode_id( ldda.id ),
                             ldda.name,
                             strings_displayed=[ 'CheckboxField', 'checked' ] )
    def test_080_add_template_to_library3( self ):
        """ Testing add an inheritable template containing an SelectField to library3"""
        # Logged in as admin_user
        self.add_template( cntrller='library_admin',
                           item_type='library',
                           form_type=galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE.replace( ' ', '+' ),
                           form_id=self.security.encode_id( SelectField_form.id ),
                           form_name=SelectField_form.name,
                           library_id=self.security.encode_id( library3.id ) )
        # Select the 2nd option in the SelectField to make sure the template contents are inherited
        # SelectField option names are zero-based
        self.library_info( 'library_admin',
                            self.security.encode_id( library3.id ),
                            template_fields=[ ( select_field_name, 'Option1' ) ] )
    def test_085_add_folder3_to_library3( self ):
        """Testing adding a folder to library3"""
        # Logged in as admin_user
        # Add a folder to library3
        folder = library3.root_folder
        name = "folder"
        description = "folder description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library3.id ),
                         self.security.encode_id( folder.id ),
                         name=name,
                         description=description )
        global folder3
        folder3 = get_folder( folder.id, name, description )
    def test_090_check_library3( self ):
        """Checking library3 and its root folder"""
        # Logged in as admin_user
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library3.id ),
                             strings_displayed=[ folder3.name, folder3.description ] )
    def test_095_save_folder3_inherited_template( self ):
        """Saving the inherited template for folder3"""
        # Logged in as admin_user
        # Save the inherited template
        self.folder_info( cntrller='library_admin',
                          folder_id=self.security.encode_id( folder3.id ),
                          library_id=self.security.encode_id( library3.id ),
                          template_fields=[ ( select_field_name, 'Option1' ) ],
                          strings_displayed=[ SelectField_form.name,
                                              'This is an inherited template and is not required to be used with this folder',
                                              'Option1' ] )
    def test_100_add_ldda_to_folder3( self ):
        """
        Testing adding a new library dataset to library3's folder, making sure the SelectField setting is correct on the upload form.
        """
        filename = '3.bed'
        ldda_message = '3.bed message'
        # Logged in as admin_user
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library3.id ),
                                     folder_id=self.security.encode_id( folder3.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'SelectField', 'selected>Option1' ] )
        ldda = get_latest_ldda_by_name( filename )
        assert ldda is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library3.id ),
                             strings_displayed=[ ldda.name, ldda.message, 'bed' ] )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library3.id ),
                             self.security.encode_id( folder3.id ),
                             self.security.encode_id( ldda.id ),
                             ldda.name,
                             strings_displayed=[ 'SelectField', 'Option1' ] )
        # Import a dataset from the current history
        filename = '8.bed'
        self.new_history( name='import with SelectField' )
        self.upload_file( filename )
        hda = get_latest_hda()
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library3.id ),
                                     folder_id=self.security.encode_id( folder3.id ),
                                     upload_option='import_from_history',
                                     hda_ids=self.security.encode_id( hda.id ),
                                     strings_displayed=[ '<input type="hidden" name="%s" value="Option1"/>' % select_field_name ] )
        ldda = get_latest_ldda_by_name( filename )
        assert ldda is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library3.id ),
                             strings_displayed=[ ldda.name, 'bed' ] )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library3.id ),
                             self.security.encode_id( folder3.id ),
                             self.security.encode_id( ldda.id ),
                             ldda.name,
                             strings_displayed=[ 'SelectField', 'Option1' ] )
    def test_105_add_template_to_library4( self ):
        """ Testing add an inheritable template containing an TextArea to library4"""
        # Logged in as admin_user
        # Add an inheritable template to library4
        self.add_template( cntrller='library_admin',
                           item_type='library',
                           form_type=galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE.replace( ' ', '+' ),
                           form_id=self.security.encode_id( TextArea_form.id ),
                           form_name=TextArea_form.name,
                           library_id=self.security.encode_id( library4.id ) )
        # Select the 2nd option in the SelectField to make sure the template contents are inherited
        self.library_info( 'library_admin',
                            self.security.encode_id( library4.id ),
                            template_fields=[ ( textarea_name, 'This text should be inherited' ) ] )
    def test_110_add_folder4_to_library4( self ):
        """Testing adding a folder to library4"""
        # Logged in as admin_user
        # Add a folder to library4
        folder = library4.root_folder
        name = "folder"
        description = "folder description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library4.id ),
                         self.security.encode_id( folder.id ),
                         name=name,
                         description=description )
        global folder4
        folder4 = get_folder( folder.id, name, description )
    def test_115_save_folder4_inherited_template( self ):
        """Saving the inherited template for folder4"""
        # Logged in as admin_user
        # Save the inherited template
        self.folder_info( cntrller='library_admin',
                          folder_id=self.security.encode_id( folder4.id ),
                          library_id=self.security.encode_id( library4.id ),
                          template_fields=[ ( textarea_name, 'This text should be inherited' ) ],
                          strings_displayed=[ TextArea_form.name,
                                              'This is an inherited template and is not required to be used with this folder',
                                              'This text should be inherited' ] )
    def test_120_add_ldda_to_folder4( self ):
        """
        Testing adding a new library dataset to library4's folder, making sure the TextArea setting is correct on the upload form.
        """
        filename = '4.bed'
        ldda_message = '4.bed message'
        # Logged in as admin_user
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library4.id ),
                                     folder_id=self.security.encode_id( folder4.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'TextArea', 'This text should be inherited' ] )
        ldda = get_latest_ldda_by_name( filename )
        assert ldda is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library4.id ),
                             strings_displayed=[ ldda.name, ldda.message, 'bed' ] )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library4.id ),
                             self.security.encode_id( folder4.id ),
                             self.security.encode_id( ldda.id ),
                             ldda.name,
                             strings_displayed=[ 'TextArea', 'This text should be inherited' ] )
    def test_125_add_template_to_library5( self ):
        """ Testing add an inheritable template containing an TextField to library5"""
        # Add an inheritable template to library5
        self.add_template( cntrller='library_admin',
                           item_type='library',
                           form_type=galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE.replace( ' ', '+' ),
                           form_id=self.security.encode_id( TextField_form.id ),
                           form_name=TextField_form.name,
                           library_id=self.security.encode_id( library5.id ) )
        # Select the 2nd option in the SelectField to make sure the template contents are inherited
        self.library_info( 'library_admin',
                           self.security.encode_id( library5.id ),
                           template_fields=[ ( textfield_name, 'This text should be inherited' ) ] )
    def test_130_add_folder5_to_library5( self ):
        """Testing adding a folder to library5"""
        # Logged in as admin_user
        # Add a folder to library5
        folder = library5.root_folder
        name = "folder"
        description = "folder description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library5.id ),
                         self.security.encode_id( folder.id ),
                         name=name,
                         description=description )
        global folder5
        folder5 = get_folder( folder.id, name, description )
    def test_135_save_folder5_inherited_template( self ):
        """Saving the inherited template for folder5"""
        # Logged in as admin_user
        # Save the inherited template
        self.folder_info( cntrller='library_admin',
                          folder_id=self.security.encode_id( folder5.id ),
                          library_id=self.security.encode_id( library5.id ),
                          template_fields=[ ( textfield_name, 'This text should be inherited' ) ],
                          strings_displayed=[ TextField_form.name,
                                              'This is an inherited template and is not required to be used with this folder',
                                              'This text should be inherited' ] )
    def test_140_add_ldda_to_folder5( self ):
        """
        Testing adding a new library dataset to library5's folder, making sure the TextField setting is correct on the upload form.
        """
        # Logged in as admin_user
        filename = '5.bed'
        ldda_message = '5.bed message'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library5.id ),
                                     folder_id=self.security.encode_id( folder5.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'TextField', 'This text should be inherited' ] )
        ldda = get_latest_ldda_by_name( filename )
        assert ldda is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library5.id ),
                             strings_displayed=[ ldda.name, ldda.message, 'bed' ] )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library5.id ),
                             self.security.encode_id( folder5.id ),
                             self.security.encode_id( ldda.id ),
                             ldda.name,
                             strings_displayed=[ 'TextField', 'This text should be inherited' ] )
    def test_145_edit_library5_template_layout( self ):
        """Test editing the layout of library5's template"""
        # Currently there is only a TextField, and we'll add a TextArea.
        self.edit_template( cntrller='library_admin',
                            item_type='library',
                            form_type=galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE.replace( ' ', '+' ),
                            library_id=self.security.encode_id( library5.id ),
                            field_type='TextArea',
                            field_label_1=TextArea_form.name,
                            field_helptext_1='%s help' % TextArea_form.name,
                            field_default_1='%s default' % TextArea_form.name )
    def test_150_add_ldda_to_library5( self ):
        """
        Testing adding a new library dataset to library5's folder, making sure the TextField and new TextArea settings are correct on the upload form.
        """
        filename = '6.bed'
        ldda_message = '6.bed message'
        # Logged in as admin_user
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library5.id ),
                                     folder_id=self.security.encode_id( library5.root_folder.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'TextField',
                                                         'This text should be inherited',
                                                         'TextArea' ] )
        ldda = get_latest_ldda_by_name( filename )
        assert ldda is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library5.id ),
                             strings_displayed=[ ldda.name, ldda.message, 'bed' ] )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library5.id ),
                             self.security.encode_id( library5.root_folder.id ),
                             self.security.encode_id( ldda.id ),
                             ldda.name,
                             strings_displayed=[ 'TextField',
                                                 'This text should be inherited',
                                                 'TextArea' ] )
    def test_155_add_template_to_library6( self ):
        """ Testing add an inheritable template containing an WorkflowField to library6"""
        # Add an inheritable template to library6
        # We won't select an option since we have no workflow to select
        self.add_template( cntrller='library_admin',
                           item_type='library',
                           form_type=galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE.replace( ' ', '+' ),
                           form_id=self.security.encode_id( WorkflowField_form.id ),
                           form_name=WorkflowField_form.name,
                           library_id=self.security.encode_id( library6.id ) )
    def test_160_add_folder6_to_library6( self ):
        """Testing adding a folder to library6"""
        # Logged in as admin_user
        # Add a folder to library5
        folder = library6.root_folder
        name = "folder"
        description = "folder description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library6.id ),
                         self.security.encode_id( folder.id ),
                         name=name,
                         description=description )
        global folder6
        folder6 = get_folder( folder.id, name, description )
    def test_165_save_folder6_inherited_template( self ):
        """Saving the inherited template for folder6"""
        # Logged in as admin_user
        # Save the inherited template - we won't select an option since we have no workflow to select
        self.folder_info( cntrller='library_admin',
                          folder_id=self.security.encode_id( folder6.id ),
                          library_id=self.security.encode_id( library6.id ),
                          template_fields=[ ( workflow_field_name, 'none' ) ],
                          strings_displayed=[ WorkflowField_form.name,
                                              'This is an inherited template and is not required to be used with this folder',
                                              'none' ] )
    def test_170_add_ldda_to_folder6( self ):
        """
        Testing adding a new library dataset to library6's folder, making sure the WorkflowField setting is correct on the upload form.
        """
        # Logged in as admin_user
        filename = '7.bed'
        ldda_message = '7.bed message'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library6.id ),
                                     folder_id=self.security.encode_id( folder6.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'WorkflowField', 'none' ] )
        ldda = get_latest_ldda_by_name( filename )
        assert ldda is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library6.id ),
                             strings_displayed=[ ldda.name, ldda.message, 'bed' ] )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library6.id ),
                             self.security.encode_id( folder6.id ),
                             self.security.encode_id( ldda.id ),
                             ldda.name,
                             strings_displayed=[ 'WorkflowField', 'none' ] )
    def test_999_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to pass"""
        # Logged in as admin_user
        ##################
        # Delete all form definitions
        ##################
        for form in [ AddressField_form, CheckboxField_form, SelectField_form, TextArea_form, TextField_form, WorkflowField_form ]:
            self.mark_form_deleted( self.security.encode_id( form.form_definition_current.id ) )
        ##################
        # Mark all user_addresses deleted
        ##################
        for user_address in [ user_address1, user_address2 ]:
            mark_obj_deleted( user_address )
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
