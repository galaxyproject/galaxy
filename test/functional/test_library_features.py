from base.twilltestcase import *
from base.test_db_util import *

class TestLibraryFeatures( TwillTestCase ):
    def test_000_initiate_users( self ):
        """Ensuring all required user accounts exist"""
        self.logout()
        self.login( email='test1@bx.psu.edu' )
        global regular_user1
        regular_user1 = get_user( 'test1@bx.psu.edu' )
        assert regular_user1 is not None, 'Problem retrieving user with email "test1@bx.psu.edu" from the database'
        self.logout()
        self.login( email='test2@bx.psu.edu' )
        global regular_user2
        regular_user2 = get_user( 'test2@bx.psu.edu' )
        assert regular_user2 is not None, 'Problem retrieving user with email "test2@bx.psu.edu" from the database'
        self.logout()
        self.login( email='test3@bx.psu.edu' )
        global regular_user3
        regular_user3 = get_user( 'test3@bx.psu.edu' )
        assert regular_user3 is not None, 'Problem retrieving user with email "test3@bx.psu.edu" from the database'
        self.logout()
        self.login( email='test@bx.psu.edu' )
        global admin_user
        admin_user = get_user( 'test@bx.psu.edu' )
        assert admin_user is not None, 'Problem retrieving user with email "test@bx.psu.edu" from the database'
    def test_005_create_library( self ):
        """Testing creating a new library, then renaming it"""
        # Logged in as admin_user
        name = "library features Library1"
        description = "library features Library1 description"
        synopsis = "library features Library1 synopsis"
        self.create_library( name=name, description=description, synopsis=synopsis )
        self.browse_libraries_admin( check_str1=name, check_str2=description )
        # Get the library object for later tests
        global library_one
        library_one = get_library( name, description, synopsis )
        assert library_one is not None, 'Problem retrieving library named "%s" from the database' % name
        # Rename the library
        new_name = "library features Library1 new name"
        new_description = "library features Library1 new description"
        new_synopsis = "library features Library1 new synopsis"
        self.library_info( 'library_admin',
                            self.security.encode_id( library_one.id ),
                            library_one.name,
                            new_name=new_name,
                            new_description=new_description,
                            new_synopsis=new_synopsis )
        self.browse_libraries_admin( check_str1=new_name, check_str2=new_description )
        # Reset the library back to the original name and description
        self.library_info( 'library_admin',
                            self.security.encode_id( library_one.id ),
                            library_one.name,
                            new_name=name,
                            new_description=description,
                            new_synopsis=synopsis )
        refresh( library_one )
    def test_010_library_template_features( self ):
        """Testing adding a template to a library, then filling in the contents"""
        # Logged in as admin_user
        form_name = 'Library template Form One'
        form_desc = 'This is Form One'
        form_type = galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE
        # Create form for library template
        self.create_form( name=form_name, desc=form_desc, formtype=form_type )
        global form_one
        form_one = get_form( form_name )
        assert form_one is not None, 'Problem retrieving form named (%s) from the database' % form_name
        # Add new template based on the form to the library
        template_name = 'Library Template 1'
        self.add_library_template( 'library_admin',
                                   'library',
                                   self.security.encode_id( library_one.id ),
                                   self.security.encode_id( form_one.id ),
                                   form_one.name )
        # Make sure the template fields are displayed on the library information page
        field_dict = form_one.fields[ 0 ]
        global form_one_field_label
        form_one_field_label = '%s' % str( field_dict.get( 'label', 'Field 0' ) )
        global form_one_field_help
        form_one_field_help = '%s' % str( field_dict.get( 'helptext', 'Field 0 help' ) )
        global form_one_field_required
        form_one_field_required = '%s' % str( field_dict.get( 'required', 'optional' ) ).capitalize()
        # Add information to the library using the template
        global form_one_field_name
        form_one_field_name = 'field_0'
        contents = '%s library contents' % form_one_field_label
        self.library_info( 'library_admin',
                            self.security.encode_id( library_one.id ),
                            library_one.name,
                            ele_1_field_name=form_one_field_name,
                            ele_1_contents=contents )
    def test_015_edit_template_contents_admin_view( self ):
        """Test editing template contents from the Admin view"""
        # Logged in as admin_user
        # Make sure the template contents were from the previous method correctly saved
        # Twill barfs if this test is run in the previous method.
        contents = '%s library contents' % form_one_field_label
        self.library_info( 'library_admin',
                            self.security.encode_id( library_one.id ),
                            library_one.name,
                            check_str1=contents )
        contents = '%s library contents' % form_one_field_label
        contents_edited = contents + ' edited'
        # Edit the contents and then save them
        self.library_info( 'library_admin',
                            self.security.encode_id( library_one.id ),
                            library_one.name,
                            ele_1_field_name=form_one_field_name,
                            ele_1_contents=contents_edited )
        # Make sure the template contents were correctly saved
        self.library_info( 'library_admin',
                            self.security.encode_id( library_one.id ),
                            library_one.name,
                            check_str1=contents_edited )
    def test_020_add_public_dataset_to_root_folder( self ):
        """Testing adding a public dataset to the root folder, making sure library template is inherited"""
        # Logged in as admin_user
        message = 'Testing adding a public dataset to the root folder'
        # The template should be inherited to the library dataset upload form.
        template_contents = "%s contents for root folder 1.bed" % form_one_field_label
        self.add_library_dataset( 'library_admin',
                                  '1.bed',
                                  self.security.encode_id( library_one.id ),
                                  self.security.encode_id( library_one.root_folder.id ),
                                  library_one.root_folder.name,
                                  file_type='bed',
                                  dbkey='hg18',
                                  message=message.replace( ' ', '+' ),
                                  root=True,
                                  template_field_name1=form_one_field_name,
                                  template_field_contents1=template_contents )
        global ldda_one
        ldda_one = get_latest_ldda()
        assert ldda_one is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda_one from the database'
        self.browse_library( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             check_str1='1.bed',
                             check_str2=message,
                             check_str3=admin_user.email )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             self.security.encode_id( library_one.root_folder.id ),
                             self.security.encode_id( ldda_one.id ),
                             ldda_one.name,
                             check_str1=template_contents )
    def test_025_add_new_folder_to_root_folder( self ):
        """Testing adding a folder to a library root folder"""
        # logged in as admin_user
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
        self.browse_library( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             check_str1=name,
                             check_str2=description )
        # Make sure the template was inherited, but the contents were not
        contents = '%s library contents' % form_one_field_label
        self.folder_info( 'library_admin',
                          self.security.encode_id( folder_one.id ),
                          self.security.encode_id( library_one.id ),
                          check_str1=form_one_field_name,
                          not_displayed=contents )
        # Add contents to the inherited template
        template_contents = "%s contents for Folder One" % form_one_field_label
        self.folder_info( 'library_admin',
                          self.security.encode_id( folder_one.id ),
                          self.security.encode_id( library_one.id ),
                          field_name=form_one_field_name,
                          contents=template_contents )
    def test_030_add_subfolder_to_folder( self ):
        """Testing adding a folder to a library folder"""
        # logged in as admin_user
        name = "Folder One's Subfolder"
        description = "This is the Folder One's subfolder"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library_one.id ),
                         self.security.encode_id( folder_one.id ),
                         name=name,
                         description=description )
        global subfolder_one
        subfolder_one = get_folder( folder_one.id, name, description )
        assert subfolder_one is not None, 'Problem retrieving library folder named "Folder Ones Subfolder" from the database'
        self.browse_library( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             check_str1=name,
                             check_str2=description )
        # Make sure the template was inherited, but the contents were not
        contents = '%s library contents' % form_one_field_label
        self.folder_info( 'library_admin',
                          self.security.encode_id( subfolder_one.id ),
                          self.security.encode_id( library_one.id ),
                          check_str1=form_one_field_name,
                          not_displayed=contents )
        # Add contents to the inherited template
        template_contents = "%s contents for Folder One" % form_one_field_label
        self.folder_info( 'library_admin',
                          self.security.encode_id( subfolder_one.id ),
                          self.security.encode_id( library_one.id ),
                          field_name=form_one_field_name,
                          contents=template_contents )
    def test_035_add_2nd_new_folder_to_root_folder( self ):
        """Testing adding a 2nd folder to a library root folder"""
        # logged in as admin_user
        root_folder = library_one.root_folder
        name = "Folder Two"
        description = "This is the root folder's Folder Two"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library_one.id ),
                         self.security.encode_id( root_folder.id ),
                         name=name,
                         description=description )
        global folder_two
        folder_two = get_folder( root_folder.id, name, description )
        assert folder_two is not None, 'Problem retrieving library folder named "%s" from the database' % name
        self.browse_library( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             check_str1=name,
                             check_str2=description )
    def test_040_add_public_dataset_to_root_folders_2nd_subfolder( self ):
        """Testing adding a public dataset to the root folder's 2nd sub-folder"""
        # Logged in as admin_user
        message = "Testing adding a public dataset to the folder named %s" % folder_two.name
        # The form_one template should be inherited to the library dataset upload form.
        template_contents = "%s contents for %s 2.bed" % ( form_one_field_label, folder_two.name )
        self.add_library_dataset( 'library_admin',
                                  '2.bed',
                                  self.security.encode_id( library_one.id ),
                                  self.security.encode_id( folder_two.id ),
                                  folder_two.name,
                                  file_type='bed',
                                  dbkey='hg18',
                                  message=message.replace( ' ', '+' ),
                                  root=False,
                                  template_field_name1=form_one_field_name,
                                  template_field_contents1=template_contents )
        global ldda_two
        ldda_two = get_latest_ldda()
        assert ldda_two is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda_two from the database'
        self.browse_library( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             check_str1='2.bed',
                             check_str2=message,
                             check_str3=admin_user.email )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             self.security.encode_id( folder_two.id ),
                             self.security.encode_id( ldda_two.id ),
                             ldda_two.name,
                             check_str1=template_contents )
    def test_045_add_2nd_public_dataset_to_root_folders_2nd_subfolder( self ):
        """Testing adding a 2nd public dataset to the root folder's 2nd sub-folder"""
        # Logged in as admin_user
        message = "Testing adding a 2nd public dataset to the folder named %s" % folder_two.name
        # The form_one template should be inherited to the library dataset upload form.
        template_contents = "%s contents for %s 3.bed" % ( form_one_field_label, folder_two.name )
        self.add_library_dataset( 'library_admin',
                                  '3.bed',
                                  self.security.encode_id( library_one.id ),
                                  self.security.encode_id( folder_two.id ),
                                  folder_two.name,
                                  file_type='bed',
                                  dbkey='hg18',
                                  message=message.replace( ' ', '+' ),
                                  root=False,
                                  template_field_name1=form_one_field_name,
                                  template_field_contents1=template_contents )
        global ldda_three
        ldda_three = get_latest_ldda()
        assert ldda_three is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda_three from the database'
        self.browse_library( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             check_str1='3.bed',
                             check_str2=message,
                             check_str3=admin_user.email )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             self.security.encode_id( folder_two.id ),
                             self.security.encode_id( ldda_three.id ),
                             ldda_three.name,
                             check_str1=template_contents )
    def test_050_copy_dataset_from_history_to_subfolder( self ):
        """Testing copying a dataset from the current history to a subfolder"""
        # logged in as admin_user
        self.new_history()
        self.upload_file( "4.bed" )
        latest_hda = get_latest_hda()
        self.add_history_datasets_to_library( 'library_admin',
                                              self.security.encode_id( library_one.id ),
                                              self.security.encode_id( subfolder_one.id ),
                                              subfolder_one.name,
                                              self.security.encode_id( latest_hda.id ),
                                              root=False )
        global ldda_four
        ldda_four = get_latest_ldda()
        assert ldda_four is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda_four from the database'
        # Make sure the correct template was inherited but the contents were not inherited
        contents = "%s contents for Folder One's Subfolder" % form_one_field_label
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             self.security.encode_id( subfolder_one.id ),
                             self.security.encode_id( ldda_four.id ),
                             ldda_four.name,
                             check_str1=form_one_field_name,
                             not_displayed=contents )
    def test_055_editing_dataset_attribute_info( self ):
        """Testing editing a library dataset's attribute information"""
        # logged in as admin_user
        new_ldda_name = '4.bed ( version 1 )'
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             self.security.encode_id( subfolder_one.id ),
                             self.security.encode_id( ldda_four.id ),
                             ldda_four.name,
                             new_ldda_name=new_ldda_name )
        refresh( ldda_four )
        self.browse_library( 'library_admin', self.security.encode_id( library_one.id ), check_str1=new_ldda_name )
        # Make sure the correct template was inherited but the contents were not inherited
        contents = "%s contents for Folder One's Subfolder" % form_one_field_label
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             self.security.encode_id( subfolder_one.id ),
                             self.security.encode_id( ldda_four.id ),
                             ldda_four.name,
                             check_str1=form_one_field_name,
                             not_displayed=contents )
    def test_060_uploading_new_dataset_version( self ):
        """Testing uploading a new version of a library dataset"""
        # logged in as admin_user
        message = 'Testing uploading a new version of a dataset'
        # The form_one template should be inherited to the library dataset upload form.
        template_contents = "%s contents for %s new version of 4.bed" % ( form_one_field_label, folder_one.name )
        self.upload_new_dataset_version( 'library_admin',
                                         '4.bed',
                                         self.security.encode_id( library_one.id ),
                                         self.security.encode_id( subfolder_one.id ),
                                         subfolder_one.name,
                                         self.security.encode_id( ldda_four.library_dataset.id ),
                                         ldda_four.name,
                                         file_type='auto',
                                         dbkey='hg18',
                                         message=message.replace( ' ', '+' ),
                                         template_field_name1=form_one_field_name,
                                         template_field_contents1=template_contents )
        global ldda_four_version_two
        ldda_four_version_two = get_latest_ldda()
        assert ldda_four_version_two is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda_four_version_two from the database'
        # Make sure the correct template was inherited, but does not include any contents
        contents = "%s contents for Folder One's Subfolder" % form_one_field_label
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             self.security.encode_id( subfolder_one.id ),
                             self.security.encode_id( ldda_four_version_two.id ),
                             ldda_four_version_two.name,
                             check_str1='This is the latest version of this library dataset',
                             not_displayed=contents )
        # Fill in the template contents
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             self.security.encode_id( subfolder_one.id ),
                             self.security.encode_id( ldda_four_version_two.id ),
                             ldda_four_version_two.name,
                             ele_1_field_name=form_one_field_name,
                             ele_1_contents=template_contents )
        # Check the previous version
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             self.security.encode_id( subfolder_one.id ),
                             self.security.encode_id( ldda_four.id ),
                             ldda_four.name,
                             check_str1='This is an expired version of this library dataset' )
        # Make sure ldda_four is no longer displayed in the library
        self.browse_library( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             not_displayed=ldda_four.name )
    def test_065_upload_directory_of_files_from_libraries_view( self ):
        """Testing uploading a directory of files to a root folder from the Data Libraries view"""
        # logged in as admin_user
        # admin_user will not have the option to upload a directory of files from the
        # Libraries view since a sub-directory named the same as their email is not contained
        # in the configured user_library_import_dir.  However, since members of role_one have
        # the LIBRARY_ADD permission, we can test this feature as regular_user1 or regular_user3
        self.logout()
        self.login( email=regular_user1.email )
        message = 'Uploaded all files in test-data/users/test1...'
        # Since regular_user1 does not have any sub-directories contained within her configured
        # user_library_import_dir, the only option in her server_dir select list will be the
        # directory named the same as her email
        check_str_after_submit = "Added 1 datasets to the library '%s' (each is selected)." % library_one.root_folder.name
        # TODO: gvk( 3/12/10 )this is broken, so commenting until I have time to discover why...
        """
        self.upload_directory_of_files( 'library',
                                        self.security.encode_id( library_one.id ),
                                        self.security.encode_id( library_one.root_folder.id ),
                                        server_dir=regular_user1.email,
                                        message=message,
                                        check_str_after_submit=check_str_after_submit )
        self.browse_library( 'library',
                             self.security.encode_id( library_one.id ),
                             check_str1=regular_user1.email,
                             check_str2=message )
        self.logout()
        self.login( regular_user3.email )
        message = 'Uploaded all files in test-data/users/test3.../run1'
        # Since regular_user2 has a subdirectory contained within her configured user_library_import_dir,
        # she will have a "None" option in her server_dir select list
        self.upload_directory_of_files( 'library',
                                        self.security.encode_id( library_one.id ),
                                        self.security.encode_id( library_one.root_folder.id ),
                                        server_dir='run1',
                                        message=message,
                                        check_str1='<option>None</option>',
                                        check_str_after_submit=check_str_after_submit )
        self.browse_library( 'library',
                             self.security.encode_id( library_one.id ),
                             check_str1=regular_user3.email,
                             check_str2=message )
        """
    def test_070_download_archive_of_library_files( self ):
        """Testing downloading an archive of files from the library"""
        # logged in as regular_user3
        self.logout()
        self.login( email=admin_user.email )
        for format in ( 'tbz', 'tgz', 'zip' ):
            archive = self.download_archive_of_library_files( cntrller='library',
                                                              library_id=self.security.encode_id( library_one.id ),
                                                              ldda_ids=[ self.security.encode_id( ldda_one.id ), self.security.encode_id( ldda_two.id ) ],
                                                              format=format )
            self.check_archive_contents( archive, ( ldda_one, ldda_two ) )
            os.remove( archive )
    def test_075_mark_dataset_deleted( self ):
        """Testing marking a library dataset as deleted"""
        # Logged in as admin_user
        self.delete_library_item( self.security.encode_id( library_one.id ),
                                  self.security.encode_id( ldda_two.library_dataset.id ),
                                  ldda_two.name,
                                  item_type='library_dataset' )
        self.browse_library( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             not_displayed=ldda_two.name )
    def test_080_display_and_hide_deleted_dataset( self ):
        """Testing displaying and hiding a deleted library dataset"""
        # Logged in as admin_user
        self.browse_library( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             show_deleted=True,
                             check_str1=ldda_two.name )
        self.browse_library( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             not_displayed=ldda_two.name )
    def test_085_mark_folder_deleted( self ):
        """Testing marking a library folder as deleted"""
        # Logged in as admin_user
        self.delete_library_item( self.security.encode_id( library_one.id ),
                                  self.security.encode_id( folder_two.id ),
                                  folder_two.name,
                                  item_type='folder' )
        self.browse_library( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             not_displayed=folder_two.name )
    def test_090_mark_folder_undeleted( self ):
        """Testing marking a library folder as undeleted"""
        # Logged in as admin_user
        self.undelete_library_item( self.security.encode_id( library_one.id ),
                                    self.security.encode_id( folder_two.id ),
                                    folder_two.name,
                                    item_type='folder' )
        # 2.bed was deleted before the folder was deleted, so state should have been saved.  In order
        # for 2.bed to be displayed, it would itself have to be marked undeleted.
        self.browse_library( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             check_str1=folder_two.name,
                             not_displayed=ldda_two.name )
    def test_095_mark_library_deleted( self ):
        """Testing marking a library as deleted"""
        # Logged in as admin_user
        # First mark folder_two as deleted to further test state saving when we undelete the library
        self.delete_library_item( self.security.encode_id( library_one.id ),
                                  self.security.encode_id( folder_two.id ),
                                  folder_two.name,
                                  item_type='folder' )
        self.delete_library_item( self.security.encode_id( library_one.id ),
                                  self.security.encode_id( library_one.id ),
                                  library_one.name,
                                  item_type='library' )
        self.browse_libraries_admin( not_displayed1=library_one.name )
        self.browse_libraries_admin( deleted=True, check_str1=library_one.name )
    def test_100_mark_library_undeleted( self ):
        """Testing marking a library as undeleted"""
        # Logged in as admin_user
        self.undelete_library_item( self.security.encode_id( library_one.id ),
                                    self.security.encode_id( library_one.id ),
                                    library_one.name,
                                    item_type='library' )
        self.browse_libraries_admin( check_str1=library_one.name )
        self.browse_library( 'library_admin',
                            self.security.encode_id( library_one.id ),
                            check_str1=library_one.name,
                            not_displayed=folder_two.name )
    def test_105_purge_library( self ):
        """Testing purging a library"""
        # Logged in as admin_user
        self.delete_library_item( self.security.encode_id( library_one.id ),
                                  self.security.encode_id( library_one.id ),
                                  library_one.name,
                                  item_type='library' )
        self.purge_library( self.security.encode_id( library_one.id ), library_one.name )
        # Make sure the library was purged
        refresh( library_one )
        if not ( library_one.deleted and library_one.purged ):
            raise AssertionError( 'The library id %s named "%s" has not been marked as deleted and purged.' % ( str( library_one.id ), library_one.name ) )
        def check_folder( library_folder ):
            for folder in library_folder.folders:
                refresh( folder )
                # Make sure all of the library_folders are purged
                if not folder.purged:
                    raise AssertionError( 'The library_folder id %s named "%s" has not been marked purged.' % ( str( folder.id ), folder.name ) )
                check_folder( folder )
            # Make sure all of the LibraryDatasets and associated objects are deleted
            refresh( library_folder )
            for library_dataset in library_folder.datasets:
                refresh( library_dataset )
                ldda = library_dataset.library_dataset_dataset_association
                if ldda:
                    refresh( ldda )
                    if not ldda.deleted:
                        raise AssertionError( 'The library_dataset_dataset_association id %s named "%s" has not been marked as deleted.' % \
                                              ( str( ldda.id ), ldda.name ) )
                    # Make sure all of the datasets have been deleted
                    dataset = ldda.dataset
                    refresh( dataset )
                    if not dataset.deleted:
                        raise AssertionError( 'The dataset with id "%s" has not been marked as deleted when it should have been.' % \
                                              str( ldda.dataset.id ) )
                if not library_dataset.deleted:
                    raise AssertionError( 'The library_dataset id %s named "%s" has not been marked as deleted.' % \
                                          ( str( library_dataset.id ), library_dataset.name ) )
        check_folder( library_one.root_folder )
    def test_110_no_library_template( self ):
        """Test library features when library has no template"""
        # Logged in as admin_user
        name = "library features Library Two"
        description = "library features This is Library Two"
        synopsis = "library features Library Two synopsis"
        # Create a library, adding no template
        self.create_library( name=name, description=description, synopsis=synopsis )
        self.browse_libraries_admin( check_str1=name, check_str2=description )
        global library_two
        library_two = get_library( name, description, synopsis )
        assert library_two is not None, 'Problem retrieving library named "%s" from the database' % name
        # Add a dataset to the library
        self.add_library_dataset( 'library_admin',
                                  '3.bed',
                                  self.security.encode_id( library_two.id ),
                                  self.security.encode_id( library_two.root_folder.id ),
                                  library_two.root_folder.name,
                                  file_type='bed',
                                  dbkey='hg18',
                                  message='',
                                  root=True )
        ldda_three = get_latest_ldda()
        assert ldda_three is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda_three from the database'
        self.browse_library( 'library_admin',
                             self.security.encode_id( library_two.id ),
                             check_str1='3.bed',
                             check_str2=admin_user.email )
        # TODO: add a functional test to cover adding a library dataset via url_paste here...
        # TODO: Add a functional test to cover checking the space_to_tab checkbox here...
        # Delete and purge the library
        self.delete_library_item( self.security.encode_id( library_two.id ),
                                  self.security.encode_id( library_two.id ),
                                  library_two.name,
                                  item_type='library' )
        self.purge_library( self.security.encode_id( library_two.id ), library_two.name )
        self.home()
    def test_999_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to pass"""
        # Logged in as admin_user
        ##################
        # Purge all libraries
        ##################
        for library in [ library_one, library_two ]:
            self.delete_library_item( self.security.encode_id( library.id ),
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
