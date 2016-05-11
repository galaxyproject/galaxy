from shed_functional.base.twilltestcase import common, ShedTwillTestCase

datatypes_repository_name = 'emboss_datatypes_0030'
datatypes_repository_description = "Galaxy applicable data formats used by Emboss tools."
datatypes_repository_long_description = "Galaxy applicable data formats used by Emboss tools.  This repository contains no tools."

emboss_repository_name = 'emboss_0030'
emboss_5_repository_name = 'emboss_5_0030'
emboss_6_repository_name = 'emboss_6_0030'
emboss_repository_description = 'Galaxy wrappers for Emboss version 5.0.0 tools'
emboss_repository_long_description = 'Galaxy wrappers for Emboss version 5.0.0 tools'

base_datatypes_count = 0
repository_datatypes_count = 0
running_standalone = False


class UninstallingAndReinstallingRepositories( ShedTwillTestCase ):
    '''Test uninstalling and reinstalling a repository with repository dependency revisions.'''

    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_galaxy_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        self.test_db_util.get_galaxy_private_role( admin_user )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        self.test_db_util.get_private_role( test_user_1 )
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        self.test_db_util.get_private_role( admin_user )

    def test_0005_ensure_repositories_and_categories_exist( self ):
        '''Create the 0030 category and upload the emboss repository to the tool shed, if necessary.'''
        global repository_datatypes_count
        global running_standalone
        category = self.create_category( name='Test 0030 Repository Dependency Revisions', description='Tests for a repository with tool dependencies.' )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        datatypes_repository = self.get_or_create_repository( name=datatypes_repository_name,
                                                              description=datatypes_repository_description,
                                                              long_description=datatypes_repository_long_description,
                                                              owner=common.test_user_1_name,
                                                              category_id=self.security.encode_id( category.id ),
                                                              strings_displayed=[] )
        if self.repository_is_new( datatypes_repository ):
            running_standalone = True
            emboss_5_repository = self.get_or_create_repository( name=emboss_5_repository_name,
                                                                 description=emboss_repository_description,
                                                                 long_description=emboss_repository_long_description,
                                                                 owner=common.test_user_1_name,
                                                                 category_id=self.security.encode_id( category.id ),
                                                                 strings_displayed=[] )
            self.upload_file( datatypes_repository,
                              filename='emboss/datatypes/datatypes_conf.xml',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded datatypes_conf.xml.',
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

    def test_0010_install_emboss_repository( self ):
        '''Install the emboss repository into the Galaxy instance.'''
        global repository_datatypes_count
        global base_datatypes_count
        global running_standalone
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        base_datatypes_count = int( self.get_datatypes_count() )
        strings_displayed = [ 'Handle', 'Never installed', 'tool dependencies', 'emboss', '5.0.0', 'package' ]
        self.install_repository( emboss_repository_name,
                                 common.test_user_1_name,
                                 'Test 0030 Repository Dependency Revisions',
                                 strings_displayed=strings_displayed,
                                 new_tool_panel_section_label='test_1210' )
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( emboss_repository_name, common.test_user_1_name )
        strings_displayed = [ 'emboss_0030',
                              'Galaxy wrappers for Emboss version 5.0.0 tools',
                              'user1',
                              self.url.replace( 'http://', '' ),
                              installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
        current_datatypes = int( self.get_datatypes_count() )
        # If we are running this test by itself, installing the emboss repository should also install the emboss_datatypes
        # repository, and this should add datatypes to the datatypes registry. If that is the case, verify that datatypes
        # have been added, otherwise verify that the count is unchanged.
        if running_standalone:
            assert current_datatypes == base_datatypes_count + repository_datatypes_count, \
                'Installing emboss resulted in unexpected count in datatypes registry, expected: %s, actual: %s, original: %s, added from repo: %s' % \
                ( str( base_datatypes_count + repository_datatypes_count ), str( current_datatypes ), str( base_datatypes_count ), str( repository_datatypes_count ) )
        else:
            assert current_datatypes == base_datatypes_count, \
                'Installing emboss added new datatypes, current datatypes: %s, original datatypes: %s' % \
                ( str( current_datatypes ), str( base_datatypes_count ) )

    def test_0015_uninstall_emboss_repository( self ):
        '''Uninstall the emboss repository.'''
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( emboss_repository_name, common.test_user_1_name )
        self.uninstall_repository( installed_repository )
        strings_not_displayed = [ installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_not_displayed=strings_not_displayed )

    def test_0020_reinstall_emboss_repository( self ):
        '''Reinstall the emboss repository.'''
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( emboss_repository_name, common.test_user_1_name )
        self.reinstall_repository( installed_repository )
        strings_displayed = [ 'emboss_0030',
                              'Galaxy wrappers for Emboss version 5.0.0 tools',
                              'user1',
                              self.url.replace( 'http://', '' ),
                              installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
        strings_displayed.extend( [ 'Installed tool shed repository', 'Valid tools', 'emboss' ] )
        self.display_installed_repository_manage_page( installed_repository, strings_displayed=strings_displayed )
        self.verify_tool_metadata_for_installed_repository( installed_repository )

    def test_0025_deactivate_emboss_repository( self ):
        '''Deactivate the emboss repository without removing it from disk.'''
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( emboss_repository_name, common.test_user_1_name )
        self.deactivate_repository( installed_repository )
        strings_not_displayed = [ installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_not_displayed=strings_not_displayed )

    def test_0030_reactivate_emboss_repository( self ):
        '''Reactivate the emboss repository and verify that it now shows up in the list of installed repositories.'''
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( emboss_repository_name, common.test_user_1_name )
        self.reactivate_repository( installed_repository )
        strings_displayed = [ 'emboss_0030',
                              'Galaxy wrappers for Emboss version 5.0.0 tools',
                              'user1',
                              self.url.replace( 'http://', '' ),
                              installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
        strings_displayed.extend( [ 'Installed tool shed repository', 'Valid tools', 'emboss' ] )
        self.display_installed_repository_manage_page( installed_repository, strings_displayed=strings_displayed )
        self.verify_tool_metadata_for_installed_repository( installed_repository )
