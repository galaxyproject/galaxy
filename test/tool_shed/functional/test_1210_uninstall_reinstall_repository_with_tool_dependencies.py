from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
import tool_shed.base.test_db_util as test_db_util

class UninstallingAndReinstallingRepositories( ShedTwillTestCase ):
    '''Test uninstalling and reinstalling a repository with tool dependencies.'''
    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        admin_user = test_db_util.get_galaxy_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = test_db_util.get_galaxy_private_role( admin_user )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % test_user_1_email
        test_user_1_private_role = test_db_util.get_private_role( test_user_1 )
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        admin_user_private_role = test_db_util.get_private_role( admin_user )
    def test_0005_ensure_repositories_and_categories_exist( self ):
        '''Create the 0010 category and upload the freebayes repository to the tool shed, if necessary.'''
        category = self.create_category( name='Test 0010 Repository With Tool Dependencies', description='Tests for a repository with tool dependencies.' )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name='freebayes_0010', 
                                                    description="Galaxy's freebayes tool", 
                                                    long_description="Long description of Galaxy's freebayes tool", 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ) )
        if self.repository_is_new( repository ):
            self.upload_file( repository, 
                              'freebayes/freebayes.xml', 
                              valid_tools_only=False, 
                              commit_message="Uploaded freebayes.xml." )
            self.upload_file( repository, 
                              'freebayes/tool_data_table_conf.xml.sample', 
                              valid_tools_only=False,
                              commit_message="Uploaded tool_data_table_conf.xml.", 
                              remove_repo_files_not_in_tar='No' )
            self.upload_file( repository, 
                              'freebayes/sam_fa_indices.loc.sample', 
                              commit_message="Uploaded sam_fa_indices.loc.sample.", 
                              valid_tools_only=False,
                             remove_repo_files_not_in_tar='No' )
            self.upload_file( repository, 
                              'freebayes/invalid_tool_dependencies/tool_dependencies.xml', 
                              valid_tools_only=False,
                              commit_message="Uploaded invalid_tool_dependencies/tool_dependencies.xml.", 
                              remove_repo_files_not_in_tar='No' )
            self.upload_file( repository, 
                              'freebayes/tool_dependencies.xml', 
                              valid_tools_only=False,
                              commit_message="Uploaded tool_dependencies.xml", 
                              remove_repo_files_not_in_tar='No' )
    def test_0010_install_freebayes_repository( self ):
        '''Install the freebayes repository into the Galaxy instance.'''
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        strings_displayed = [ 'Handle', 'tool dependencies', 'freebayes', '0.9.4_9696d0ce8a9', 'samtools', '0.1.18' ]
        self.install_repository( 'freebayes_0010', 
                                 common.test_user_1_name, 
                                 'Test 0010 Repository With Tool Dependencies', 
                                 strings_displayed=strings_displayed,
                                 new_tool_panel_section='test_1210' )
        installed_repository = test_db_util.get_installed_repository_by_name_owner( 'freebayes_0010', common.test_user_1_name )
        strings_displayed = [ installed_repository.name,
                              installed_repository.description,
                              installed_repository.owner, 
                              installed_repository.tool_shed, 
                              installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
    def test_0015_uninstall_freebayes_repository( self ):
        '''Uninstall the freebayes repository.'''
        installed_repository = test_db_util.get_installed_repository_by_name_owner( 'freebayes_0010', common.test_user_1_name )
        self.uninstall_repository( installed_repository, remove_from_disk=True )
        strings_not_displayed = [ installed_repository.name, installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_not_displayed=strings_not_displayed )
    def test_0020_reinstall_freebayes_repository( self ):
        '''Reinstall the freebayes repository.'''
        installed_repository = test_db_util.get_installed_repository_by_name_owner( 'freebayes_0010', common.test_user_1_name )
        self.reinstall_repository( installed_repository )
        strings_displayed = [ installed_repository.name,
                              installed_repository.description,
                              installed_repository.owner, 
                              installed_repository.tool_shed, 
                              installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
        self.display_installed_repository_manage_page( installed_repository, 
                                                       strings_displayed=[ 'Installed tool shed repository', 'Valid tools', 'FreeBayes' ] )
        self.verify_tool_metadata_for_installed_repository( installed_repository )
    def test_0025_deactivate_freebayes_repository( self ):
        '''Deactivate the freebayes repository without removing it from disk.'''
        installed_repository = test_db_util.get_installed_repository_by_name_owner( 'freebayes_0010', common.test_user_1_name )
        self.uninstall_repository( installed_repository, remove_from_disk=False )
        strings_not_displayed = [ installed_repository.name, installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_not_displayed=strings_not_displayed )
    def test_0030_reactivate_freebayes_repository( self ):
        '''Reactivate the freebayes repository and verify that it now shows up in the list of installed repositories.'''
        installed_repository = test_db_util.get_installed_repository_by_name_owner( 'freebayes_0010', common.test_user_1_name )
        self.reactivate_repository( installed_repository )
        strings_displayed = [ installed_repository.name,
                              installed_repository.description,
                              installed_repository.owner, 
                              installed_repository.tool_shed, 
                              installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
        self.display_installed_repository_manage_page( installed_repository, 
                                                       strings_displayed=[ 'Installed tool shed repository', 'Valid tools', 'FreeBayes' ] )
        self.verify_tool_metadata_for_installed_repository( installed_repository )
