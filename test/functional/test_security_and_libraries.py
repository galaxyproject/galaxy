import galaxy.model
from galaxy.model.orm import *
from base.twilltestcase import *

s = 'You must have Galaxy administrator privileges to use this feature.'
        
class TestHistory( TwillTestCase ):
    def test_00_admin_features_when_not_logged_in( self ):
        """Testing admin_features when not logged in"""
        self.logout()
        self.visit_url( "%s/admin" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/reload_tool?tool_id=upload1" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/roles" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/create_role" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/new_role" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/role" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/groups" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/create_group" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/group_members_edit" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/update_group_members" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/users" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/library_browser" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/libraries" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/library" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/folder?id=1&new=True" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/dataset" % self.url )
        self.check_page_for_string( s )
    def test_05_login_as_admin( self ):
        """Testing logging in as an admin user"""
        self.login( email='test@bx.psu.edu' ) #This is configured as our admin user
        self.visit_page( "admin" )
        self.check_page_for_string( 'Administration' )
        user = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test@bx.psu.edu' ).first()
        # Make sure a private role exists for the user
        private_role_found = False
        for role in user.all_roles():
            if role.name == user.email and role.description == 'Private Role for %s' % user.email:
                private_role_found = True
                break
        if not private_role_found:
            raise AssertionError( "Private role not found for user '%s'" % user.email )
        self.visit_url( "%s/admin/user?user_id=%s" % ( self.url, user.id ) )
        self.check_page_for_string( "test@bx.psu.edu" )
        self.home()
        self.logout()
        # Make sure that we have 3 users
        self.login( email='test2@bx.psu.edu' ) # This will not be an admin user
        self.visit_page( "admin" )
        self.check_page_for_string( s )
        self.logout()
        self.login( email='test3@bx.psu.edu' ) # This will not be an admin user
        self.visit_page( "admin" )
        self.check_page_for_string( s )
        self.logout()
    def test_10_create_role( self ):
        """Testing creating new non-private role with 2 members"""
        self.login( email='test@bx.psu.edu' )
        user = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test@bx.psu.edu' ).first()
        user_id1 = str( user.id )
        user = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test2@bx.psu.edu' ).first()
        user_id2 = str( user.id )
        self.create_role( user_ids=[ user_id1, user_id2 ] )
    def test_15_create_group( self ):
        """Testing creating new group with 2 members and 1 associated role"""
        user = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test@bx.psu.edu' ).first()
        user_id1 = str( user.id )
        user = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test2@bx.psu.edu' ).first()
        user_id2 = str( user.id )
        role = galaxy.model.Role.filter( galaxy.model.Role.table.c.name=='New Test Role' ).first()
        role_id = str( role.id )
        self.create_group( user_ids=[ user_id1, user_id2 ], role_ids=[ role_id ] )
    def test_20_add_group_member( self ):
        """Testing editing membership of an existing group"""
        self.create_group( name='Another Test Group' )
        group = galaxy.model.Group.filter( galaxy.model.Group.table.c.name == 'Another Test Group' ).first()
        group_id = str( group.id )
        user = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test3@bx.psu.edu' ).first()
        user_id = str( user.id )
        self.add_group_members( group_id, [ user_id  ] )
        self.visit_url( "%s/admin/group_members_edit?group_id=%s" % ( self.url, group_id ) )
        self.check_page_for_string( 'test3@bx.psu.edu' )
    def test_25_associate_groups_with_role( self ):
        """Testing adding existing groups to an existing role"""
        group = galaxy.model.Group.filter( galaxy.model.Group.table.c.name == 'Another Test Group' ).first()
        group_id = str( group.id )
        user = galaxy.model.User.filter( galaxy.model.User.table.c.email == 'test@bx.psu.edu' ).first()
        user_id = str( user.id )
        # NOTE: To get this to work with twill, all select lists on the ~/admin/role page must contain at least
        # 1 option value or twill throws an exception, which is: ParseError: OPTION outside of SELECT
        # Due to this bug in twill, we create the role, associating it with at least 1 user and 1 group...
        #
        # TODO: need to enhance this test to associate DefaultUserPermissions and DefaultHistoryPermissions
        # with the role, then add tests in test_55_purge_role to make sure the association records are deleted
        # when the role is purged.
        self.create_role( name='Another Test Role', user_ids=[ user_id ], group_ids=[ group_id ] )
        role = galaxy.model.Role.filter( galaxy.model.Role.table.c.name=='Another Test Role' ).first()
        role_id = str( role.id )
        group = galaxy.model.Group.filter( galaxy.model.Group.table.c.name == 'New Test Group' ).first()
        group_id = str( group.id )
        # ...and then we associate the role with a group not yet associated
        self.associate_groups_with_role( role_id, group_ids=[ group_id  ] )
        self.visit_page( 'admin/roles' )
        self.check_page_for_string( 'New Test Group' )
    def test_30_create_library( self ):
        """Testing creating new library"""
        self.create_library( name='New Test Library', description='New Test Library Description' )
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( "New Test Library" )
    def test_35_rename_library( self ):
        """Testing renaming a library"""
        library = galaxy.model.Library.filter( and_( galaxy.model.Library.table.c.name=='New Test Library',
                                                     galaxy.model.Library.table.c.deleted==False ) ).first()
        library_id = str( library.id )
        self.rename_library( library_id, name='New Test Library Renamed', description='New Test Library Description Re-described' )
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( "New Test Library Renamed" )
        # Rename it back to what it was originally
        self.rename_library( library_id, name='New Test Library', description='New Test Library Description' )
    def test_40_rename_root_folder( self ):
        """Testing renaming a library root folder"""
        library = galaxy.model.Library.filter( and_( galaxy.model.Library.table.c.name=='New Test Library',
                                                     galaxy.model.Library.table.c.deleted==False ) ).first()
        folder = library.root_folder
        folder_id = str( folder.id )
        self.rename_folder( folder_id, name='New Test Library Root Folder', description='New Test Library Root Folder Description' )
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( "New Test Library Root Folder" )
    def test_45_add_public_dataset_to_root_folder( self ):
        """Testing adding a public dataset to a library root folder"""
        library = galaxy.model.Library.filter( and_( galaxy.model.Library.table.c.name=='New Test Library',
                                                     galaxy.model.Library.table.c.deleted==False ) ).first()
        folder = library.root_folder
        folder_id = str( folder.id )
        self.add_dataset( '1.bed', folder_id, extension='bed', dbkey='hg18', roles=[] )
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( "1.bed" )
        self.check_page_for_string( "bed" )
        self.check_page_for_string( "hg18" )
    def test_50_add_new_folder( self ):
        """Testing adding a folder to a library root folder"""
        library = galaxy.model.Library.filter( and_( galaxy.model.Library.table.c.name=='New Test Library',
                                                     galaxy.model.Library.table.c.deleted==False ) ).first()
        folder = library.root_folder
        folder_id = str( folder.id )
        self.add_folder( folder_id, name='New Test Folder', description='New Test Folder Description' )
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( "New Test Folder" )
    def test_55_mark_group_deleted( self ):
        """Testing marking a group as deleted"""
        self.visit_page( "admin/groups" )
        self.check_page_for_string( "Another Test Group" )
        group = galaxy.model.Group.filter( galaxy.model.Group.table.c.name == 'Another Test Group' ).first()
        group_id = str( group.id )
        self.mark_group_deleted( group_id )
    def test_60_undelete_group( self ):
        """Testing undeleting a deleted group"""
        group = galaxy.model.Group.filter( galaxy.model.Group.table.c.name == 'Another Test Group' ).first()
        group_id = str( group.id )
        self.undelete_group( group_id )
    def test_65_mark_role_deleted( self ):
        """Testing marking a role as deleted"""
        self.visit_page( "admin/roles" )
        self.check_page_for_string( "Another Test Role" )
        role = galaxy.model.Role.filter( galaxy.model.Role.table.c.name == 'Another Test Role' ).first()
        role_id = str( role.id )
        self.mark_role_deleted( role_id )
    def test_70_undelete_role( self ):
        """Testing undeleting a deleted role"""
        role = galaxy.model.Role.filter( galaxy.model.Role.table.c.name == 'Another Test Role' ).first()
        role_id = str( role.id )
        self.undelete_role( role_id )
    def test_75_mark_library_deleted( self ):
        """Testing marking a library as deleted"""
        library = galaxy.model.Library.filter( and_( galaxy.model.Library.table.c.name=='New Test Library',
                                                     galaxy.model.Library.table.c.deleted==False ) ).first()
        library_id = str( library.id )
        self.mark_library_deleted( library_id )
    def test_80_mark_library_undeleted( self ):
        """Testing marking a library as not deleted"""
        library = galaxy.model.Library.filter( and_( galaxy.model.Library.table.c.name=='New Test Library',
                                                     galaxy.model.Library.table.c.deleted==True ) ).first()
        library_id = str( library.id )
        self.mark_library_undeleted( library_id )
        # Mark library as deleted again so we can test purging it
        self.mark_library_deleted( library_id )
    def test_85_purge_group( self ):
        """Testing purging a group"""
        group = galaxy.model.Group.filter( galaxy.model.Group.table.c.name == 'Another Test Group' ).first()
        group_id = str( group.id )
        self.purge_group( group_id )
        # Make sure there are no UserGroupAssociations
        uga = galaxy.model.UserGroupAssociation.filter( galaxy.model.UserGroupAssociation.table.c.group_id == group_id ).all()
        if uga:
            raise AssertionError( "Purging the group did not delete the UserGroupAssociations for group_id '%s'" % group_id )
        # Make sure there are no GroupRoleAssociations
        gra = galaxy.model.GroupRoleAssociation.filter( galaxy.model.GroupRoleAssociation.table.c.group_id == group_id ).all()
        if gra:
            raise AssertionError( "Purging the group did not delete the GroupRoleAssociations for group_id '%s'" % group_id )
    def test_90_purge_role( self ):
        """Testing purging a role"""
        role = galaxy.model.Role.filter( galaxy.model.Role.table.c.name == 'Another Test Role' ).first()
        role_id = str( role.id )
        self.purge_role( role_id )
        # Make sure there are no GroupRoleAssociations
        gra = galaxy.model.GroupRoleAssociation.filter( galaxy.model.GroupRoleAssociation.table.c.role_id == role_id ).all()
        if gra:
            raise AssertionError( "Purging the role did not delete the GroupRoleAssociations for role_id '%s'" % role_id )
        # Make sure there are no ActionDatasetRoleAssociations
        adra = galaxy.model.ActionDatasetRoleAssociation.filter( galaxy.model.ActionDatasetRoleAssociation.table.c.role_id == role_id ).all()
        if adra:
            raise AssertionError( "Purging the role did not delete the ActionDatasetRoleAssociations for role_id '%s'" % role_id )
    def test_95_purge_library( self ):
        """Testing purging a library"""
        library = galaxy.model.Library.filter( and_( galaxy.model.Library.table.c.name=='New Test Library',
                                                     galaxy.model.Library.table.c.deleted==True ) ).first()
        library_id = str( library.id )
        self.purge_library( library_id )
