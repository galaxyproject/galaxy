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

    def test_005_create_libraries( self ):
        """Testing creating libraries used in this script, then renaming one of them"""
        # Logged in as admin_user
        for index in range( 0, 3 ):
            name = 'library%s' % str( index + 1 )
            description = '%s description' % name
            synopsis = '%s synopsis' % name
            self.create_library( name=name, description=description, synopsis=synopsis )
            self.browse_libraries_admin( strings_displayed=[ name, description ] )
        # Get the libraries for later use
        global library1
        library1 = get_library( 'library1', 'library1 description', 'library1 synopsis' )
        assert library1 is not None, 'Problem retrieving library (library1) from the database'
        global library2
        library2 = get_library( 'library2', 'library2 description', 'library2 synopsis' )
        assert library2 is not None, 'Problem retrieving library (library2) from the database'
        global library3
        library3 = get_library( 'library3', 'library3 description', 'library3 synopsis' )
        assert library3 is not None, 'Problem retrieving library (library3) from the database'
        # Rename the library
        new_name = "library1 new name"
        new_description = "library1 new description"
        new_synopsis = "library1 new synopsis"
        self.library_info( 'library_admin',
                            self.security.encode_id( library1.id ),
                            library1.name,
                            new_name=new_name,
                            new_description=new_description,
                            new_synopsis=new_synopsis )
        self.browse_libraries_admin( strings_displayed=[ new_name, new_description ] )
        # Reset the library back to the original name and description
        self.library_info( 'library_admin',
                            self.security.encode_id( library1.id ),
                            library1.name,
                            new_name='library1',
                            new_description='library1 description',
                            new_synopsis='library1 synopsis' )
        refresh( library1 )

    def test_030_add_folder_to_library1( self ):
        """Testing adding a folder to a library1"""
        # logged in as admin_user
        root_folder = library1.root_folder
        name = "folder1"
        description = "folder1 description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library1.id ),
                         self.security.encode_id( library1.root_folder.id ),
                         name=name,
                         description=description )
        global folder1
        folder1 = get_folder( root_folder.id, name, description )
        assert folder1 is not None, 'Problem retrieving library folder named "%s" from the database' % name
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ folder1.name, folder1.description ] )

    def test_035_add_subfolder_to_folder( self ):
        """Testing adding a folder to a folder"""
        # logged in as admin_user
        name = "Folder One's Subfolder"
        description = "This is the Folder One's subfolder"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library1.id ),
                         self.security.encode_id( folder1.id ),
                         name=name,
                         description=description )
        global subfolder1
        subfolder1 = get_folder( folder1.id, name, description )
        assert subfolder1 is not None, 'Problem retrieving subfolder1 from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ subfolder1.name, subfolder1.description ] )

    def test_040_add_2nd_folder_to_library1( self ):
        """Testing adding a 2nd folder to a library1"""
        # logged in as admin_user
        name = "folder2"
        description = "folder2 description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library1.id ),
                         self.security.encode_id( library1.root_folder.id ),
                         name=name,
                         description=description )
        global folder2
        folder2 = get_folder( library1.root_folder.id, name, description )
        assert folder2 is not None, 'Problem retrieving library folder named "%s" from the database' % name
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ folder2.name, folder2.description ] )

    def test_045_add_public_dataset_to_folder2( self ):
        """Testing adding a public dataset to folder2"""
        # Logged in as admin_user
        filename = '2.bed'
        ldda_message = "Testing uploading %s" % filename
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library1.id ),
                                     folder_id=self.security.encode_id( folder2.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'Upload files' ] )
        global ldda2
        ldda2 = get_latest_ldda_by_name( filename )
        assert ldda2 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda2 from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ ldda2.name, ldda2.message, 'bed' ] )

    def test_050_add_2nd_public_dataset_to_folder2( self ):
        """Testing adding a 2nd public dataset folder2"""
        # Logged in as admin_user
        filename='3.bed'
        ldda_message = "Testing uploading %s" % filename
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library1.id ),
                                     folder_id=self.security.encode_id( folder2.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'Upload files' ] )
        global ldda3
        ldda3 = get_latest_ldda_by_name( filename )
        assert ldda3 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda3 from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ ldda3.name, ldda3.message, 'bed' ] )

    def test_055_copy_dataset_from_history_to_subfolder( self ):
        """Testing copying a dataset from the current history to a subfolder"""
        # logged in as admin_user
        self.new_history()
        filename = '4.bed'
        self.upload_file( filename )
        latest_hda = get_latest_hda()
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library1.id ),
                                     folder_id=self.security.encode_id( subfolder1.id ),
                                     upload_option='import_from_history',
                                     hda_ids=self.security.encode_id( latest_hda.id ),
                                     ldda_message='Imported from history',
                                     strings_displayed=[ 'Active datasets in your current history' ] )
        global ldda4
        ldda4 = get_latest_ldda_by_name( filename )
        assert ldda4 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda4 from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ ldda4.name, ldda4.message, 'bed' ] )

    def test_060_editing_dataset_attribute_info( self ):
        """Testing editing a library dataset's attribute information"""
        # logged in as admin_user
        new_ldda_name = '4.bed ( version 1 )'
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library1.id ),
                             self.security.encode_id( subfolder1.id ),
                             self.security.encode_id( ldda4.id ),
                             ldda4.name,
                             new_ldda_name=new_ldda_name )
        refresh( ldda4 )
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ new_ldda_name, ldda4.message ] )

    def test_065_uploading_new_dataset_version( self ):
        """Testing uploading a new version of a library dataset"""
        # logged in as admin_user
        filename = '4.bed'
        ldda_message = 'Testing uploading a new version of a dataset'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library1.id ),
                                     folder_id=self.security.encode_id( subfolder1.id ),
                                     replace_id=self.security.encode_id( ldda4.library_dataset.id ),
                                     filename=filename,
                                     file_type='auto',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'Upload files', 'You are currently selecting a new file to replace' ] )
        global ldda4_version2
        ldda4_version2 = get_latest_ldda_by_name( filename )
        assert ldda4_version2 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda4_version2 from the database'
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library1.id ),
                             self.security.encode_id( subfolder1.id ),
                             self.security.encode_id( ldda4_version2.id ),
                             ldda4_version2.name,
                             strings_displayed=[ 'This is the latest version of this library dataset' ] )
        # Check the previous version
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library1.id ),
                             self.security.encode_id( subfolder1.id ),
                             self.security.encode_id( ldda4.id ),
                             ldda4.name,
                             strings_displayed=[ 'This is an expired version of this library dataset' ] )
        # Make sure ldda4 is no longer displayed in the library
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_not_displayed=[ ldda4.name, ldda4.message ] )

    def test_070_upload_directory_of_files_from_libraries_view( self ):
        """Testing uploading a directory of files to a root folder from the Data Libraries view"""
        # logged in as admin_user
        # admin_user will not have the option to upload a directory of files from the
        # Libraries view since a sub-directory named the same as their email is not contained
        # in the configured user_library_import_dir ( in the test_data directory, only  regular_user1
        # and regular_user3 have directories ).  We'll need to give these 2 user LIBRARY_ADD permission
        # on library1 to test this feature.
        permissions_in = [ 'LIBRARY_ADD' ]
        permissions_out = [ 'LIBRARY_ACCESS', 'LIBRARY_MODIFY', 'LIBRARY_MANAGE' ]
        role_ids = '%s,%s' % ( str( regular_user1_private_role.id ), str( regular_user3_private_role.id ) )
        self.library_permissions( self.security.encode_id( library1.id ),
                                  library1.name,
                                  role_ids,
                                  permissions_in,
                                  permissions_out )
        self.logout()
        # Now that we have permissions set on the library, we can proceed to test uploading files
        self.login( email=regular_user1.email )
        ldda_message = 'Uploaded all files in test-data/users/test1...'
        # Since regular_user1 does not have any sub-directories contained within her configured
        # user_library_import_dir, the only option in her server_dir select list will be the
        # directory named the same as her email
        self.upload_library_dataset( cntrller='library',
                                     library_id=self.security.encode_id( library1.id ),
                                     folder_id=self.security.encode_id( library1.root_folder.id ),
                                     upload_option='upload_directory',
                                     server_dir=regular_user1.email,
                                     ldda_message=ldda_message,
                                     strings_displayed = [ "Upload a directory of files" ] )
        self.logout()
        self.login( regular_user3.email )
        ldda_message = 'Uploaded all files in test-data/users/test3.../run1'
        # Since regular_user2 has a subdirectory contained within her configured user_library_import_dir,
        # she will have a "None" option in her server_dir select list
        self.upload_library_dataset( cntrller='library',
                                     library_id=self.security.encode_id( library1.id ),
                                     folder_id=self.security.encode_id( library1.root_folder.id ),
                                     upload_option='upload_directory',
                                     server_dir='run1',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'Upload a directory of files', '<option>None</option>' ] )

    def test_075_download_archive_of_library_files( self ):
        """Testing downloading an archive of files from library1"""
        # logged in as regular_user3
        self.logout()
        self.login( email=admin_user.email )
        filename = '1.bed'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library1.id ),
                                     folder_id=self.security.encode_id( library1.root_folder.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     strings_displayed=[ 'Upload files' ] )
        global ldda1
        ldda1 = get_latest_ldda_by_name( filename )
        assert ldda1 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda1 from the database'
        for format in ( 'tbz', 'tgz', 'zip' ):
            archive = self.download_archive_of_library_files( cntrller='library',
                                                              library_id=self.security.encode_id( library1.id ),
                                                              ldda_ids=[ self.security.encode_id( ldda1.id ), self.security.encode_id( ldda2.id ) ],
                                                              format=format )
            self.check_archive_contents( archive, ( ldda1, ldda2 ) )
            os.remove( archive )

    def test_080_check_libraries_for_uploaded_directories_of_files( self ):
        """Testing the results of uploading directories of files to library1"""
        # We'll make sure the directories of files were uploaded in test_070... above.
        # We do this here because the check would generally fail if we did it in the
        # test_070... method since the files would not finish uploading before the check
        # was done.  Hopefully doing the check here will allow for enough time...
        ldda_message = 'Uploaded all files in test-data/users/test1...'
        self.browse_library( 'library',
                             self.security.encode_id( library1.id ),
                             strings_displayed=[ 'fasta', ldda_message, '1.fasta' ] )
        ldda_message = 'Uploaded all files in test-data/users/test3.../run1'
        self.browse_library( 'library',
                             self.security.encode_id( library1.id ),
                             strings_displayed=[ 'fasta', ldda_message, '2.fasta' ] )

    def test_085_mark_ldda2_deleted( self ):
        """Testing marking ldda2 as deleted"""
        # Logged in as admin_user
        self.delete_library_item( 'library_admin',
                                  self.security.encode_id( library1.id ),
                                  self.security.encode_id( ldda2.library_dataset.id ),
                                  ldda2.name,
                                  item_type='library_dataset' )
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_not_displayed=[ ldda2.name, ldda2.message ] )

    def test_090_display_and_hide_deleted_ldda2( self ):
        """Testing displaying and hiding a deleted ldda2"""
        # Logged in as admin_user
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             show_deleted=True,
                             strings_displayed=[ ldda2.name, ldda2.message ] )
        self.browse_library( 'library_admin',
                             self.security.encode_id( library1.id ),
                             strings_not_displayed=[ ldda2.name, ldda2.message ] )

    def test_095_mark_folder2_deleted( self ):
        """Testing marking folder2 as deleted"""
        # Logged in as admin_user
        self.delete_library_item( 'library_admin',
                                  self.security.encode_id( library1.id ),
                                  self.security.encode_id( folder2.id ),
                                  folder2.name,
                                  item_type='folder' )
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_not_displayed=[ folder2.name ] )

    def test_100_mark_folder_undeleted( self ):
        """Testing marking a library folder as undeleted"""
        # Logged in as admin_user
        self.undelete_library_item( 'library_admin',
                                    self.security.encode_id( library1.id ),
                                    self.security.encode_id( folder2.id ),
                                    folder2.name,
                                    item_type='folder' )
        # 2.bed was deleted before the folder was deleted, so state should have been saved.  In order
        # for 2.bed to be displayed, it would itself have to be marked undeleted.
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ folder2.name ],
                             strings_not_displayed=[ ldda2.name ] )

    def test_105_mark_library_deleted( self ):
        """Testing marking a library as deleted"""
        # Logged in as admin_user
        # First mark folder2 as deleted to further test state saving when we undelete the library
        self.delete_library_item( 'library_admin',
                                  self.security.encode_id( library1.id ),
                                  self.security.encode_id( folder2.id ),
                                  folder2.name,
                                  item_type='folder' )
        self.delete_library_item( 'library_admin',
                                  self.security.encode_id( library1.id ),
                                  self.security.encode_id( library1.id ),
                                  library1.name,
                                  item_type='library' )
        self.browse_libraries_admin( strings_not_displayed=[ library1.name ] )
        self.browse_libraries_admin( deleted=True, strings_displayed=[ library1.name ] )

    def test_110_mark_library_undeleted( self ):
        """Testing marking a library as undeleted"""
        # Logged in as admin_user
        self.undelete_library_item( 'library_admin',
                                    self.security.encode_id( library1.id ),
                                    self.security.encode_id( library1.id ),
                                    library1.name,
                                    item_type='library' )
        self.browse_libraries_admin( strings_displayed=[ library1.name ] )
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ library1.name ],
                             strings_not_displayed=[ folder2.name ] )

    def test_115_purge_library( self ):
        """Testing purging a library"""
        # Logged in as admin_user
        self.delete_library_item( 'library_admin',
                                  self.security.encode_id( library1.id ),
                                  self.security.encode_id( library1.id ),
                                  library1.name,
                                  item_type='library' )
        self.purge_library( self.security.encode_id( library1.id ), library1.name )
        # Make sure the library was purged
        refresh( library1 )
        if not ( library1.deleted and library1.purged ):
            raise AssertionError( 'The library id %s named "%s" has not been marked as deleted and purged.' % ( str( library1.id ), library1.name ) )
    
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
        check_folder( library1.root_folder )

    def test_120_populate_public_library2( self ):
        """Testing library datasets within a library"""
        # Logged in as admin_user
        # Add a folder named Three to library2 root
        root_folder = library2.root_folder
        name = "One"
        description = "One description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library2.id ),
                         self.security.encode_id( root_folder.id ),
                         name=name,
                         description=description )
        global folder3
        folder3 = get_folder( root_folder.id, name, description )
        assert folder3 is not None, 'Problem retrieving library folder named "%s" from the database' % name
        # Upload dataset 1.bed to folder One
        filename = '1.bed'
        ldda_message = "Testing uploading %s" % filename
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library2.id ),
                                     folder_id=self.security.encode_id( folder3.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'Upload files' ] )
        global ldda5
        ldda5 = get_latest_ldda_by_name( filename )
        assert ldda5 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda5 from the database'
        # Add a sub-folder named Two to folder One
        name = "Two"
        description = "Two description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library2.id ),
                         self.security.encode_id( folder3.id ),
                         name=name,
                         description=description )
        global folder4
        folder4 = get_folder( folder3.id, name, description )
        assert folder4 is not None, 'Problem retrieving library folder named "%s" from the database' % name
        # Upload dataset 2.bed to folder Two
        filename = '2.bed'
        ldda_message = "Testing uploading %s" % filename
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library2.id ),
                                     folder_id=self.security.encode_id( folder4.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'Upload files' ] )
        global ldda6
        ldda6 = get_latest_ldda_by_name( filename )
        assert ldda6 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda6 from the database'
        # Add a folder named Three to library2 root
        name = "Three"
        description = "Three description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library2.id ),
                         self.security.encode_id( root_folder.id ),
                         name=name,
                         description=description )
        global folder5
        folder5 = get_folder( root_folder.id, name, description )
        assert folder5 is not None, 'Problem retrieving library folder named "%s" from the database' % name
        # Upload dataset 3.bed to library2 root folder
        filename = '3.bed'
        ldda_message = "Testing uploading %s" % filename
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library2.id ),
                                     folder_id=self.security.encode_id( root_folder.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'Upload files' ] )
        global ldda7
        ldda7 = get_latest_ldda_by_name( filename )
        assert ldda7 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda7 from the database'

    def test_125_move_dataset_within_library2( self ):
        """Testing moving a dataset within library2"""
        # Logged in as admin_user
        # Move 3.bed to folder Three
        self.move_library_item( cntrller='library_admin',
                                item_type='ldda',
                                item_id=self.security.encode_id( ldda7.id ),
                                source_library_id=self.security.encode_id( library2.id ),
                                make_target_current=True,
                                target_folder_id=self.security.encode_id( folder5.id ),
                                strings_displayed=[ 'Move data library items',
                                                    '3.bed' ],
                                strings_displayed_after_submit=[ '1 dataset moved to folder (Three) within data library (library2)' ] )

    def test_130_move_folder_to_another_library( self ):
        """Testing moving a folder to another library"""
        # Logged in as admin_user
        # Move folder Three which now includes 3.bed to library3
        self.move_library_item( cntrller='library_admin',
                                item_type='folder',
                                item_id=self.security.encode_id( folder5.id ),
                                source_library_id=self.security.encode_id( library2.id ),
                                make_target_current=False,
                                target_library_id=self.security.encode_id( library3.id ),
                                target_folder_id=self.security.encode_id( library3.root_folder.id ),
                                strings_displayed=[ 'Move data library items',
                                                    'Three' ],
                                strings_displayed_after_submit=[ 'Moved folder (Three) to folder (library3) within data library (library3)' ] )
        # Make sure folder Three is not longer in library2
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library2.id ),
                             strings_displayed=[ folder4.name, folder4.description ],
                             strings_not_displayed=[ folder5.name, folder5.description ] )
        # Make sure folder Three was moved to library3
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library3.id ),
                             strings_displayed=[ folder5.name, folder5.description, ldda7.name ] )

    def test_135_upload_unsorted_bam_to_library_using_file_path_with_link_to_file( self ):
        """Test uploading 3unsorted.bam, using filesystem_paths option in combination with link_to_files"""
        filename = '3unsorted.bam'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library2.id ),
                                     folder_id=self.security.encode_id( library2.root_folder.id ),
                                     upload_option='upload_paths',
                                     link_data_only='link_to_files',
                                     filesystem_paths='test-data/3unsorted.bam' )
        global ldda8
        ldda8 = get_latest_ldda_by_name( filename )
        assert ldda8 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda8 from the database'
        # The upload above should produce an error condition in the uploaded library dataset since
        # the uploaded bam file is not sorted, and we are linking to the file.
        self.ldda_info( cntrller='library_admin',
                        library_id=self.security.encode_id( library2.id ),
                        folder_id=self.security.encode_id( library2.root_folder.id ),
                        ldda_id=self.security.encode_id( ldda8.id ),
                        strings_displayed=[ 'The uploaded files need grooming, so change your <b>Copy data into Galaxy?</b> selection to be' ] )

    def test_999_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to pass"""
        # Logged in as admin_user
        ##################
        # Purge all libraries
        ##################
        for library in [ library1, library2, library3 ]:
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
