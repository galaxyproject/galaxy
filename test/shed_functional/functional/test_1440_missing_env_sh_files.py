import logging

from shed_functional.base.twilltestcase import common, ShedTwillTestCase

log = logging.getLogger( __name__ )

category_name = 'Test 1440 Tool dependency missing env.sh'
category_description = 'Test script 1440 for detection of missing environment settings.'
package_repository_name = 'package_env_sh_1_0_1440'
tool_repository_name = 'filter_1440'
package_repository_description = 'Repository that should result in an env.sh file, but does not.'
tool_repository_description = 'Galaxy filtering tool.'
package_repository_long_description = '%s: %s' % ( package_repository_name, package_repository_description )
tool_repository_long_description = '%s: %s' % ( tool_repository_name, tool_repository_description )

'''
1. Create a tool dependency type repository that reliably fails to install successfully. This repository should define
   an action that would have created an env.sh file on success, resulting in an env.sh file that should exist, but is missing.

2. Create a repository that defines a complex repository dependency in the repository created in step 1, with prior_install_required
   and set_environment_for_install.

3. Attempt to install the second repository into a galaxy instance, verify that it is installed but missing tool dependencies.

'''


class TestMissingEnvSh( ShedTwillTestCase ):
    '''Test installing a repository that should create an env.sh file, but does not.'''

    def test_0000_initiate_users_and_category( self ):
        """Create necessary user accounts and login as an admin user."""
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        self.test_db_util.get_private_role( admin_user )
        self.create_category( name=category_name, description=category_description )
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        test_user_2 = self.test_db_util.get_user( common.test_user_2_email )
        assert test_user_2 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_2_email
        self.test_db_util.get_private_role( test_user_2 )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        self.test_db_util.get_private_role( test_user_1 )

    def test_0005_create_package_repository( self ):
        '''Create and populate package_env_sh_1_0_1440.'''
        '''
        This is step 1 - Create repository package_env_sh_1_0_1440.

        Create and populate a repository that is designed to fail a tool dependency installation. This tool dependency should
        also define one or more environment variables.
        '''
        category = self.test_db_util.get_category_by_name( category_name )
        repository = self.get_or_create_repository( name=package_repository_name,
                                                    description=package_repository_description,
                                                    long_description=package_repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        # Upload the edited tool dependency definition to the package_lapack_3_4_1440 repository.
        self.upload_file( repository,
                          filename='1440_files/dependency_definition/tool_dependencies.xml',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate package_env_sh_1_0_1440 with a broken tool dependency definition.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0010_create_filter_repository( self ):
        '''Create and populate filter_1440.'''
        '''
        This is step 2 - Create a repository that defines a complex repository dependency on the repository created in
        step 1, with prior_install_required and set_environment_for_install.
        '''
        category = self.test_db_util.get_category_by_name( category_name )
        repository = self.get_or_create_repository( name=tool_repository_name,
                                                    description=tool_repository_description,
                                                    long_description=tool_repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        # Upload the edited tool dependency definition to the package_lapack_3_4_1440 repository.
        self.upload_file( repository,
                          filename='filtering/filtering_2.2.0.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate filter_1440 with the filtering tool.',
                          strings_displayed=[],
                          strings_not_displayed=[] )
        self.upload_file( repository,
                          filename='1440_files/complex_dependency/tool_dependencies.xml',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate filter_1440 with a dependency on package_env_sh_1_0_1440.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0015_install_filter_repository( self ):
        '''Install the filter_1440 repository to galaxy.'''
        '''
        This is step 3 - Attempt to install the second repository into a galaxy instance, verify that it is installed but
        missing tool dependencies.
        '''
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        post_submit_strings_displayed = [ 'filter_1440', 'package_env_sh_1_0_1440' ]
        self.install_repository( 'filter_1440',
                                 common.test_user_1_name,
                                 category_name,
                                 install_tool_dependencies=True,
                                 post_submit_strings_displayed=post_submit_strings_displayed )

    def test_0020_verify_missing_tool_dependency( self ):
        '''Verify that the filter_1440 repository is installed and missing tool dependencies.'''
        repository = self.test_db_util.get_installed_repository_by_name_owner( 'filter_1440', common.test_user_1_name )
        strings_displayed = [ 'Missing tool dependencies' ]
        self.display_installed_repository_manage_page( repository, strings_displayed=strings_displayed )
        assert len( repository.missing_tool_dependencies ) == 1, 'filter_1440 should have a missing tool dependency, but does not.'
