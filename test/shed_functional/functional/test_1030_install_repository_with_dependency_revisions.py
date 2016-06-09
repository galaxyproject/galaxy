from shed_functional.base.twilltestcase import common, ShedTwillTestCase

datatypes_repository_name = 'emboss_datatypes_0030'
datatypes_repository_description = "Galaxy applicable data formats used by Emboss tools."
datatypes_repository_long_description = "Galaxy applicable data formats used by Emboss tools.  This repository contains no tools."

emboss_repository_name = 'emboss_0030'
emboss_5_repository_name = 'emboss_5_0030'
emboss_6_repository_name = 'emboss_6_0030'
emboss_repository_description = 'Galaxy wrappers for Emboss version 5.0.0 tools for test 0030'
emboss_repository_long_description = 'Galaxy wrappers for Emboss version 5.0.0 tools for test 0030'

base_datatypes_count = 0
repository_datatypes_count = 0
running_standalone = False


class RepositoryWithDependencyRevisions( ShedTwillTestCase ):
    '''Test installing a repository with dependency revisions.'''

    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        self.test_db_util.get_private_role( test_user_1 )
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        self.test_db_util.get_private_role( admin_user )
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        galaxy_admin_user = self.test_db_util.get_galaxy_user( common.admin_email )
        assert galaxy_admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        self.test_db_util.get_galaxy_private_role( galaxy_admin_user )

    def test_0005_ensure_repositories_and_categories_exist( self ):
        '''Create the 0030 category and add repositories to it, if necessary.'''
        global repository_datatypes_count
        global running_standalone
        category = self.create_category( name='Test 0030 Repository Dependency Revisions', description='Test 0030 Repository Dependency Revisions' )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        datatypes_repository = self.get_or_create_repository( name=datatypes_repository_name,
                                                              description=datatypes_repository_description,
                                                              long_description=datatypes_repository_long_description,
                                                              owner=common.test_user_1_name,
                                                              category_id=self.security.encode_id( category.id ),
                                                              strings_displayed=[] )
        if self.repository_is_new( datatypes_repository ):
            running_standalone = True
            self.upload_file( datatypes_repository,
                              filename='emboss/datatypes/datatypes_conf.xml',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded datatypes_conf.xml.',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            emboss_5_repository = self.get_or_create_repository( name=emboss_5_repository_name,
                                                                 description=emboss_repository_description,
                                                                 long_description=emboss_repository_long_description,
                                                                 owner=common.test_user_1_name,
                                                                 category_id=self.security.encode_id( category.id ),
                                                                 strings_displayed=[] )
            self.upload_file( emboss_5_repository,
                              filename='emboss/emboss.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded tool tarball.',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            repository_dependencies_path = self.generate_temp_path( 'test_1030', additional_paths=[ 'emboss', '5' ] )
            datatypes_tuple = ( self.url, datatypes_repository.name, datatypes_repository.user.username, self.get_repository_tip( datatypes_repository ) )
            self.create_repository_dependency( repository=emboss_5_repository, repository_tuples=[ datatypes_tuple ], filepath=repository_dependencies_path )
            emboss_6_repository = self.get_or_create_repository( name=emboss_6_repository_name,
                                                                 description=emboss_repository_description,
                                                                 long_description=emboss_repository_long_description,
                                                                 owner=common.test_user_1_name,
                                                                 category_id=self.security.encode_id( category.id ),
                                                                 strings_displayed=[] )
            self.upload_file( emboss_6_repository,
                              filename='emboss/emboss.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded tool tarball.',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            repository_dependencies_path = self.generate_temp_path( 'test_1030', additional_paths=[ 'emboss', '6' ] )
            datatypes_tuple = ( self.url, datatypes_repository.name, datatypes_repository.user.username, self.get_repository_tip( datatypes_repository ) )
            self.create_repository_dependency( repository=emboss_6_repository, repository_tuples=[ datatypes_tuple ], filepath=repository_dependencies_path )
            emboss_repository = self.get_or_create_repository( name=emboss_repository_name,
                                                               description=emboss_repository_description,
                                                               long_description=emboss_repository_long_description,
                                                               owner=common.test_user_1_name,
                                                               category_id=self.security.encode_id( category.id ),
                                                               strings_displayed=[] )
            self.upload_file( emboss_repository,
                              filename='emboss/emboss.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded tool tarball.',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            repository_dependencies_path = self.generate_temp_path( 'test_1030', additional_paths=[ 'emboss', '5' ] )
            dependency_tuple = ( self.url, emboss_5_repository.name, emboss_5_repository.user.username, self.get_repository_tip( emboss_5_repository ) )
            self.create_repository_dependency( repository=emboss_repository, repository_tuples=[ dependency_tuple ], filepath=repository_dependencies_path )
            dependency_tuple = ( self.url, emboss_6_repository.name, emboss_6_repository.user.username, self.get_repository_tip( emboss_6_repository ) )
            self.create_repository_dependency( repository=emboss_repository, repository_tuples=[ dependency_tuple ], filepath=repository_dependencies_path )
        repository_datatypes_count = int( self.get_repository_datatypes_count( datatypes_repository ) )

    def test_0010_browse_tool_shed( self ):
        """Browse the available tool sheds in this Galaxy instance and preview the emboss tool."""
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        self.browse_tool_shed( url=self.url, strings_displayed=[ 'Test 0030 Repository Dependency Revisions' ] )
        category = self.test_db_util.get_category_by_name( 'Test 0030 Repository Dependency Revisions' )
        self.browse_category( category, strings_displayed=[ 'emboss_0030' ] )
        self.preview_repository_in_tool_shed( 'emboss_0030', common.test_user_1_name, strings_displayed=[ 'emboss_0030', 'Valid tools' ] )

    def test_0015_install_emboss_repository( self ):
        '''Install the emboss repository without installing tool dependencies.'''
        global repository_datatypes_count
        global base_datatypes_count
        global running_standalone
        base_datatypes_count = int( self.get_datatypes_count() )
        strings_displayed = [ 'Handle', 'Never installed', 'tool dependencies', 'emboss', '5.0.0', 'package' ]
        self.install_repository( 'emboss_0030',
                                 common.test_user_1_name,
                                 'Test 0030 Repository Dependency Revisions',
                                 strings_displayed=strings_displayed,
                                 install_tool_dependencies=False,
                                 new_tool_panel_section_label='test_1030' )
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( 'emboss_0030', common.test_user_1_name )
        strings_displayed = [ 'emboss_0030',
                              'Galaxy wrappers for Emboss version 5.0.0 tools for test 0030',
                              'user1',
                              self.url.replace( 'http://', '' ),
                              installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
        strings_displayed.extend( [ 'Installed tool shed repository', 'Valid tools', 'antigenic' ] )
        self.display_installed_repository_manage_page( installed_repository, strings_displayed=strings_displayed )
        strings_displayed = [ 'emboss', '5.0.0', 'package' ]
        self.check_installed_repository_tool_dependencies( installed_repository, strings_displayed=strings_displayed, dependencies_installed=False )
        self.verify_tool_metadata_for_installed_repository( installed_repository )
        self.update_installed_repository( installed_repository, strings_displayed=[ "there are no updates available" ] )
        current_datatypes = int( self.get_datatypes_count() )
        if running_standalone:
            assert current_datatypes == base_datatypes_count + repository_datatypes_count, 'Installing emboss did not add new datatypes.'
        else:
            assert current_datatypes == base_datatypes_count, 'Installing emboss added new datatypes.'

    def test_0025_verify_installed_repository_metadata( self ):
        '''Verify that resetting the metadata on an installed repository does not change the metadata.'''
        self.verify_installed_repository_metadata_unchanged( 'emboss_0030', common.test_user_1_name )
