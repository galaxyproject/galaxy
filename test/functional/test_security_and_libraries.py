import galaxy.model
from galaxy.model.orm import *
from base.twilltestcase import *

security_msg = 'You must have Galaxy administrator privileges to use this feature.'

class TestHistory( TwillTestCase ):
    def test_00_admin_features_when_not_logged_in( self ):
        """Testing admin_features when not logged in"""
        self.logout()
        self.visit_url( "%s/admin" % self.url )
        self.check_page_for_string( security_msg )
        self.visit_url( "%s/admin/reload_tool?tool_id=upload1" % self.url )
        self.check_page_for_string( security_msg )
        self.visit_url( "%s/admin/roles" % self.url )
        self.check_page_for_string( security_msg )
        self.visit_url( "%s/admin/create_role" % self.url )
        self.check_page_for_string( security_msg )
        self.visit_url( "%s/admin/new_role" % self.url )
        self.check_page_for_string( security_msg )
        self.visit_url( "%s/admin/role" % self.url )
        self.check_page_for_string( security_msg )
        self.visit_url( "%s/admin/groups" % self.url )
        self.check_page_for_string( security_msg )
        self.visit_url( "%s/admin/create_group" % self.url )
        self.check_page_for_string( security_msg )
        self.visit_url( "%s/admin/group_members_edit" % self.url )
        self.check_page_for_string( security_msg )
        self.visit_url( "%s/admin/update_group_members" % self.url )
        self.check_page_for_string( security_msg )
        self.visit_url( "%s/admin/users" % self.url )
        self.check_page_for_string( security_msg )
        self.visit_url( "%s/admin/library_browser" % self.url )
        self.check_page_for_string( security_msg )
        self.visit_url( "%s/admin/libraries" % self.url )
        self.check_page_for_string( security_msg )
        self.visit_url( "%s/admin/library" % self.url )
        self.check_page_for_string( security_msg )
        self.visit_url( "%s/admin/folder?id=1&new=True" % self.url )
        self.check_page_for_string( security_msg )
        self.visit_url( "%s/admin/dataset" % self.url )
        self.check_page_for_string( security_msg )
    def test_03_login_as_admin( self ):
        """Testing logging in as an admin user"""
        self.login( email='test@bx.psu.edu' ) #This is configured as our admin user
        self.visit_page( "admin" )
        self.check_page_for_string( 'Administration' )
        global testuser1
        testuser1 = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test@bx.psu.edu' ).first()
        # Make sure a private role exists for the user
        private_role_found = False
        for role in testuser1.all_roles():
            if role.name == testuser1.email and role.description == 'Private Role for %s' % testuser1.email:
                private_role_found = True
                break
        if not private_role_found:
            raise AssertionError( "Private role not found for user '%s'" % testuser1.email )
        self.visit_url( "%s/admin/user?user_id=%s" % ( self.url, testuser1.id ) )
        self.check_page_for_string( testuser1.email )
        self.home()
        self.logout()
        # Make sure that we have 3 users
        self.login( email='test2@bx.psu.edu' ) # This will not be an admin user
        global testuser2
        testuser2 = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test2@bx.psu.edu' ).first()
        self.visit_page( "admin" )
        self.check_page_for_string( security_msg )
        self.logout()
        self.login( email='test3@bx.psu.edu' ) # This will not be an admin user
        global testuser3
        testuser3 = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test3@bx.psu.edu' ).first()
        self.visit_page( "admin" )
        self.check_page_for_string( security_msg )
        self.logout()
    def test_06_create_role( self ):
        """Testing creating new non-private role with 2 members"""
        self.login( email=testuser1.email )
        self.create_role( user_ids=[ str( testuser1.id ), str( testuser2.id ) ] )
        name = 'New Test Role'
        # Get the role object for later tests
        global new_test_role
        new_test_role = galaxy.model.Role.filter( galaxy.model.Role.table.c.name==name ).first()
    def test_09_create_group( self ):
        """Testing creating new group with 2 members and 1 associated role"""
        name = 'New Test Group'
        self.create_group( name=name, user_ids=[ str( testuser1.id ), str( testuser2.id ) ], role_ids=[ str( new_test_role.id ) ] )
        # Get the group object for later tests
        global new_test_group
        new_test_group = galaxy.model.Group.filter( galaxy.model.Group.table.c.name==name ).first()
    def test_12_add_group_member( self ):
        """Testing editing membership of an existing group"""
        name = 'Another Test Group'
        self.create_group( name=name )
        # Get the group object for later tests
        global another_test_group
        another_test_group = galaxy.model.Group.filter( galaxy.model.Group.table.c.name==name ).first()
        self.add_group_members( str( another_test_group.id ), [ str( testuser3.id )  ] )
        self.visit_url( "%s/admin/group_members_edit?group_id=%s" % ( self.url, str( another_test_group.id ) ) )
        self.check_page_for_string( testuser3.email )
    def test_15_associate_groups_with_role( self ):
        """Testing adding existing groups to an existing role"""
        # NOTE: To get this to work with twill, all select lists on the ~/admin/role page must contain at least
        # 1 option value or twill throws an exception, which is: ParseError: OPTION outside of SELECT
        # Due to this bug in twill, we create the role, associating it with at least 1 user and 1 group...
        #
        # TODO: need to enhance this test to associate DefaultUserPermissions and DefaultHistoryPermissions
        # with the role, then add tests in test_55_purge_role to make sure the association records are deleted
        # when the role is purged.
        name = 'Another Test Role'
        self.create_role( name=name, user_ids=[ str( testuser1.id ) ], group_ids=[ str( another_test_group.id ) ] )
        # Get the role object for later tests
        global another_test_role
        another_test_role = galaxy.model.Role.filter( galaxy.model.Role.table.c.name==name ).first()
        # ...and then we associate the role with a group not yet associated
        self.associate_groups_with_role( str( another_test_role.id ), group_ids=[ str( new_test_group.id )  ] )
        self.visit_page( 'admin/roles' )
        self.check_page_for_string( new_test_group.name )
    def test_18_create_library( self ):
        """Testing creating new library"""
        name = 'New Test Library'
        description = 'New Test Library Description'
        self.create_library( name=name, description=description )
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( name )
        # Get the library object for later tests
        global library
        library = galaxy.model.Library.filter( and_( galaxy.model.Library.table.c.name==name,
                                                     galaxy.model.Library.table.c.description==description,
                                                     galaxy.model.Library.table.c.deleted==False ) ).first()
    def test_21_rename_library( self ):
        """Testing renaming a library"""
        self.rename_library( str( library.id ), name='New Test Library Renamed', description='New Test Library Description Re-described', root_folder='on' )
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( "New Test Library Renamed" )
        # Rename it back to what it was originally
        self.rename_library( str( library.id ), name='New Test Library', description='New Test Library Description', root_folder='on' )
    def test_24_rename_root_folder( self ):
        """Testing renaming a library root folder"""
        folder = library.root_folder
        self.rename_folder( str( folder.id ), name='New Test Library Root Folder', description='New Test Library Root Folder Description' )
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( "New Test Library Root Folder" )
    def test_27_add_public_dataset_to_root_folder( self ):
        """Testing adding a public dataset to a library root folder"""
        folder = library.root_folder
        self.add_dataset( '1.bed', str( folder.id ), extension='bed', dbkey='hg18', roles=[] )
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( "1.bed" )
        self.check_page_for_string( "bed" )
        self.check_page_for_string( "hg18" )
    def test_30_copy_dataset_from_history_to_root_folder( self ):
        """Testing copying a dataset from the current history to a library root folder"""
        folder = library.root_folder
        self.add_dataset_to_folder_from_history( str( folder.id ) )
    def test_33_add_new_folder( self ):
        """Testing adding a folder to a library root folder"""
        root_folder = library.root_folder
        name = 'New Test Folder'
        description = 'New Test Folder Description'
        self.add_folder( str( root_folder.id ), name=name, description=description )
        global new_test_folder
        new_test_folder = galaxy.model.LibraryFolder.filter( and_( galaxy.model.LibraryFolder.table.c.parent_id==root_folder.id,
                                                                   galaxy.model.LibraryFolder.table.c.name==name,
                                                                   galaxy.model.LibraryFolder.table.c.description==description ) ).first()
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( "New Test Folder" )
    def test_36_add_datasets_from_library_dir( self ):
        """Testing adding several datasets from library directory to sub-folder"""
        self.add_datasets_from_library_dir( str( new_test_folder.id ), roles=[ str( new_test_role.id ) ] )
    def test_39_mark_group_deleted( self ):
        """Testing marking a group as deleted"""
        self.visit_page( "admin/groups" )
        self.check_page_for_string( another_test_group.name )
        self.mark_group_deleted( str( another_test_group.id ) )
    def test_42_undelete_group( self ):
        """Testing undeleting a deleted group"""
        self.undelete_group( str( another_test_group.id ) )
    def test_45_mark_role_deleted( self ):
        """Testing marking a role as deleted"""
        self.visit_page( "admin/roles" )
        self.check_page_for_string( another_test_role.name )
        self.mark_role_deleted( str( another_test_role.id ) )
    def test_48_undelete_role( self ):
        """Testing undeleting a deleted role"""
        self.undelete_role( str( another_test_role.id ) )
    def test_51_mark_library_deleted( self ):
        """Testing marking a library as deleted"""
        self.mark_library_deleted( str( library.id ) )
        # Make sure the library was deleted
        library.refresh()
        if not library.deleted:
            raise AssertionError( 'The library id %s named "%s" has not been marked as deleted.' % ( str( library.id ), library.name ) )
        def check_folder( library_folder ):
            for folder in library_folder.folders:
                folder.refresh()
                # Make sure all of the library_folders are deleted
                if not folder.deleted:
                    raise AssertionError( 'The library_folder named "%s" has not been marked as deleted ( library.id: %s ).' % ( folder.name, str( library.id ) ) )
                check_folder( folder )
            # Make sure all of the library_folder_dataset_associations are deleted
            for lfda in library_folder.datasets:
                lfda.refresh()
                if not lfda.deleted:
                    raise AssertionError( 'The library_folder_dataset_association id %s named "%s" has not been marked as deleted ( library.id: %s ).' % ( str( lfda.id ), lfda.name, str( library.id ) ) )
                # Make sure none of the datasets have been deleted since that should occur only when the library is purged
                lfda.dataset.refresh()
                if lfda.dataset.deleted:
                    raise AssertionError( 'The dataset with id "%s" has been marked as deleted when it should not have been.' % lfda.dataset.id )
        check_folder( library.root_folder )
    def test_54_mark_library_undeleted( self ):
        """Testing marking a library as not deleted"""
        self.mark_library_undeleted( str( library.id ) )
        # Make sure the library is undeleted
        library.refresh()
        if library.deleted:
            raise AssertionError( 'The library id %s named "%s" has not been marked as undeleted.' % ( str( library.id ), library.name ) )
        def check_folder( library_folder ):
            for folder in library_folder.folders:
                folder.refresh()
                # Make sure all of the library_folders are undeleted
                if folder.deleted:
                    raise AssertionError( 'The library_folder id %s named "%s" has not been marked as undeleted ( library.id: %s ).' % ( str( folder.id ), folder.name, str( library.id ) ) )
                check_folder( folder )
            # Make sure all of the library_folder_dataset_associations are undeleted
            for lfda in library_folder.datasets:
                lfda.refresh()
                if lfda.deleted:
                    raise AssertionError( 'The library_folder_dataset_association id %s named "%s" has not been marked as undeleted ( library.id: %s ).' % ( str( lfda.id ), lfda.name, str( library.id ) ) )
                # Make sure all of the datasets have been undeleted
                if lfda.dataset.deleted:
                    raise AssertionError( 'The dataset with id "%s" has not been marked as undeleted.' % lfda.dataset.id )
        check_folder( library.root_folder )
        # Mark library as deleted again so we can test purging it
        self.mark_library_deleted( str( library.id ) )
        # Make sure the library is deleted again
        library.refresh()
        if not library.deleted:
            raise AssertionError( 'The library id %s named "%s" has not been marked as deleted after it was undeleted.' % ( str( library.id ), library.name ) )
    def test_57_purge_group( self ):
        """Testing purging a group"""
        group_id = str( another_test_group.id )
        self.purge_group( group_id )
        # Make sure there are no UserGroupAssociations
        uga = galaxy.model.UserGroupAssociation.filter( galaxy.model.UserGroupAssociation.table.c.group_id == group_id ).all()
        if uga:
            raise AssertionError( "Purging the group did not delete the UserGroupAssociations for group_id '%s'" % group_id )
        # Make sure there are no GroupRoleAssociations
        gra = galaxy.model.GroupRoleAssociation.filter( galaxy.model.GroupRoleAssociation.table.c.group_id == group_id ).all()
        if gra:
            raise AssertionError( "Purging the group did not delete the GroupRoleAssociations for group_id '%s'" % group_id )
    def test_60_purge_role( self ):
        """Testing purging a role"""
        role_id = str( another_test_role.id )
        self.purge_role( role_id )
        # Make sure there are no GroupRoleAssociations
        gra = galaxy.model.GroupRoleAssociation.filter( galaxy.model.GroupRoleAssociation.table.c.role_id == role_id ).all()
        if gra:
            raise AssertionError( "Purging the role did not delete the GroupRoleAssociations for role_id '%s'" % role_id )
        # Make sure there are no ActionDatasetRoleAssociations
        adra = galaxy.model.ActionDatasetRoleAssociation.filter( galaxy.model.ActionDatasetRoleAssociation.table.c.role_id == role_id ).all()
        if adra:
            raise AssertionError( "Purging the role did not delete the ActionDatasetRoleAssociations for role_id '%s'" % role_id )
    def test_63_purge_library( self ):
        """Testing purging a library"""
        self.purge_library( str( library.id ) )
        # Make sure the library was purged
        library.refresh()
        if not library.purged:
            raise AssertionError( 'The library id %s named "%s" has not been marked as purged.' % ( str( library.id ), library.name ) )
        def check_folder( library_folder ):
            for folder in library_folder.folders:
                folder.refresh()
                # Make sure all of the library_folders are purged
                if not folder.purged:
                    raise AssertionError( 'The library_folder id %s named "%s" has not been marked purged.' % ( str( folder.id ), folder.name ) )
                check_folder( folder )
            # Make sure all of the library_folder_dataset_associations are deleted ( no purged column )
            for lfda in library_folder.datasets:
                lfda.refresh()
                if not lfda.deleted:
                    raise AssertionError( 'The library_folder_dataset_association id %s named "%s" has not been marked as deleted.' % ( str( lfda.id ), lfda.name ) )
                # Make sure all of the datasets have been deleted
                dataset = lfda.dataset
                dataset.refresh()
                if not dataset.deleted:
                    raise AssertionError( 'The dataset with id "%s" has not been marked as deleted when it should have been.' % str( lfda.dataset.id ) )
        check_folder( library.root_folder )
