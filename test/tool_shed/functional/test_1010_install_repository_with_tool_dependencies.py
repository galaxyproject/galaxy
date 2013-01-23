from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
import tool_shed.base.test_db_util as test_db_util
import logging
repository_name = 'freebayes_0010'
repository_description="Galaxy's freebayes tool"
repository_long_description="Long description of Galaxy's freebayes tool"
category_name = 'Test 0010 Repository With Tool Dependencies'
log = logging.getLogger( __name__ )

class ToolWithToolDependencies( ShedTwillTestCase ):
    '''Test installing a repository with tool dependencies.'''
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
        '''Create the 0010 category and upload the freebayes repository to it, if necessary.'''
        category = self.create_category( name=category_name, description='Tests for a repository with tool dependencies.' )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=repository_name, 
                                                    description=repository_description, 
                                                    long_description=repository_long_description, 
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
    def test_0010_browse_tool_shed( self ):
        """Browse the available tool sheds in this Galaxy instance and preview the freebayes tool."""
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        self.browse_tool_shed( url=self.url, strings_displayed=[ category_name ] )
        category = test_db_util.get_category_by_name( category_name )
        self.browse_category( category, strings_displayed=[ repository_name ] )
        strings_displayed = [ repository_name, 'Valid tools', 'Tool dependencies' ]
        self.preview_repository_in_tool_shed( repository_name, common.test_user_1_name, strings_displayed=strings_displayed )
    def test_0015_install_freebayes_repository( self ):
        '''Install the freebayes repository without installing tool dependencies.'''
        strings_displayed=[ 'Never installed', 'can be automatically installed', 'Set the tool_dependency_dir' ]
        strings_displayed.extend( [ 'Handle', 'tool dependencies', 'freebayes', '0.9.4_9696d0ce8a9', 'samtools', '0.1.18' ] )
        self.install_repository( repository_name, 
                                 common.test_user_1_name,
                                 category_name, 
                                 strings_displayed=strings_displayed,
                                 install_tool_dependencies=False, 
                                 new_tool_panel_section='test_1010' )
        installed_repository = test_db_util.get_installed_repository_by_name_owner( repository_name, common.test_user_1_name )
        strings_displayed = [ installed_repository.name,
                              installed_repository.description,
                              installed_repository.owner, 
                              installed_repository.tool_shed, 
                              installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
        self.display_installed_repository_manage_page( installed_repository, 
                                                       strings_displayed=[ 'Installed tool shed repository', 'Valid tools', 'FreeBayes' ] )
        self.check_installed_repository_tool_dependencies( installed_repository, dependencies_installed=False )
        self.verify_tool_metadata_for_installed_repository( installed_repository )
    def test_0020_verify_installed_repository_metadata( self ):
        '''Verify that resetting the metadata on an installed repository does not change the metadata.'''
        self.verify_installed_repository_metadata_unchanged( repository_name, common.test_user_1_name )
    def test_0025_verify_sample_files( self ):
        '''Verify that the installed repository populated shed_tool_data_table.xml and the sample files.'''
        self.verify_installed_repository_data_table_entries( data_tables=[ 'sam_fa_indexes' ] )
        
