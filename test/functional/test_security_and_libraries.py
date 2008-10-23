import galaxy.model
from base.twilltestcase import TwillTestCase

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
        self.visit_url( "%s/admin/folder" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/dataset" % self.url )
        self.check_page_for_string( s )
    def test_05_login_as_admin( self ):
        """Testing logging in as an admin user"""
        self.login( email='test@bx.psu.edu' ) #This is configured as our admin user
        self.visit_page( "admin" )
        self.check_page_for_string( 'Administration' )
        user = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test@bx.psu.edu' ).first()
        self.visit_url( "%s/admin/user?user_id=%s" % ( self.url, user.id ) )
        self.check_page_for_string( "test@bx.psu.edu" )
        self.home()
        self.logout()
        # Need to ensure that we have 2 users
        self.login( email='test2@bx.psu.edu' ) # This will not be an admin user
        self.visit_page( "admin" )
        self.check_page_for_string( s )
        self.logout()
    def test_10_create_role( self ):
        """Testing creating new non-private role with 2 members"""
        self.login( email='test@bx.psu.edu' )
        self.visit_page( "admin/create_role" )
        self.check_page_for_string( 'Create Role' )
        user = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test@bx.psu.edu' ).first()
        user_id1 = str( user.id )
        user = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test2@bx.psu.edu' ).first()
        user_id2 = str( user.id )
        self.create_role( user_ids=[user_id1, user_id2] )
        self.visit_page( "admin/roles" )
        self.check_page_for_string( "New Test Role" )
    def test_15_create_group( self ):
        """Testing creating new group with 2 members and 1 associated role"""
        self.visit_page( "admin/create_group" )
        self.check_page_for_string( 'Create Group' )
        user = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test@bx.psu.edu' ).first()
        user_id1 = str( user.id )
        user = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test2@bx.psu.edu' ).first()
        user_id2 = str( user.id )
        role = galaxy.model.Role.filter( galaxy.model.Role.table.c.name=='New Test Role' ).first()
        role_id = str( role.id )
        self.create_group( user_ids=[user_id1, user_id2], role_ids=[role_id] )
        self.visit_page( "admin/groups" )
        self.check_page_for_string( "New Test Group" )
    def test_20_add_group_member( self ):
        """Testing editing membership of an existing group"""
        self.create_group( 'Another Test Group' )
        group = galaxy.model.Group.filter( galaxy.model.Group.table.c.name == 'New Test Group' ).first()
        group_id = str( group.id )
        self.add_group_member( group_id )
        self.visit_page( 'admin/group_members_edit?group_id=%s' % group_id )
        self.check_page_for_string( 'test@bx.psu.edu' )
        self.check_page_for_string( 'test2@bx.psu.edu' )
    #def test_20_delete_group( self ):
    #    """Testing deleting a group"""
    #    self.visit_page( "admin/groups" )
    #    self.check_page_for_string( "group_name=New+Test+Group" )
    #    group = galaxy.model.Group.filter_by( name='New Test Group' ).all()[0]
    #    group_id = str( group.id )
    #    self.mark_group_deleted( group_id=group_id )
    #def test_25_undelete_group( self ):
    #    """Testing undeleting a deleted group"""
    #    group = galaxy.model.Group.filter_by( name='New Test Group' ).all()[0]
    #    group_id = str( group.id )
    #    self.undelete_group( group_id=group_id )
    #def test_30_purge_group( self ):
    #    """Testing purging a group"""
    #    group = galaxy.model.Group.filter_by( name='New Test Group' ).all()[0]
    #    self.purge_group( group=group )

    #def test_20_create_library( self ):
    #    """Testing creating new library"""
    #    self.create_library( name='New Test Library', description='New Test Library Description' )
    #    self.visit_page( 'admin/libraries' )
    #    self.check_page_for_string( "New Test Library" )
               
