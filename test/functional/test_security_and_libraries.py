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
        self.visit_url( "%s/admin/dataset_security" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/groups" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/create_group" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/group_members_edit" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/update_group_members" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/group_dataset_permitted_actions_edit" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/mark_group_deleted" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/purge_group" % self.url )
        self.check_page_for_string( s )
        self.visit_url( "%s/admin/users" % self.url )
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
        self.logout()
        # Need to ensure that we have 2 users
        self.login( email='test2@bx.psu.edu' ) # This will not be an admin user
        self.visit_page( "admin" )
        self.check_page_for_string( s )
    def test_10_create_group( self ):
        """Testing creating new group with 1 members"""
        self.login( email='test@bx.psu.edu' )
        self.visit_page( "admin/groups" )
         # the following should have been created when account was created.
        self.check_page_for_string( 'test@bx.psu.edu private group' )
        self.create_group( name='New Test Group', priority='10' )
        self.visit_page( "admin/groups" )
        self.check_page_for_string( "group_name=New+Test+Group" )
    # twill version 0.9 still does not allow for the following test
    #def test_15_add_group_member( self ):
    #    """Testing adding a member to an existing group"""
    #    group = galaxy.model.Group.get_by( name='New Test Group' )
    #    group_id = str( group.id )
    #    group_name = group.name.replace( ' ', '+' )
    #    self.add_group_member( group_id=group_id, group_name=group_name )
    #    self.visit_page( 'admin/group_members?group_id=%s&group_name=%s' % ( group_id, group_name ) )
    #    self.check_page_for_string( 'test@bx.psu.edu' )
    #    self.check_page_for_string( 'test2@bx.psu.edu' )
    def test_20_delete_group( self ):
        """Testing deleting a group"""
        self.visit_page( "admin/groups" )
        self.check_page_for_string( "group_name=New+Test+Group" )
        group = galaxy.model.Group.get_by( name='New Test Group' )
        group_id = str( group.id )
        self.mark_group_deleted( group_id=group_id )
    def test_25_undelete_group( self ):
        """Testing undeleting a deleted group"""
        group = galaxy.model.Group.get_by( name='New Test Group' )
        group_id = str( group.id )
        self.undelete_group( group_id=group_id )
    def test_30_purge_group( self ):
        """Testing purging a group"""
        group = galaxy.model.Group.get_by( name='New Test Group' )
        self.purge_group( group=group )

    def test_20_create_library( self ):
        """Testing creating new library"""
        self.create_library( name='New Test Library', description='New Test Library Description' )
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( "New Test Library" )
               
