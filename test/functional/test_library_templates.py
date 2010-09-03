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
        self.add_library_template( 'library_admin',
                                   'library',
                                   self.security.encode_id( library1.id ),
                                   self.security.encode_id( AddressField_form.id ),
                                   AddressField_form.name )
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
    def test_030_add_dataset_to_library1_folder( self ):
        """
        Testing adding a new library dataset to library1's folder, and adding a new UserAddress
        on the upload form.
        """
        # Logged in as admin_user
        # The AddressField template should be inherited to the library dataset upload form.  Passing
        # the value 'new' should submit the form via refresh_on_change and allow new UserAddress information
        # to be posted as part of the upload.
        self.add_library_dataset( 'library_admin',
                                  '1.bed',
                                  self.security.encode_id( library1.id ),
                                  self.security.encode_id( folder1.id ),
                                  folder1.name,
                                  file_type='bed',
                                  dbkey='hg18',
                                  root=False,
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
                             self.security.encode_id( folder1.id ),
                             self.security.encode_id( ldda1.id ),
                             ldda1.name,
                             check_str1='Dick' )
    def test_035_add_template_to_library2( self ):
        """ Testing add an inheritable template containing an CheckboxField to library2"""
        # Add a template containing an CheckboxField to library1
        self.add_library_template( 'library_admin',
                                   'library',
                                   self.security.encode_id( library2.id ),
                                   self.security.encode_id( CheckboxField_form.id ),
                                   CheckboxField_form.name )
        # Check the CheckboxField to make sure the template contents are inherited
        self.set_library_info_field_template_field( 'library_admin',
                                                    self.security.encode_id( library2.id ),
                                                    field_value='1' )
    def test_040_add_folder_to_library2( self ):
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
    def test_045_check_library2( self ):
        """Checking library2 and its root folder"""
        # Logged in as admin_user
        self.browse_library( 'library_admin',
                             self.security.encode_id( library2.id ),
                             check_str1=folder2.name,
                             check_str2=folder2.description )
    def test_050_save_folder2_inherited_template( self ):
        """Saving the inherited template for folder2"""
        # Logged in as admin_user
        # Save the inherited template
        self.save_folder_template( 'library_admin',
                                   self.security.encode_id( folder2.id ),
                                   self.security.encode_id( library2.id ),
                                   field_name="field_0",
                                   field_value='1',
                                   check_str1=CheckboxField_form.name,
                                   check_str2='This is an inherited template and is not required to be used with this folder' )
    def test_055_add_dataset_to_library2_folder( self ):
        """
        Testing adding a new library dataset to library2's folder, making sure the CheckboxField is
        checked on the upload form.
        """
        # Logged in as admin_user
        self.add_library_dataset( 'library_admin',
                                  '1.bed',
                                  self.security.encode_id( library2.id ),
                                  self.security.encode_id( folder2.id ),
                                  folder2.name,
                                  file_type='bed',
                                  dbkey='hg18',
                                  root=False,
                                  check_str1='CheckboxField',
                                  check_str2='checked' )
        global ldda2
        ldda2 = get_latest_ldda()
        assert ldda2 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda2 from the database'
        self.browse_library( 'library_admin',
                             self.security.encode_id( library2.id ),
                             check_str1='1.bed',
                             check_str2=admin_user.email )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library2.id ),
                             self.security.encode_id( folder2.id ),
                             self.security.encode_id( ldda2.id ),
                             ldda2.name,
                             check_str1='CheckboxField',
                             check_str2='checked' )
    def test_060_add_template_to_library3( self ):
        """ Testing add an inheritable template containing an SelectField to library3"""
        # Logged in as admin_user
        self.add_library_template( 'library_admin',
                                   'library',
                                   self.security.encode_id( library3.id ),
                                   self.security.encode_id( SelectField_form.id ),
                                   SelectField_form.name )
        # Select the 2nd option in the SelectField to make sure the template contents are inherited
        self.set_library_info_field_template_field( 'library_admin',
                                                    self.security.encode_id( library3.id ),
                                                    field_value='Two' )
    def test_065_add_folder_to_library3( self ):
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
    def test_070_check_library3( self ):
        """Checking library3 and its root folder"""
        # Logged in as admin_user
        self.browse_library( 'library_admin',
                             self.security.encode_id( library3.id ),
                             check_str1=folder3.name,
                             check_str2=folder3.description )
    def test_075_save_folder3_inherited_template( self ):
        """Saving the inherited template for folder3"""
        # Logged in as admin_user
        # Save the inherited template
        self.save_folder_template( 'library_admin',
                                   self.security.encode_id( folder3.id ),
                                   self.security.encode_id( library3.id ),
                                   field_name="field_0",
                                   field_value='Two',
                                   check_str1=SelectField_form.name,
                                   check_str2='This is an inherited template and is not required to be used with this folder',
                                   check_str3='Two' )
    def test_080_add_dataset_to_library3_folder( self ):
        """
        Testing adding a new library dataset to library3's folder,
        making sure the SelectField setting is correct on the upload form.
        """
        # Logged in as admin_user
        self.add_library_dataset( 'library_admin',
                                  '1.bed',
                                  self.security.encode_id( library3.id ),
                                  self.security.encode_id( folder3.id ),
                                  folder3.name,
                                  file_type='bed',
                                  dbkey='hg18',
                                  root=False,
                                  check_str1='SelectField',
                                  check_str2='selected>Two' )
        global ldda3
        ldda3 = get_latest_ldda()
        assert ldda3 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda3 from the database'
        self.browse_library( 'library_admin',
                             self.security.encode_id( library3.id ),
                             check_str1='1.bed',
                             check_str2=admin_user.email )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library3.id ),
                             self.security.encode_id( folder3.id ),
                             self.security.encode_id( ldda3.id ),
                             ldda3.name,
                             check_str1='SelectField',
                             check_str2='Two' )
    def test_085_add_template_to_library4( self ):
        """ Testing add an inheritable template containing an TextArea to library4"""
        # Logged in as admin_user
        # Add an inheritable template to library4
        self.add_library_template( 'library_admin',
                                   'library',
                                   self.security.encode_id( library4.id ),
                                   self.security.encode_id( TextArea_form.id ),
                                   TextArea_form.name )
        # Select the 2nd option in the SelectField to make sure the template contents are inherited
        self.set_library_info_field_template_field( 'library_admin',
                                                    self.security.encode_id( library4.id ),
                                                    field_value='This text should be inherited' )
    def test_090_add_folder_to_library4( self ):
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
    def test_095_save_folder4_inherited_template( self ):
        """Saving the inherited template for folder4"""
        # Logged in as admin_user
        # Save the inherited template
        self.save_folder_template( 'library_admin',
                                   self.security.encode_id( folder4.id ),
                                   self.security.encode_id( library4.id ),
                                   field_name="field_0",
                                   field_value='This text should be inherited',
                                   check_str1=TextArea_form.name,
                                   check_str2='This is an inherited template and is not required to be used with this folder',
                                   check_str3='This text should be inherited' )
    def test_100_add_dataset_to_library4_folder( self ):
        """
        Testing adding a new library dataset to library4's folder,
        making sure the TextArea setting is correct on the upload form.
        """
        # Logged in as admin_user
        self.add_library_dataset( 'library_admin',
                                  '1.bed',
                                  self.security.encode_id( library4.id ),
                                  self.security.encode_id( folder4.id ),
                                  folder4.name,
                                  file_type='bed',
                                  dbkey='hg18',
                                  root=False,
                                  check_str1='TextArea',
                                  check_str2='This text should be inherited' )
        global ldda4
        ldda4 = get_latest_ldda()
        assert ldda4 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda4 from the database'
        self.browse_library( 'library_admin',
                             self.security.encode_id( library4.id ),
                             check_str1='1.bed',
                             check_str2=admin_user.email )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library4.id ),
                             self.security.encode_id( folder4.id ),
                             self.security.encode_id( ldda4.id ),
                             ldda4.name,
                             check_str1='TextArea',
                             check_str2='This text should be inherited' )
    def test_105_add_template_to_library5( self ):
        """ Testing add an inheritable template containing an TextField to library5"""
        # Add an inheritable template to library5
        self.add_library_template( 'library_admin',
                                   'library',
                                   self.security.encode_id( library5.id ),
                                   self.security.encode_id( TextField_form.id ),
                                   TextField_form.name )
        # Select the 2nd option in the SelectField to make sure the template contents are inherited
        self.set_library_info_field_template_field( 'library_admin',
                                                    self.security.encode_id( library5.id ),
                                                    field_value='This text should be inherited' )
    def test_110_add_folder_to_library5( self ):
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
    def test_115_save_folder5_inherited_template( self ):
        """Saving the inherited template for folder5"""
        # Logged in as admin_user
        # Save the inherited template
        self.save_folder_template( 'library_admin',
                                   self.security.encode_id( folder5.id ),
                                   self.security.encode_id( library5.id ),
                                   field_name="field_0",
                                   field_value='This text should be inherited',
                                   check_str1=TextField_form.name,
                                   check_str2='This is an inherited template and is not required to be used with this folder',
                                   check_str3='This text should be inherited' )
    def test_120_add_dataset_to_library5_folder( self ):
        """
        Testing adding a new library dataset to library5's folder,
        making sure the TextField setting is correct on the upload form.
        """
        # Logged in as admin_user
        self.add_library_dataset( 'library_admin',
                                  '1.bed',
                                  self.security.encode_id( library5.id ),
                                  self.security.encode_id( folder5.id ),
                                  folder5.name,
                                  file_type='bed',
                                  dbkey='hg18',
                                  root=False,
                                  check_str1='TextField',
                                  check_str2='This text should be inherited' )
        global ldda5
        ldda5 = get_latest_ldda()
        assert ldda5 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda5 from the database'
        self.browse_library( 'library_admin',
                             self.security.encode_id( library5.id ),
                             check_str1='1.bed',
                             check_str2=admin_user.email )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library5.id ),
                             self.security.encode_id( folder5.id ),
                             self.security.encode_id( ldda5.id ),
                             ldda5.name,
                             check_str1='TextField',
                             check_str2='This text should be inherited' )
    def test_125_edit_library5_template_layout( self ):
        """Test editing the layout of library5's template"""
        # Currently there is only a TextField, and we'll add a TextArea.
        self.edit_template( 'library_admin',
                            'library',
                            self.security.encode_id( library5.id ),
                            field_type='TextArea',
                            field_name_1=TextArea_form.name,
                            field_helptext_1='%s help' % TextArea_form.name,
                            field_default_1='%s default' % TextArea_form.name )
    def test_130_add_dataset_to_library5( self ):
        """
        Testing adding a new library dataset to library5's folder,
        making sure the TextField and new TextArea settings are 
        correct on the upload form.
        """
        # Logged in as admin_user
        self.add_library_dataset( 'library_admin',
                                  '2.bed',
                                  self.security.encode_id( library5.id ),
                                  self.security.encode_id( library5.root_folder.id ),
                                  library5.root_folder.name,
                                  file_type='bed',
                                  dbkey='hg18',
                                  root=True,
                                  check_str1='TextField',
                                  check_str2='This text should be inherited',
                                  check_str3='TextArea' )
        global ldda5a
        ldda5a = get_latest_ldda()
        assert ldda5a is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda5a from the database'
        self.browse_library( 'library_admin',
                             self.security.encode_id( library5.id ),
                             check_str1='1.bed',
                             check_str2=admin_user.email )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library5.id ),
                             self.security.encode_id( library5.root_folder.id ),
                             self.security.encode_id( ldda5a.id ),
                             ldda5a.name,
                             check_str1='TextField',
                             check_str2='This text should be inherited',
                             check_str3='TextArea' )
    def test_135_add_template_to_library6( self ):
        """ Testing add an inheritable template containing an WorkflowField to library6"""
        # Add an inheritable template to library6
        # We won't select an option since we have no workflow to select
        self.add_library_template( 'library_admin',
                                   'library',
                                   self.security.encode_id( library6.id ),
                                   self.security.encode_id( WorkflowField_form.id ),
                                   WorkflowField_form.name )
    def test_140_add_folder_to_library6( self ):
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
    def test_145_save_folder6_inherited_template( self ):
        """Saving the inherited template for folder6"""
        # Logged in as admin_user
        # Save the inherited template - we won't select an option since we have no workflow to select
        self.save_folder_template( 'library_admin',
                                   self.security.encode_id( folder6.id ),
                                   self.security.encode_id( library6.id ),
                                   field_name="field_0",
                                   field_value='none',
                                   check_str1=WorkflowField_form.name,
                                   check_str2='This is an inherited template and is not required to be used with this folder',
                                   check_str3='none' )
    def test_150_add_dataset_to_library6_folder( self ):
        """
        Testing adding a new library dataset to library6's folder,
        making sure the WorkflowField setting is correct on the upload form.
        """
        # Logged in as admin_user
        self.add_library_dataset( 'library_admin',
                                  '1.bed',
                                  self.security.encode_id( library6.id ),
                                  self.security.encode_id( folder6.id ),
                                  folder6.name,
                                  file_type='bed',
                                  dbkey='hg18',
                                  root=False,
                                  check_str1='WorkflowField',
                                  check_str2='none' )
        global ldda6
        ldda6 = get_latest_ldda()
        assert ldda6 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda6 from the database'
        self.browse_library( 'library_admin',
                             self.security.encode_id( library6.id ),
                             check_str1='1.bed',
                             check_str2=admin_user.email )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library6.id ),
                             self.security.encode_id( folder6.id ),
                             self.security.encode_id( ldda6.id ),
                             ldda6.name,
                             check_str1='WorkflowField',
                             check_str2='none' )
    def test_999_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to pass"""
        """
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
        """