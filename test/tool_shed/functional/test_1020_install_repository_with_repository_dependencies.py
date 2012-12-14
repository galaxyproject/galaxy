from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
import tool_shed.base.test_db_util as test_db_util

class ToolWithRepositoryDependencies( ShedTwillTestCase ):
    '''Test installing a repository with repository dependencies.'''
    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        admin_user = test_db_util.get_galaxy_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = test_db_util.get_galaxy_private_role( admin_user )
    def test_0005_browse_tool_shed( self ):
        """Browse the available tool sheds in this Galaxy instance and preview the emboss tool."""
        self.browse_tool_shed( url=self.url, strings_displayed=[ 'Test 0020 Basic Repository Dependencies' ] )
        category = test_db_util.get_category_by_name( 'Test 0020 Basic Repository Dependencies' )
        self.browse_category( category, strings_displayed=[ 'emboss_0020' ] )
        self.preview_repository_in_tool_shed( 'emboss_0020', common.test_user_1_name, strings_displayed=[ 'emboss_0020', 'Valid tools' ] )
    def test_0015_install_emboss_repository( self ):
        '''Install the emboss repository without installing tool dependencies.'''
        self.install_repository( 'emboss_0020', common.test_user_1_name, install_tool_dependencies=False )
        installed_repository = test_db_util.get_installed_repository_by_name_owner( 'emboss_0020', common.test_user_1_name )
        self.verify_installed_repository_on_browse_page( installed_repository )
        self.display_installed_repository_manage_page( installed_repository, 
                                                       strings_displayed=[ 'Installed tool shed repository', 'Tools', 'antigenic' ] )
        self.check_installed_repository_tool_dependencies( installed_repository, dependencies_installed=False )
        self.verify_tool_metadata_for_installed_repository( installed_repository )
    def test_0020_verify_installed_repository_metadata( self ):
        '''Verify that resetting the metadata on an installed repository does not change the metadata.'''
        self.verify_installed_repository_metadata_unchanged( 'emboss_0020', common.test_user_1_name )
