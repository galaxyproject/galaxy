from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
import tool_shed.base.test_db_util as test_db_util

class RepositoryWithDependencyRevisions( ShedTwillTestCase ):
    '''Test installing a repository with dependency revisions.'''
    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        admin_user = test_db_util.get_galaxy_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = test_db_util.get_galaxy_private_role( admin_user )
    def test_0005_browse_tool_shed( self ):
        """Browse the available tool sheds in this Galaxy instance and preview the emboss tool."""
        self.browse_tool_shed( url=self.url, strings_displayed=[ 'Test 0030 Repository Dependency Revisions' ] )
        category = test_db_util.get_category_by_name( 'Test 0030 Repository Dependency Revisions' )
        self.browse_category( category, strings_displayed=[ 'emboss_0030' ] )
        self.preview_repository_in_tool_shed( 'emboss_0030', common.test_user_1_name, strings_displayed=[ 'emboss_0030', 'Valid tools' ] )
    def test_0015_install_emboss_repository( self ):
        '''Install the emboss repository without installing tool dependencies.'''
        repository = test_db_util.get_repository_by_name_and_owner( 'emboss_0030', common.test_user_1_name )
        revisions = self.get_repository_metadata_revisions( repository )
        self.install_repository( 'emboss_0030', common.test_user_1_name, changeset_revision=revisions[1], install_tool_dependencies=False )
        installed_repository = test_db_util.get_installed_repository_by_name_owner( 'emboss_0030', common.test_user_1_name )
        self.verify_installed_repository_on_browse_page( installed_repository )
        self.display_installed_repository_manage_page( installed_repository, 
                                                       strings_displayed=[ 'Installed tool shed repository', 'Tools', 'antigenic' ] )
        self.check_installed_repository_tool_dependencies( installed_repository, dependencies_installed=False )
        self.verify_tool_metadata_for_installed_repository( installed_repository )
