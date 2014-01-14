from base.twilltestcase import *
from base.test_db_util import *


# TODO: Functional tests start failing at 050, fix or eliminate rest of tests.
class TestLibrarySecurity( TwillTestCase ):
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
        # Create Role1: admin_user, regular_user1, regular_user3
        name = 'Role1'
        description = "Role1 description"
        self.create_role( name=name,
                          description=description,
                          in_user_ids=[ str( admin_user.id ), str( regular_user1.id ), str( regular_user3.id ) ],
                          in_group_ids=[],
                          create_group_for_role='no',
                          private_role=admin_user.email )
        global role1
        role1 = get_role_by_name( name )
        # Create Group1: regular_user1, admin_user, regular_user3
        name = 'Group1'
        self.create_group( name=name, in_user_ids=[ str( regular_user1.id ) ], in_role_ids=[ str( role1.id ) ] )
        global group1
        group1 = get_group_by_name( name )
        assert group1 is not None, 'Problem retrieving group named "Group1" from the database'
        # NOTE: To get this to work with twill, all select lists on the ~/admin/role page must contain at least
        # 1 option value or twill throws an exception, which is: ParseError: OPTION outside of SELECT
        # Due to this bug in twill, we create the role, we bypass the page and visit the URL in the
        # associate_users_and_groups_with_role() method.
        #
        #create Role2: admin_user, regular_user1, regular_user3
        name = 'Role2'
        description = 'Role2 description'
        private_role = admin_user.email
        self.create_role( name=name,
                          description=description,
                          in_user_ids=[ str( admin_user.id ) ],
                          in_group_ids=[ str( group1.id ) ],
                          private_role=private_role )
        global role2
        role2 = get_role_by_name( name )
        assert role2 is not None, 'Problem retrieving role named "Role2" from the database'
    def test_010_create_libraries( self ):
        """Creating new libraries used in this script"""
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
    def test_015_restrict_access_to_library1( self ):
        """Testing restricting access to library1"""
        # Logged in as admin_user
        # Make sure library1 is public
        assert 'access library' not in [ a.action for a in library1.actions ], 'Library %s is not public when first created' % library1.name
        # Set permissions on the library, sort for later testing.
        permissions_in = [ k for k, v in galaxy.model.Library.permitted_actions.items() ]
        permissions_out = []
        # Role1 members are: admin_user, regular_user1, regular_user3.  Each of these users will be permitted for
        # LIBRARY_ACCESS, LIBRARY_ADD, LIBRARY_MODIFY, LIBRARY_MANAGE on library1 and its contents.
        self.library_permissions( self.security.encode_id( library1.id ),
                                  library1.name,
                                  str( role1.id ),
                                  permissions_in,
                                  permissions_out )
        # Make sure the library is accessible by admin_user
        self.visit_url( '%s/library/browse_libraries' % self.url )
        self.check_page_for_string( library1.name )
        # Make sure the library is not accessible by regular_user2 since regular_user2 does not have Role1.
        self.logout()
        self.login( email=regular_user2.email )
        self.visit_url( '%s/library/browse_libraries' % self.url )
        try:
            self.check_page_for_string( library1.name )
            raise AssertionError, 'Library %s is accessible by %s when it should be restricted' % ( library1.name, regular_user2.email )
        except:
            pass
        self.logout()
        self.login( email=admin_user.email )
    def test_020_add_folder_to_library1( self ):
        """Testing adding a folder1 to a library1"""
        # logged in as admin_user
        root_folder = library1.root_folder
        name = "Folder1"
        description = "Folder1 description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library1.id ),
                         self.security.encode_id( root_folder.id ),
                         name=name,
                         description=description )
        global folder1
        folder1 = get_folder( root_folder.id, name, description )
        assert folder1 is not None, 'Problem retrieving folder1 from the database'
    def test_025_create_ldda1_with_private_role_restriction( self ):
        """Testing create ldda1 with a private role restriction"""
        # Logged in as admin_user
        #
        # Library1 LIBRARY_ACCESS = Role1: admin_user, regular_user1, regular_user3
        #
        # Add a dataset restricted by the following:
        # DATASET_MANAGE_PERMISSIONS = admin_user via DefaultUserPermissions
        # DATASET_ACCESS = regular_user1 private role via this test method
        # LIBRARY_ADD = "Role1" via inheritance from parent folder
        # LIBRARY_MODIFY = "Role1" via inheritance from parent folder
        # LIBRARY_MANAGE = "Role1" via inheritance from parent folder
        #
        # This means that only regular_user1 can see the dataset from the Data Libraries view
        filename = '1.bed'
        ldda_message ='ldda1'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library1.id ),
                                     folder_id=self.security.encode_id( folder1.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     roles=[ str( regular_user1_private_role.id ) ],
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'Upload files' ] )
        global ldda1
        ldda1 = get_latest_ldda_by_name( filename )
        assert ldda1 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda1 from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ ldda1.name, ldda1.message, 'bed' ] )
    def test_030_access_ldda1_with_private_role_restriction( self ):
        """Testing accessing ldda1 with a private role restriction"""
        # Logged in as admin_user
        #
        # LIBRARY_ACCESS = Role1: admin_user, regular_user1, regular_user3.  Each of these users will be permitted for
        # LIBRARY_ACCESS, LIBRARY_ADD, LIBRARY_MODIFY, LIBRARY_MANAGE on this library and its contents.
        #
        # Legitimate roles displayed on the permission form are as follows:
        # 'Role1' since the LIBRARY_ACCESS permission is associated with Role1.  # Role one members are: admin_user, regular_user1, regular_user3.
        # 'test@bx.psu.edu' ( admin_user's private role ) since admin_user has Role1
        # 'Role2' since admin_user has Role2
        # 'Role Three' since admin_user has Role Three
        # 'test1@bx.psu.edu' ( regular_user1's private role ) since regular_user1 has Role1
        # 'test3@bx.psu.edu' ( regular_user3's private role ) since regular_user3 has Role1
        #
        # admin_user should not be able to see 1.bed from the analysis view's access libraries
        self.browse_library( cntrller='library',
                             library_id=self.security.encode_id( library1.id ),
                             strings_not_displayed=[ folder1.name, ldda1.name, ldda1.message ] )
        self.logout()
        # regular_user1 should be able to see 1.bed from the Data Libraries view
        # since it was associated with regular_user1's private role
        self.login( email=regular_user1.email )
        self.browse_library( cntrller='library',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ folder1.name, ldda1.name, ldda1.message ] )
        self.logout()
        # regular_user2 should not be to see library1 since they do not have 
        # Role1 which is associated with the LIBRARY_ACCESS permission
        self.login( email=regular_user2.email )
        self.browse_libraries_regular_user( strings_not_displayed=[ library1.name ] )
        self.logout()
        # regular_user3 should not be able to see 1.bed from the analysis view's access librarys
        self.login( email=regular_user3.email )
        self.browse_library( cntrller='library',
                             library_id=self.security.encode_id( library1.id ),
                             strings_not_displayed=[ folder1.name ] )
        self.logout()
        self.login( email=admin_user.email )
    def test_035_change_ldda1_access_permission( self ):
        """Testing changing the access permission on ldda1 with a private role restriction"""
        # Logged in as admin_user
        # We need admin_user to be able to access 1.bed
        permissions_in = [ k for k, v in galaxy.model.Dataset.permitted_actions.items() ]
        for k, v in galaxy.model.Library.permitted_actions.items():
            if k != 'LIBRARY_ACCESS':
                permissions_in.append( k )
        permissions_out = []
        # Attempt to associate multiple roles with the library dataset, with one of the
        # roles being private.
        role_ids_str = '%s,%s' % ( str( role1.id ), str( admin_user_private_role.id ) )
        check_str = "At least 1 user must have every role associated with accessing datasets.  "
        check_str += "Since you are associating more than 1 role, no private roles are allowed."
        self.ldda_permissions( 'library_admin',
                                self.security.encode_id( library1.id ),
                                self.security.encode_id( folder1.id ),
                                self.security.encode_id( ldda1.id ),
                                role_ids_str,
                                permissions_in,
                                permissions_out,
                                strings_displayed=[ check_str ] )
        role_ids_str = str( role1.id )
        self.ldda_permissions( 'library_admin',
                                self.security.encode_id( library1.id ),
                                self.security.encode_id( folder1.id ),
                                self.security.encode_id( ldda1.id ),
                                role_ids_str,
                                permissions_in,
                                permissions_out,
                                ldda_name=ldda1.name )
        # admin_user should now be able to see 1.bed from the analysis view's access libraries
        self.browse_library( cntrller='library',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ ldda1.name, ldda1.message ] )
    def test_040_create_ldda2_with_role2_associated_with_group_and_users( self ):
        """Testing creating ldda2 with a role that is associated with a group and users"""
        # Logged in as admin_user
        # Add a dataset restricted by role2, which is currently associated as follows:
        # groups: group1
        # users: test@bx.psu.edu, test1@bx.psu.edu via group1
        #
        # We first need to make library1 public, but leave its contents permissions unchanged
        self.make_library_item_public( self.security.encode_id( library1.id ),
                                       self.security.encode_id( library1.id ),
                                       item_type='library',
                                       contents=False,
                                       library_name=library1.name )
        refresh( library1 )
        filename = '2.bed'
        ldda_message = 'ldda2'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library1.id ),
                                     folder_id=self.security.encode_id( folder1.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg17',
                                     roles=[ str( role2.id ) ],
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'Upload files' ] )
        global ldda2
        ldda2 = get_latest_ldda_by_name( filename )
        assert ldda2 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda2 from the database'
        self.browse_library( cntrller='library',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ ldda2.name, ldda2.message, 'bed' ] )
    def test_045_accessing_ldda2_with_role_associated_with_group_and_users( self ):
        """Testing accessing ldda2 with a role that is associated with a group and users"""
        # Logged in as admin_user
        # admin_user should be able to see 2.bed since she is associated with role2
        self.browse_library( cntrller='library',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ ldda2.name, ldda2.message, 'bed' ] )
        self.logout()
        # regular_user1 should be able to see 2.bed since she is associated with group_two
        self.login( email = regular_user1.email )
        self.browse_library( cntrller='library',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ folder1.name, ldda2.name, ldda2.message, 'bed' ] )
        # Check the permissions on the dataset 2.bed - they are as folows:
        # DATASET_MANAGE_PERMISSIONS = test@bx.psu.edu
        # DATASET_ACCESS = Role2
        #                  Role2 associations: test@bx.psu.edu and Group2
        #                  Group2 members: Role1, Role2, test1@bx.psu.edu
        #                  Role1 associations: test@bx.psu.edu, test1@bx.psu.edu, test3@bx.psu.edu
        # LIBRARY_ADD = Role1
        #               Role1 aassociations: test@bx.psu.edu, test1@bx.psu.edu, test3@bx.psu.edu
        # LIBRARY_MODIFY = Role1
        #                  Role1 aassociations: test@bx.psu.edu, test1@bx.psu.edu, test3@bx.psu.edu
        # LIBRARY_MANAGE = Role1
        #                  Role1 aassociations: test@bx.psu.edu, test1@bx.psu.edu, test3@bx.psu.edu        
        self.ldda_edit_info( 'library',
                             self.security.encode_id( library1.id ),
                             self.security.encode_id( folder1.id ),
                             self.security.encode_id( ldda2.id ),
                             ldda2.name,
                             strings_displayed=[ '2.bed',
                                                 'This is the latest version of this library dataset',
                                                 'Edit attributes of 2.bed' ] )
        self.import_datasets_to_histories( cntrller='library',
                                           library_id=self.security.encode_id( library1.id ),
                                           ldda_ids=self.security.encode_id( ldda2.id ),
                                           new_history_name='goodbye',
                                           strings_displayed=[ '1 dataset imported into 1 history' ] )
        self.logout()
        # regular_user2 should not be able to see ldda2
        self.login( email=regular_user2.email )
        self.browse_library( cntrller='library',
                             library_id=self.security.encode_id( library1.id ),
                             strings_not_displayed=[ folder1.name, ldda2.name, ldda2.message ] )
        
        self.logout()
        # regular_user3 should not be able to see ldda2
        self.login( email=regular_user3.email )
        self.browse_library( cntrller='library',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ folder1.name ],
                             strings_not_displayed=[ ldda2.name, ldda2.message ] )
        self.logout()
        self.login( email=admin_user.email )
        # Now makse ldda2 publicly accessible
        self.make_library_item_public( self.security.encode_id( library1.id ),
                                       self.security.encode_id( ldda2.id ),
                                       item_type='ldda',
                                       ldda_name=ldda2.name )
        self.logout()
        # regular_user2 should now be able to see ldda2
        self.login( email=regular_user2.email )
        self.browse_library( cntrller='library',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ folder1.name, ldda2.name, ldda2.message ] )
        self.logout()
        self.login( email=admin_user.email )
        # Now make folder1 publicly acessible
        self.make_library_item_public( self.security.encode_id( library1.id ),
                                       self.security.encode_id( folder1.id ),
                                       item_type='folder',
                                       folder_name=folder1.name )
        self.logout()
        # regular_user3 should now be able to see ldda1
        self.login( email=regular_user3.email )
        self.browse_library( cntrller='library',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ folder1.name, ldda1.name, ldda1.message ] )
        self.logout()
        self.login( email=admin_user.email )
    def test_050_upload_directory_of_files_from_admin_view( self ):
        """Testing uploading a directory of files to library1 from the Admin view"""
        # logged in as admin_user
        ldda_message = 'This is a test for uploading a directory of files'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library1.id ),
                                     folder_id=self.security.encode_id( library1.root_folder.id ),
                                     upload_option='upload_directory',
                                     server_dir='library',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ "Upload a directory of files" ] )
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ 'bed', ldda_message ] )
    def test_055_change_permissions_on_datasets_uploaded_from_library_dir( self ):
        """Testing changing the permissions on datasets uploaded from a directory from the Admin view"""
        # logged in as admin_user
        # It would be nice if twill functioned such that the above test resulted in a
        # form with the uploaded datasets selected, but it does not ( they're not checked ),
        # so we'll have to simulate this behavior ( not ideal ) for the 'edit' action.  We
        # first need to get the ldda.id for the 3 new datasets
        latest_3_lddas = get_latest_lddas( 3 )
        ldda_ids = ''
        for ldda in latest_3_lddas:
            ldda_ids += '%s,' % self.security.encode_id( ldda.id )
        ldda_ids = ldda_ids.rstrip( ',' )
        # Set permissions
        self.ldda_permissions( 'library_admin',
                               self.security.encode_id( library1.id ),
                               self.security.encode_id( folder1.id ),
                               ldda_ids,
                               str( role1.id ),
                               permissions_in=[ 'DATASET_ACCESS', 'LIBRARY_MANAGE' ],
                               strings_displayed=[ 'Permissions updated for 3 datasets.' ] )
        # Make sure the permissions have been correctly updated for the 3 datasets.  Permissions should 
        # be all of the above on any of the 3 datasets that are imported into a history.
        def check_edit_page( lddas, strings_displayed=[], strings_not_displayed=[] ):
            for ldda in lddas:
                # Import each library dataset into our history
                self.import_datasets_to_histories( cntrller='library',
                                                   library_id=self.security.encode_id( library1.id ),
                                                   ldda_ids=self.security.encode_id( ldda.id ),
                                                   new_history_name='hello' )
                # Determine the new HistoryDatasetAssociation id created when the library dataset was imported into our history
                last_hda_created = get_latest_hda()            
                self.edit_hda_attribute_info( str( last_hda_created.id ),
                                              strings_displayed=strings_displayed )
        # admin_user is associated with role1, so should have all permissions on imported datasets
        check_edit_page( latest_3_lddas,
                         strings_displayed=[ 'Manage dataset permissions on',
                                             'can manage the roles associated with permissions on this dataset',
                                             'can import this dataset into their history for analysis' ] )
        self.logout()
        # regular_user1 is associated with role1, so should have all permissions on imported datasets
        self.login( email=regular_user1.email )
        check_edit_page( latest_3_lddas )
        self.logout()
        # Since regular_user2 is not associated with role1, she should not have
        # access to any of the 3 datasets, so she will not see folder1 on the libraries page
        self.login( email=regular_user2.email )        
        self.browse_library( cntrller='library',
                             library_id=self.security.encode_id( library1.id ),
                             strings_not_displayed=[ folder1.name ] )
        self.logout()
        # regular_user3 is associated with role1, so should have all permissions on imported datasets
        self.login( email=regular_user3.email )
        check_edit_page( latest_3_lddas )
        self.logout()
        self.login( email=admin_user.email )
        # Change the permissions and test again
        self.ldda_permissions( 'library_admin',
                               self.security.encode_id( library1.id ),
                               self.security.encode_id( folder1.id ),
                               ldda_ids,
                               str( role1.id ),
                               permissions_in=[ 'DATASET_ACCESS' ],
                               strings_displayed=[ 'Permissions updated for 3 datasets.' ] )
        # Even though we've eliminated the roles associated with the LIBRARY_MANAGE_PERMISSIONS permission,
        # none of the roles associated with the DATASET_MANAGE permission sould have been changed.
        check_edit_page( latest_3_lddas,
                         strings_displayed=[ 'manage permissions' ] )
    def test_060_restrict_access_to_library2( self ):
        """Testing restricting access to library2"""
        # Logged in as admin_user
        # Make sure library2 is public
        assert 'access library' not in [ a.action for a in library2.actions ], 'Library %s is not public when first created' % library2.name
        # Set permissions on the library2
        permissions_in = [ k for k, v in galaxy.model.Library.permitted_actions.items() ]
        permissions_out = []
        # Only admin_user will be permitted for
        # LIBRARY_ACCESS, LIBRARY_ADD, LIBRARY_MODIFY, LIBRARY_MANAGE on library2 and its contents.
        self.library_permissions( self.security.encode_id( library1.id ),
                                  library1.name,
                                  str( admin_user_private_role.id ),
                                  permissions_in,
                                  permissions_out )
        # Make sure library2 is not accessible by regular_user2.
        self.logout()
        self.login( email=regular_user2.email )
        self.visit_url( '%s/library/browse_libraries' % self.url )
        try:
            self.check_page_for_string( library2.name )
            raise AssertionError, 'Library %s is accessible by %s when it should be restricted' % ( library2.name, regular_user2.email )
        except:
            pass
        self.logout()
        self.login( email=admin_user.email )
    def test_065_create_ldda6( self ):
        """Testing create ldda6, restricting access on upload form to admin_user's private role"""
        filename = '6.bed'
        ldda_message = 'ldda6'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library2.id ),
                                     folder_id=self.security.encode_id( library2.root_folder.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     roles=[ str( admin_user_private_role.id ) ],
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'Upload files' ] )
        global ldda6
        ldda6 = get_latest_ldda_by_name( filename )
        assert ldda6 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda6 from the database'
    def test_070_add_folder2_to_library2( self ):
        """Testing adding folder2 to a library2"""
        # logged in as admin_user
        root_folder = library2.root_folder
        name = "Folder2"
        description = "Folder2 description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library2.id ),
                         self.security.encode_id( root_folder.id ),
                         name=name,
                         description=description )
        global folder2
        folder2 = get_folder( root_folder.id, name, description )
        assert folder2 is not None, 'Problem retrieving folder2 from the database'
    def test_075_create_ldda7( self ):
        """Testing create ldda7, restricting access on upload form to admin_user's private role"""
        filename = '7.bed'
        ldda_message = 'ldda7'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library2.id ),
                                     folder_id=self.security.encode_id( folder2.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     roles=[ str( admin_user_private_role.id ) ],
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'Upload files' ] )
        global ldda7
        ldda7 = get_latest_ldda_by_name( filename )
        assert ldda7 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda7 from the database'
    def test_080_add_subfolder2_to_folder2( self ):
        """Testing adding subfolder2 to a folder2"""
        # logged in as admin_user
        name = "Subfolder2"
        description = "Subfolder2 description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library2.id ),
                         self.security.encode_id( folder2.id ),
                         name=name,
                         description=description )
        global subfolder2
        subfolder2 = get_folder( folder2.id, name, description )
        assert subfolder2 is not None, 'Problem retrieving subfolder2 from the database'
    def test_085_create_ldda8( self ):
        """Testing create ldda8, restricting access on upload form to admin_user's private role"""
        filename = '8.bed'
        ldda_message = 'ldda8'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library2.id ),
                                     folder_id=self.security.encode_id( subfolder2.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     roles=[ str( admin_user_private_role.id ) ],
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'Upload files' ] )
        global ldda8
        ldda8 = get_latest_ldda_by_name( filename )
        assert ldda8 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda8 from the database'
    def test_090_make_library2_and_contents_public( self ):
        """Testing making library2 and all of its contents public"""
        self.make_library_item_public( self.security.encode_id( library2.id ),
                                       self.security.encode_id( library2.id ),
                                       item_type='library',
                                       contents=True,
                                       library_name=library2.name )
        # Make sure library2 is now accessible by regular_user2
        self.logout()
        self.login( email=regular_user2.email )
        self.visit_url( '%s/library/browse_libraries' % self.url )
        self.check_page_for_string( library2.name )
        self.browse_library( cntrller='library',
                             library_id=self.security.encode_id( library2.id ),
                             strings_displayed=[ ldda6.name, ldda6.message, ldda7.name, ldda7.message, ldda8.name, ldda8.message ] )
    def test_999_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to pass"""
        # Logged in as regular_user2
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
        # Eliminate all non-private roles
        ##################
        for role in [ role1, role2 ]:
            self.mark_role_deleted( self.security.encode_id( role.id ), role.name )
            self.purge_role( self.security.encode_id( role.id ), role.name )
            # Manually delete the role from the database
            refresh( role )
            sa_session.delete( role )
            sa_session.flush()
        ##################
        # Eliminate all groups
        ##################
        for group in [ group1 ]:
            self.mark_group_deleted( self.security.encode_id( group.id ), group.name )
            self.purge_group( self.security.encode_id( group.id ), group.name )
            # Manually delete the group from the database
            refresh( group )
            sa_session.delete( group )
            sa_session.flush()
        ##################
        # Make sure all users are associated only with their private roles
        ##################
        for user in [ admin_user, regular_user1, regular_user2, regular_user3 ]:
            refresh( user )
            if len( user.roles) != 1:
                raise AssertionError( '%d UserRoleAssociations are associated with %s ( should be 1 )' % ( len( user.roles ), user.email ) )
