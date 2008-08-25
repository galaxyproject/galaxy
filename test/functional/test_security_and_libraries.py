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
        self.check_page_for_string( 'Galaxy Administration' )
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
        self.create_group()
        self.visit_page( "admin/groups" )
        self.check_page_for_string( "group_name=New+Test+Group" )
    # TODO: Upgrade twill, make sure the following works
    #def test_15_add_group_member( self ):
    #    #"""Testing adding a member to an existing group"""
    #    #self.add_group_member()
    #    #self.visit_page( 'group_name=New+Test+Group' )
    #    #self.check_page_for_string( 'test@bx.psu.edu' )
    #    # TODO: See self.add_group_member() problem
    #    #self.check_page_for_string( 'test2@bx.psu.edu' )
    # TODO: make the following work
    #def test_20_create_library( self ):
    #    """Testing creating new library"""
    #    self.create_library()
    #    self.visit_page( 'admin/libraries' )
    #    self.check_page_for_string( "New Test Library" )
               
