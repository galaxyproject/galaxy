from base.twilltestcase import *
from base.test_db_util import *

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
        # Create role_one
        name = 'library security Role One'
        description = "library security This is Role One's description"
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
        name = 'library security Role Two'
        description = 'library security This is Role Two'
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
    def test_010_create_library( self ):
        """Testing creating a new library, then renaming it"""
        # Logged in as admin_user
        name = "library security Library1"
        description = "library security Library1 description"
        synopsis = "library security Library1 synopsis"
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
    def test_015_add_new_folder_to_root_folder( self ):
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
    def test_020_add_dataset_with_private_role_restriction_to_folder( self ):
        """Testing adding a dataset with a private role restriction to a folder"""
        # Logged in as admin_user
        #
        # Keep in mind that # LIBRARY_ACCESS = "Role One" on the whole library
        #
        # Add a dataset restricted by the following:
        # DATASET_MANAGE_PERMISSIONS = "test@bx.psu.edu" via DefaultUserPermissions
        # DATASET_ACCESS = "regular_user1" private role via this test method
        # LIBRARY_ADD = "Role One" via inheritance from parent folder
        # LIBRARY_MODIFY = "Role One" via inheritance from parent folder
        # LIBRARY_MANAGE = "Role One" via inheritance from parent folder
        # "Role One" members are: test@bx.psu.edu, test1@bx.psu.edu, test3@bx.psu.edu
        # This means that only user test1@bx.psu.edu can see the dataset from the Libraries view
        message ='This is a test of the fourth dataset uploaded'
        self.add_library_dataset( 'library_admin',
                                  '1.bed',
                                  self.security.encode_id( library_one.id ),
                                  self.security.encode_id( folder_one.id ),
                                  folder_one.name,
                                  file_type='bed',
                                  dbkey='hg18',
                                  roles=[ str( regular_user1_private_role.id ) ],
                                  message=message.replace( ' ', '+' ),
                                  root=False )
        global ldda_one
        ldda_one = get_latest_ldda()
        assert ldda_one is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda_one from the database'
        self.browse_library( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             check_str1='1.bed',
                             check_str2=message,
                             check_str3=admin_user.email )
    def test_025_accessing_dataset_with_private_role_restriction( self ):
        """Testing accessing a dataset with a private role restriction"""
        # Logged in as admin_user
        #
        # Keep in mind that # LIBRARY_ACCESS = "Role One" on the whole library
        # Role one members are: admin_user, regular_user1, regular_user3.  Each of these users will be permitted for
        # LIBRARY_ACCESS, LIBRARY_ADD, LIBRARY_MODIFY, LIBRARY_MANAGE on this library and it's contents.
        #
        # Legitimate roles displayed on the permission form are as follows:
        # 'Role One' since the LIBRARY_ACCESS permission is associated with Role One.  # Role one members are: admin_user, regular_user1, regular_user3.
        # 'test@bx.psu.edu' ( admin_user's private role ) since admin_user has Role One
        # 'Role Two' since admin_user has Role Two
        # 'Role Three' since admin_user has Role Three
        # 'test1@bx.psu.edu' ( regular_user1's private role ) since regular_user1 has Role One
        # 'test3@bx.psu.edu' ( regular_user3's private role ) since regular_user3 has Role One
        #
        # admin_user should not be able to see 1.bed from the analysis view's access libraries
        self.browse_library( 'library',
                              self.security.encode_id( library_one.id ),
                              not_displayed=folder_one.name,
                              not_displayed2='1.bed' )
        self.logout()
        # regular_user1 should be able to see 1.bed from the analysis view's access librarys
        # since it was associated with regular_user1's private role
        self.login( email=regular_user1.email )
        self.browse_library( 'library',
                              self.security.encode_id( library_one.id ),
                              check_str1=folder_one.name,
                              check_str2='1.bed' )
        self.logout()
        # regular_user2 should not be to see the library since they do not have 
        # Role One which is associated with the LIBRARY_ACCESS permission
        self.login( email=regular_user2.email )
        self.browse_libraries_regular_user( check_str1="No Items" )
        self.logout()
        # regular_user3 should not be able to see 1.bed from the analysis view's access librarys
        self.login( email=regular_user3.email )
        self.browse_library( 'library',
                             self.security.encode_id( library_one.id ),
                             not_displayed=folder_one.name,
                             not_displayed2='1.bed' )
        self.logout()
        self.login( email=admin_user.email )
    def test_030_change_dataset_access_permission( self ):
        """Testing changing the access permission on a dataset with a private role restriction"""
        # Logged in as admin_user
        # We need admin_user to be able to access 1.bed
        permissions_in = [ k for k, v in galaxy.model.Dataset.permitted_actions.items() ]
        for k, v in galaxy.model.Library.permitted_actions.items():
            if k != 'LIBRARY_ACCESS':
                permissions_in.append( k )
        permissions_out = []
        # Attempt to associate multiple roles with the library dataset, with one of the
        # roles being private.
        role_ids_str = '%s,%s' % ( str( role_one.id ), str( admin_user_private_role.id ) )
        check_str = "At least 1 user must have every role associated with accessing datasets.  "
        check_str += "Since you are associating more than 1 role, no private roles are allowed."
        self.ldda_permissions( 'library_admin',
                                self.security.encode_id( library_one.id ),
                                self.security.encode_id( folder_one.id ),
                                self.security.encode_id( ldda_one.id ),
                                role_ids_str,
                                permissions_in,
                                permissions_out,
                                check_str1=check_str )
        role_ids_str = str( role_one.id )
        self.ldda_permissions( 'library_admin',
                                self.security.encode_id( library_one.id ),
                                self.security.encode_id( folder_one.id ),
                                self.security.encode_id( ldda_one.id ),
                                role_ids_str,
                                permissions_in,
                                permissions_out,
                                ldda_name=ldda_one.name )
        # admin_user should now be able to see 1.bed from the analysis view's access libraries
        self.browse_library( 'library',
                             self.security.encode_id( library_one.id ),
                             check_str1=ldda_one.name )
    def test_035_add_dataset_with_role_associated_with_group_and_users( self ):
        """Testing adding a dataset with a role that is associated with a group and users"""
        # Logged in as admin_user
        # Add a dataset restricted by role_two, which is currently associated as follows:
        # groups: group_one
        # users: test@bx.psu.edu, test1@bx.psu.edu via group_one
        #
        # We first need to make library_one public
        permissions_in = []
        for k, v in galaxy.model.Library.permitted_actions.items():
            if k != 'LIBRARY_ACCESS':
                permissions_in.append( k )
        permissions_out = []
        # Role one members are: admin_user, regular_user1, regular_user3.  Each of these users will now be permitted for
        # LIBRARY_ADD, LIBRARY_MODIFY, LIBRARY_MANAGE on this library and it's contents.  The library will be public from
        # this point on.
        self.library_permissions( self.security.encode_id( library_one.id ),
                                  library_one.name,
                                  str( role_one.id ),
                                  permissions_in,
                                  permissions_out )
        refresh( library_one )
        message = 'Testing adding a dataset with a role that is associated with a group and users'
        self.add_library_dataset( 'library_admin',
                                  '2.bed',
                                  self.security.encode_id( library_one.id ),
                                  self.security.encode_id( folder_one.id ),
                                  folder_one.name,
                                  file_type='bed',
                                  dbkey='hg17',
                                  roles=[ str( role_two.id ) ],
                                  message=message.replace( ' ', '+' ),
                                  root=False )
        global ldda_two
        ldda_two = get_latest_ldda()
        assert ldda_two is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda_two from the database'
        self.browse_library( 'library',
                             self.security.encode_id( library_one.id ),
                             check_str1='2.bed',
                             check_str2=message,
                             check_str3=admin_user.email )
    def test_040_accessing_dataset_with_role_associated_with_group_and_users( self ):
        """Testing accessing a dataset with a role that is associated with a group and users"""
        # Logged in as admin_user
        # admin_user should be able to see 2.bed since she is associated with role_two
        self.browse_library( 'library',
                             self.security.encode_id( library_one.id ),
                             check_str1='2.bed',
                             check_str2=admin_user.email )
        self.logout()
        # regular_user1 should be able to see 2.bed since she is associated with group_two
        self.login( email = 'test1@bx.psu.edu' )
        self.browse_library( 'library',
                             self.security.encode_id( library_one.id ),
                             check_str1=folder_one.name,
                             check_str2='2.bed',
                             check_str3=admin_user.email )
        # Check the permissions on the dataset 2.bed - they are as folows:
        # DATASET_MANAGE_PERMISSIONS = test@bx.psu.edu
        # DATASET_ACCESS = Role Two
        #                  Role Two associations: test@bx.psu.edu and Group Two
        #                  Group Two members: Role One, Role Two, test1@bx.psu.edu
        #                  Role One associations: test@bx.psu.edu, test1@bx.psu.edu, test3@bx.psu.edu
        # LIBRARY_ADD = Role One
        #               Role One aassociations: test@bx.psu.edu, test1@bx.psu.edu, test3@bx.psu.edu
        # LIBRARY_MODIFY = Role One
        #                  Role One aassociations: test@bx.psu.edu, test1@bx.psu.edu, test3@bx.psu.edu
        # LIBRARY_MANAGE = Role One
        #                  Role One aassociations: test@bx.psu.edu, test1@bx.psu.edu, test3@bx.psu.edu        
        self.ldda_edit_info( 'library',
                             self.security.encode_id( library_one.id ),
                             self.security.encode_id( folder_one.id ),
                             self.security.encode_id( ldda_two.id ),
                             ldda_two.name,
                             check_str1='2.bed',
                             check_str2='This is the latest version of this library dataset',
                             check_str3='Edit attributes of 2.bed' )
        self.act_on_multiple_datasets( 'library',
                                       self.security.encode_id( library_one.id ),
                                       'import_to_history',
                                       ldda_ids=self.security.encode_id( ldda_two.id ),
                                       check_str1='1 dataset(s) have been imported into your history' )
        self.logout()
        # regular_user2 should not be able to see 2.bed
        self.login( email = 'test2@bx.psu.edu' )
        self.browse_library( 'library',
                             self.security.encode_id( library_one.id ),
                             not_displayed=folder_one.name,
                             not_displayed2='2.bed' )
        
        self.logout()
        # regular_user3 should not be able to see folder_one ( even though it does not contain any datasets that she
        # can access ) since she has Role One, and Role One has all library permissions ( see above ).
        self.login( email = 'test3@bx.psu.edu' )
        self.browse_library( 'library',
                             self.security.encode_id( library_one.id ),
                             check_str1=folder_one.name,
                             not_displayed='2.bed' )
        self.logout()
        self.login( email='test@bx.psu.edu' )
    def test_045_upload_directory_of_files_from_admin_view( self ):
        """Testing uploading a directory of files to a root folder from the Admin view"""
        # logged in as admin_user
        message = 'This is a test for uploading a directory of files'
        check_str_after_submit="Added 3 datasets to the library '%s' (each is selected)." % library_one.root_folder.name
        self.upload_directory_of_files( 'library_admin',
                                        self.security.encode_id( library_one.id ),
                                        self.security.encode_id( library_one.root_folder.id ),
                                        server_dir='library',
                                        message=message,
                                        check_str_after_submit=check_str_after_submit )
        self.browse_library( 'library_admin',
                             self.security.encode_id( library_one.id ),
                             check_str1=admin_user.email,
                             check_str2=message )
    def test_050_change_permissions_on_datasets_uploaded_from_library_dir( self ):
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
                               self.security.encode_id( library_one.id ),
                               self.security.encode_id( folder_one.id ),
                               ldda_ids,
                               str( role_one.id ),
                               permissions_in=[ 'DATASET_ACCESS', 'LIBRARY_MANAGE' ],
                               check_str1='Permissions updated for 3 datasets.' )
        # Make sure the permissions have been correctly updated for the 3 datasets.  Permissions should 
        # be all of the above on any of the 3 datasets that are imported into a history.
        def check_edit_page( lddas, check_str1='', check_str2='', check_str3='', check_str4='',
                             not_displayed1='', not_displayed2='', not_displayed3='' ):
            for ldda in lddas:
                # Import each library dataset into our history
                self.act_on_multiple_datasets( 'library',
                                               self.security.encode_id( library_one.id ),
                                               'import_to_history',
                                               ldda_ids=self.security.encode_id( ldda.id ) )
                # Determine the new HistoryDatasetAssociation id created when the library dataset was imported into our history
                last_hda_created = get_latest_hda()            
                self.edit_hda_attribute_info( str( last_hda_created.id ),
                                              check_str1=check_str1,
                                              check_str2=check_str2,
                                              check_str3=check_str3,
                                              check_str4=check_str4 )
        # admin_user is associated with role_one, so should have all permissions on imported datasets
        check_edit_page( latest_3_lddas,
                         check_str1='Manage dataset permissions on',
                         check_str2='Role members can manage the roles associated with permissions on this dataset',
                         check_str3='Role members can import this dataset into their history for analysis' )
        self.logout()
        # regular_user1 is associated with role_one, so should have all permissions on imported datasets
        self.login( email='test1@bx.psu.edu' )
        check_edit_page( latest_3_lddas )
        self.logout()
        # Since regular_user2 is not associated with role_one, she should not have
        # access to any of the 3 datasets, so she will not see folder_one on the libraries page
        self.login( email='test2@bx.psu.edu' )        
        self.browse_library( 'library',
                             self.security.encode_id( library_one.id ),
                             not_displayed=folder_one.name )
        self.logout()
        # regular_user3 is associated with role_one, so should have all permissions on imported datasets
        self.login( email='test3@bx.psu.edu' )
        check_edit_page( latest_3_lddas )
        self.logout()
        self.login( email='test@bx.psu.edu' )
        # Change the permissions and test again
        self.ldda_permissions( 'library_admin',
                               self.security.encode_id( library_one.id ),
                               self.security.encode_id( folder_one.id ),
                               ldda_ids,
                               str( role_one.id ),
                               permissions_in=[ 'DATASET_ACCESS' ],
                               check_str1='Permissions updated for 3 datasets.' )
        check_edit_page( latest_3_lddas,
                         check_str1='View Permissions',
                         not_displayed1='Manage dataset permissions on',
                         not_displayed2='Role members can manage roles associated with permissions on this library item',
                         not_displayed3='Role members can import this dataset into their history for analysis' )
    def test_055_library_permissions( self ):
        """Test library permissions"""
        # Logged in as admin_user
        form_name = 'Library template Form One'
        form_desc = 'This is Form One'
        form_type = galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE
        # Create form for library template
        self.create_form( name=form_name, desc=form_desc, formtype=form_type )
        global form_one
        form_one = get_form( form_name )
        assert form_one is not None, 'Problem retrieving form named (%s) from the database' % form_name
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
        # Create a library, adding no template
        name = "library security Library Two"
        description = "library security This is Library Two"
        synopsis = "library security Library Two synopsis"
        self.create_library( name=name, description=description, synopsis=synopsis )
        self.browse_libraries_admin( check_str1=name, check_str2=description )
        global library_two
        library_two = get_library( name, description, synopsis )
        assert library_two is not None, 'Problem retrieving library named "%s" from the database' % name
        # Set library permissions for regular_user1 and regular_user2.  Each of these users will be permitted to
        # LIBRARY_ADD, LIBRARY_MODIFY, LIBRARY_MANAGE for library items.
        permissions_in = [ k for k, v in galaxy.model.Library.permitted_actions.items() ]
        permissions_out = []
        role_ids_str = '%s,%s' % ( str( regular_user1_private_role.id ), str( regular_user2_private_role.id ) )
        self.library_permissions( self.security.encode_id( library_two.id ),
                                  library_two.name,
                                  role_ids_str,
                                  permissions_in,
                                  permissions_out )
        self.logout()
        # Login as regular_user1 and make sure they can see the library
        self.login( email=regular_user1.email )
        self.browse_libraries_regular_user( check_str1=name )
        self.logout()
        # Login as regular_user2 and make sure they can see the library
        self.login( email=regular_user2.email )
        self.browse_libraries_regular_user( check_str1=name )
        # Add a dataset to the library
        message = 'Testing adding 1.bed to Library Two root folder'
        self.add_library_dataset( 'library',
                                  '1.bed',
                                  self.security.encode_id( library_two.id ),
                                  self.security.encode_id( library_two.root_folder.id ),
                                  library_two.root_folder.name,
                                  file_type='bed',
                                  dbkey='hg18',
                                  message=message,
                                  root=True )
        # Add a folder to the library
        name = "Root Folder's Folder X"
        description = "This is the root folder's Folder X"
        self.add_folder( 'library',
                         self.security.encode_id( library_two.id ),
                         self.security.encode_id( library_two.root_folder.id ), 
                         name=name,
                         description=description )
        global folder_x
        folder_x = get_folder( library_two.root_folder.id, name, description )
        # Add an information template to the folder
        template_name = 'Folder Template 1'
        self.add_library_template( 'library',
                                   'folder',
                                   self.security.encode_id( library_one.id ),
                                   self.security.encode_id( form_one.id ),
                                   form_one.name,
                                   folder_id=self.security.encode_id( folder_x.id ) )
        # Modify the folder's information
        contents = '%s folder contents' % form_one_field_label
        new_name = "Root Folder's Folder Y"
        new_description = "This is the root folder's Folder Y"
        self.folder_info( 'library',
                          self.security.encode_id( folder_x.id ),
                          self.security.encode_id( library_two.id ),
                          name,
                          new_name,
                          new_description,
                          contents=contents,
                          field_name=form_one_field_name )
        # Twill barfs when self.check_page_for_string() is called after dealing with an information template,
        # the exception is: TypeError: 'str' object is not callable
        # the work-around it to end this method so any calls are in the next method.
    def test_060_template_features_and_permissions( self ):
        """Test library template and more permissions behavior from the Data Libraries view"""
        # Logged in as regular_user2
        refresh( folder_x )
        # Add a dataset to the folder
        message = 'Testing adding 2.bed to Library Three root folder'
        self.add_library_dataset( 'library',
                                  '2.bed',
                                  self.security.encode_id( library_two.id ),
                                  self.security.encode_id( folder_x.id ),
                                  folder_x.name,
                                  file_type='bed',
                                  dbkey='hg18',
                                  message=message.replace( ' ', '+' ),
                                  root=False )
        global ldda_x
        ldda_x = get_latest_ldda()
        assert ldda_x is not None, 'Problem retrieving ldda_x from the database'
        # Add an information template to the library
        template_name = 'Library Template 3'
        self.add_library_template( 'library',
                                   'library',
                                   self.security.encode_id( library_two.id ),
                                   self.security.encode_id( form_one.id ),
                                   form_one.name )
        # Add information to the library using the template
        contents = '%s library contents' % form_one_field_label
        self.visit_url( '%s/library_common/library_info?cntrller=library&id=%s' % ( self.url, self.security.encode_id( library_two.id ) ) )
        # There are 2 forms on this page and the template is the 2nd form
        tc.fv( '2', form_one_field_name, contents )
        tc.submit( 'edit_info_button' )
        # For some reason, the following check:
        # self.check_page_for_string ( 'The information has been updated.' )
        # ...throws the following exception - I have not idea why!
        # TypeError: 'str' object is not callable
        # The work-around is to not make ANY self.check_page_for_string() calls until the next method
    def test_065_permissions_as_different_regular_user( self ):
        """Test library template and more permissions behavior from the Data Libraries view as a different user"""
        # Logged in as regular_user2
        self.logout()
        self.login( email=regular_user1.email )
        self.browse_library( 'library',
                             self.security.encode_id( library_two.id ),
                             check_str1=ldda_x.name )
    def test_999_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to pass"""
        # Logged in as regular_user1
        self.logout()
        self.login( email=admin_user.email )
        ##################
        # Purge all libraries
        ##################
        for library in [ library_one, library_two ]:
            self.delete_library_item( 'library_admin',
                                      self.security.encode_id( library.id ),
                                      self.security.encode_id( library.id ),
                                      library.name,
                                      item_type='library' )
            self.purge_library( self.security.encode_id( library.id ), library.name )
        ##################
        # Eliminate all non-private roles
        ##################
        for role in [ role_one, role_two ]:
            self.mark_role_deleted( self.security.encode_id( role.id ), role.name )
            self.purge_role( self.security.encode_id( role.id ), role.name )
            # Manually delete the role from the database
            refresh( role )
            sa_session.delete( role )
            sa_session.flush()
        ##################
        # Eliminate all groups
        ##################
        for group in [ group_one ]:
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
