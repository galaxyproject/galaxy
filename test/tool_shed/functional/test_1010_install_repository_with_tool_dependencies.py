from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
import tool_shed.base.test_db_util as test_db_util

class ToolWithToolDependencies( ShedTwillTestCase ):
    '''Test installing a repository with tool dependencies.'''
    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        admin_user = test_db_util.get_galaxy_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = test_db_util.get_galaxy_private_role( admin_user )
    def test_0005_browse_tool_shed( self ):
        """Browse the available tool sheds in this Galaxy instance and preview the freebayes tool."""
        self.browse_tool_shed( url=self.url, strings_displayed=[ 'Test 0010 Repository With Tool Dependencies' ] )
        category = test_db_util.get_category_by_name( 'Test 0010 Repository With Tool Dependencies' )
        self.browse_category( category, strings_displayed=[ 'freebayes_0010' ] )
        self.preview_repository_in_tool_shed( 'freebayes_0010', common.test_user_1_name, strings_displayed=[ 'freebayes_0010', 'Valid tools' ] )
    def test_0015_install_freebayes_repository( self ):
        '''Install the freebayes repository without installing tool dependencies.'''
        self.install_repository( 'freebayes_0010', common.test_user_1_name, install_tool_dependencies=False )
        installed_repository = test_db_util.get_installed_repository_by_name_owner( 'freebayes_0010', common.test_user_1_name )
        self.verify_installed_repository_on_browse_page( installed_repository )
        self.display_installed_repository_manage_page( installed_repository, 
                                                       strings_displayed=[ 'Installed tool shed repository', 'Tools', 'FreeBayes' ] )
        self.check_installed_repository_tool_dependencies( installed_repository, dependencies_installed=False )
        self.verify_tool_metadata_for_installed_repository( installed_repository )
