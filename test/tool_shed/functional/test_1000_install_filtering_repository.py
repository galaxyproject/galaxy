from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
from tool_shed.base.test_db_util import get_repository_by_name_and_owner, get_galaxy_user, get_galaxy_private_role, get_category_by_name

class BasicToolShedFeatures( ShedTwillTestCase ):
    '''Test installing a basic repository.'''
    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
        self.galaxy_logout()
        self.galaxy_login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = get_galaxy_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % test_user_1_email
        test_user_1_private_role = get_galaxy_private_role( test_user_1 )
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        admin_user = get_galaxy_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = get_galaxy_private_role( admin_user )
    def test_0005_browse_tool_sheds( self ):
        """Browse the available tool sheds in this Galaxy instance."""
        self.visit_galaxy_url( '/admin_toolshed/browse_tool_sheds' )
        self.check_page_for_string( 'Embedded tool shed for functional tests' )
        self.browse_tool_shed( url=self.url, strings_displayed=[ 'Test 0000 Basic Repository Features 1', 'Test 0000 Basic Repository Features 2' ] )
    def test_0010_browse_test_0000_category( self ):
        '''Browse the category created in test 0000. It should contain the filtering_0000 repository also created in that test.'''
        category = get_category_by_name( 'Test 0000 Basic Repository Features 1' )
        self.browse_category( category, strings_displayed=[ 'filtering_0000' ] )
    def test_0015_preview_filtering_repository( self ):
        '''Load the preview page for the filtering_0000 repository in the tool shed.'''
        self.preview_repository_in_tool_shed( 'filtering_0000', common.test_user_1_name, strings_displayed=[ 'filtering_0000', 'Valid tools' ] )
    def test_0020_install_filtering_repository( self ):
        self.install_repository( 'filtering_0000', common.test_user_1_name )
