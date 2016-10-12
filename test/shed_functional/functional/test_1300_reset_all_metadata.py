import os

from shed_functional.base.twilltestcase import common, ShedTwillTestCase

datatypes_repository_name = 'emboss_datatypes_0020'
datatypes_repository_description = "Galaxy applicable data formats used by Emboss tools."
datatypes_repository_long_description = "Galaxy applicable data formats used by Emboss tools.  This repository contains no tools."
emboss_repository_description = 'Galaxy wrappers for Emboss version 5.0.0 tools'
emboss_repository_long_description = 'Galaxy wrappers for Emboss version 5.0.0 tools'
workflow_filename = 'Workflow_for_0060_filter_workflow_repository.ga'
workflow_name = 'Workflow for 0060_filter_workflow_repository'
filtering_repository_description = "Galaxy's filtering tool for test 0040"
filtering_repository_long_description = "Long description of Galaxy's filtering tool for test 0040"

category_0000_name = 'Test 0000 Basic Repository Features 1'
category_0001_name = 'Test 0000 Basic Repository Features 2'
category_0010_name = 'Test 0010 Repository With Tool Dependencies'
category_0020_name = 'Test 0020 Basic Repository Dependencies'
category_0030_name = 'Test 0030 Repository Dependency Revisions'
category_0040_name = 'test_0040_repository_circular_dependencies'
category_0050_name = 'test_0050_repository_n_level_circular_dependencies'
category_0060_name = 'Test 0060 Workflow Features'

'''
This script will run in one of two possible ways:

1. Directly, by calling sh run_functional_tests.sh -toolshed test/tool_shed/functional/test_1300_reset_all_metadata.py.
 -OR-
2. After the previous test scripts have completed.

In the first case, it is desirable to have the Galaxy database in a state that is as close as possible to the state it would
be in following the second case. This means explicitly installing whatever repositories would be in an installed state following
the previous test scripts.
'''

base_datatypes_count = 0
repository_datatypes_count = 0
running_standalone = False


class TestResetInstalledRepositoryMetadata( ShedTwillTestCase ):
    '''Verify that the "Reset selected metadata" feature works.'''

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

    def test_0005_create_categories( self ):
        '''Create the categories for the repositories in this test script.'''
        self.login( email=common.admin_email, username=common.admin_username )
        self.create_category( name=category_0000_name, description='Test 0000 Basic Repository Features 1' )
        self.create_category( name=category_0001_name, description='Test 0000 Basic Repository Features 2' )
        self.create_category( name=category_0010_name, description='Tests for a repository with tool dependencies.' )
        self.create_category( name=category_0020_name, description='Testing basic repository dependency features.' )
        self.create_category( name=category_0030_name, description='Testing repository dependencies by revision.' )
        self.create_category( name=category_0040_name, description='Testing handling of circular repository dependencies.' )
        self.create_category( name=category_0050_name, description='Testing handling of circular repository dependencies to n levels.' )
        self.create_category( name=category_0060_name, description='Test 0060 - Workflow Features' )

    def test_0010_create_repositories_from_0000_series( self ):
        '''Create repository filtering_0000 if necessary.'''
        global running_standalone
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        category = self.create_category( name=category_0000_name, description='' )
        repository = self.get_or_create_repository( name='filtering_0000',
                                                    description="Galaxy's filtering tool",
                                                    long_description="Long description of Galaxy's filtering tool",
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ) )
        if self.repository_is_new( repository ):
            running_standalone = True
            self.upload_file( repository,
                              filename='filtering/filtering_1.1.0.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded filtering 1.1.0 tarball.',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            self.upload_file( repository,
                              filename='filtering/filtering_2.2.0.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded filtering 2.2.0 tarball.',
                              strings_displayed=[],
                              strings_not_displayed=[] )

    def test_0015_create_repositories_from_0010_series( self ):
        '''Create repository freebayes_0010.'''
        category = self.create_category( name=category_0010_name, description='' )
        repository = self.get_or_create_repository( name='freebayes_0010',
                                                    description="Galaxy's freebayes tool",
                                                    long_description="Long description of Galaxy's freebayes tool",
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            self.upload_file( repository,
                              filename='freebayes/freebayes.xml',
                              filepath=None,
                              valid_tools_only=False,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded freebayes.xml.',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            self.upload_file( repository,
                              filename='freebayes/tool_data_table_conf.xml.sample',
                              filepath=None,
                              valid_tools_only=False,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded tool_data_table_conf.xml.sample',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            self.upload_file( repository,
                              filename='freebayes/sam_fa_indices.loc.sample',
                              filepath=None,
                              valid_tools_only=False,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded sam_fa_indices.loc.sample',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            self.upload_file( repository,
                              filename='freebayes/tool_dependencies.xml',
                              filepath=None,
                              valid_tools_only=False,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded tool_dependencies.xml',
                              strings_displayed=[],
                              strings_not_displayed=[] )

    def test_0020_create_repositories_from_0020_series( self ):
        '''Create repositories emboss_0020 and emboss_datatypes_0020 if necessary.'''
        category = self.create_category( name=category_0020_name, description='' )
        repository = self.get_or_create_repository( name='emboss_datatypes_0020',
                                                    description="Galaxy applicable data formats used by Emboss tools.",
                                                    long_description="Galaxy applicable data formats used by Emboss tools. This repository contains no tools.",
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            self.upload_file( repository,
                              filename='emboss/datatypes/datatypes_conf.xml',
                              filepath=None,
                              valid_tools_only=False,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded datatypes_conf.xml.',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            repository = self.get_or_create_repository( name='emboss_0020',
                                                 description='Galaxy wrappers for Emboss version 5.0.0 tools',
                                                 long_description='Galaxy wrappers for Emboss version 5.0.0 tools',
                                                 owner=common.test_user_1_name,
                                                 category_id=self.security.encode_id( category.id ),
                                                 strings_displayed=[] )
            self.upload_file( repository,
                              filename='emboss/emboss.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded emboss.tar',
                              strings_displayed=[],
                              strings_not_displayed=[] )

    def test_0025_create_repositories_from_0030_series( self ):
        '''Create repositories emboss_0030, emboss_5_0030, emboss_6_0030, and emboss_datatypes_0030.'''
        global repository_datatypes_count
        category = self.create_category( name=category_0030_name, description='' )
        datatypes_repository = self.get_or_create_repository( name='emboss_datatypes_0030',
                                                              description=datatypes_repository_description,
                                                              long_description=datatypes_repository_long_description,
                                                              owner=common.test_user_1_name,
                                                              category_id=self.security.encode_id( category.id ),
                                                              strings_displayed=[] )
        if self.repository_is_new( datatypes_repository ):
            self.upload_file( datatypes_repository,
                              filename='emboss/datatypes/datatypes_conf.xml',
                              filepath=None,
                              valid_tools_only=False,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded datatypes_conf.xml.',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            repository_datatypes_count = int( self.get_repository_datatypes_count( datatypes_repository ) )
            emboss_5_repository = self.get_or_create_repository( name='emboss_5_0030',
                                                                 description=emboss_repository_description,
                                                                 long_description=emboss_repository_long_description,
                                                                 owner=common.test_user_1_name,
                                                                 category_id=self.security.encode_id( category.id ),
                                                                 strings_displayed=[] )
            self.upload_file( emboss_5_repository,
                              filename='emboss/emboss.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded emboss.tar',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            repository_dependencies_path = self.generate_temp_path( 'test_0330', additional_paths=[ 'emboss', '5' ] )
            dependency_tuple = ( self.url, datatypes_repository.name, datatypes_repository.user.username, self.get_repository_tip( datatypes_repository ) )
            self.create_repository_dependency( repository=emboss_5_repository, repository_tuples=[ dependency_tuple ], filepath=repository_dependencies_path )
            emboss_6_repository = self.get_or_create_repository( name='emboss_6_0030',
                                                                 description=emboss_repository_description,
                                                                 long_description=emboss_repository_long_description,
                                                                 owner=common.test_user_1_name,
                                                                 category_id=self.security.encode_id( category.id ),
                                                                 strings_displayed=[] )
            self.upload_file( emboss_6_repository,
                              filename='emboss/emboss.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded emboss.tar',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            repository_dependencies_path = self.generate_temp_path( 'test_0330', additional_paths=[ 'emboss', '6' ] )
            dependency_tuple = ( self.url, datatypes_repository.name, datatypes_repository.user.username, self.get_repository_tip( datatypes_repository ) )
            self.create_repository_dependency( repository=emboss_6_repository, repository_tuples=[ dependency_tuple ], filepath=repository_dependencies_path )
            emboss_repository = self.get_or_create_repository( name='emboss_0030',
                                                               description=emboss_repository_description,
                                                               long_description=emboss_repository_long_description,
                                                               owner=common.test_user_1_name,
                                                               category_id=self.security.encode_id( category.id ),
                                                               strings_displayed=[] )
            self.upload_file( emboss_repository,
                              filename='emboss/emboss.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded emboss.tar',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            repository_dependencies_path = self.generate_temp_path( 'test_0330', additional_paths=[ 'emboss', '5' ] )
            dependency_tuple = ( self.url, emboss_5_repository.name, emboss_5_repository.user.username, self.get_repository_tip( emboss_5_repository ) )
            self.create_repository_dependency( repository=emboss_repository, repository_tuples=[ dependency_tuple ], filepath=repository_dependencies_path )
            dependency_tuple = ( self.url, emboss_6_repository.name, emboss_6_repository.user.username, self.get_repository_tip( emboss_6_repository ) )
            self.create_repository_dependency( repository=emboss_repository, repository_tuples=[ dependency_tuple ], filepath=repository_dependencies_path )

    def test_0030_create_repositories_from_0040_series( self ):
        '''Create repositories freebayes_0040 and filtering_0040.'''
        category = self.create_category( name=category_0040_name, description='' )
        repository = self.get_or_create_repository( name='freebayes_0040',
                                                    description="Galaxy's freebayes tool",
                                                    long_description="Long description of Galaxy's freebayes tool",
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            self.upload_file( repository,
                              filename='freebayes/freebayes.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded the tool tarball.',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            repository = self.get_or_create_repository( name='filtering_0040',
                                                        description=filtering_repository_description,
                                                        long_description=filtering_repository_long_description,
                                                        owner=common.test_user_1_name,
                                                        category_id=self.security.encode_id( category.id ),
                                                        strings_displayed=[] )
            self.upload_file( repository,
                              filename='filtering/filtering_1.1.0.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded the tool tarball for filtering 1.1.0.',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            repository = self.test_db_util.get_repository_by_name_and_owner( 'freebayes_0040', common.test_user_1_name )
            filtering_repository = self.test_db_util.get_repository_by_name_and_owner( 'filtering_0040', common.test_user_1_name )
            repository_dependencies_path = self.generate_temp_path( 'test_1340', additional_paths=[ 'filtering' ] )
            repository_tuple = ( self.url, repository.name, repository.user.username, self.get_repository_tip( repository ) )
            self.create_repository_dependency( repository=filtering_repository, repository_tuples=[ repository_tuple ], filepath=repository_dependencies_path )
            repository = self.test_db_util.get_repository_by_name_and_owner( 'filtering_0040', common.test_user_1_name )
            freebayes_repository = self.test_db_util.get_repository_by_name_and_owner( 'freebayes_0040', common.test_user_1_name )
            repository_dependencies_path = self.generate_temp_path( 'test_1340', additional_paths=[ 'freebayes' ] )
            repository_tuple = ( self.url, repository.name, repository.user.username, self.get_repository_tip( repository ) )
            self.create_repository_dependency( repository=freebayes_repository, repository_tuples=[ repository_tuple ], filepath=repository_dependencies_path )

    def test_0035_create_repositories_from_0050_series( self ):
        '''Create repositories emboss_0050, emboss_datatypes_0050, filtering_0050, freebayes_0050.'''
        category = self.create_category( name=category_0050_name, description='' )
        datatypes_repository = self.get_or_create_repository( name='emboss_datatypes_0050',
                                                    description="Datatypes for emboss",
                                                    long_description="Long description of Emboss' datatypes",
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        if self.repository_is_new( datatypes_repository ):
            emboss_repository = self.get_or_create_repository( name='emboss_0050',
                                                        description="Galaxy's emboss tool",
                                                        long_description="Long description of Galaxy's emboss tool",
                                                        owner=common.test_user_1_name,
                                                        category_id=self.security.encode_id( category.id ),
                                                        strings_displayed=[] )
            filtering_repository = self.get_or_create_repository( name='filtering_0050',
                                                                  description="Galaxy's filtering tool",
                                                                  long_description="Long description of Galaxy's filtering tool",
                                                                  owner=common.test_user_1_name,
                                                                  category_id=self.security.encode_id( category.id ),
                                                                  strings_displayed=[] )
            freebayes_repository = self.get_or_create_repository( name='freebayes_0050',
                                                                  description="Galaxy's freebayes tool",
                                                                  long_description="Long description of Galaxy's freebayes tool",
                                                                  owner=common.test_user_1_name,
                                                                  category_id=self.security.encode_id( category.id ),
                                                                  strings_displayed=[] )
            self.upload_file( datatypes_repository,
                              filename='emboss/datatypes/datatypes_conf.xml',
                              filepath=None,
                              valid_tools_only=False,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded datatypes_conf.xml.',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            self.upload_file( emboss_repository,
                              filename='emboss/emboss.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded emboss.tar',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            self.upload_file( freebayes_repository,
                              filename='freebayes/freebayes.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded freebayes tarball.',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            self.upload_file( filtering_repository,
                              filename='filtering/filtering_1.1.0.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded filtering 1.1.0 tarball.',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            repository_dependencies_path = self.generate_temp_path( 'test_0350', additional_paths=[ 'emboss' ] )
            dependency_tuple = ( self.url, datatypes_repository.name, datatypes_repository.user.username, self.get_repository_tip( datatypes_repository ) )
            self.create_repository_dependency( repository=emboss_repository, repository_tuples=[ dependency_tuple ], filepath=repository_dependencies_path )
            repository_dependencies_path = self.generate_temp_path( 'test_0350', additional_paths=[ 'filtering' ] )
            dependency_tuple = ( self.url, emboss_repository.name, emboss_repository.user.username, self.get_repository_tip( emboss_repository ) )
            self.create_repository_dependency( repository=filtering_repository, repository_tuples=[ dependency_tuple ], filepath=repository_dependencies_path )
            repository_dependencies_path = self.generate_temp_path( 'test_0350', additional_paths=[ 'freebayes' ] )
            dependency_tuple = ( self.url, filtering_repository.name, filtering_repository.user.username, self.get_repository_tip( filtering_repository ) )
            self.create_repository_dependency( repository=emboss_repository, repository_tuples=[ dependency_tuple ], filepath=repository_dependencies_path )
            dependency_tuples = [ ( self.url, datatypes_repository.name, datatypes_repository.user.username, self.get_repository_tip( datatypes_repository ) ),
                                  ( self.url, emboss_repository.name, emboss_repository.user.username, self.get_repository_tip( emboss_repository ) ),
                                  ( self.url, filtering_repository.name, filtering_repository.user.username, self.get_repository_tip( filtering_repository ) ),
                                  ( self.url, freebayes_repository.name, freebayes_repository.user.username, self.get_repository_tip( freebayes_repository ) ) ]
            self.create_repository_dependency( repository=freebayes_repository, repository_tuples=dependency_tuples, filepath=repository_dependencies_path )

    def test_0035_create_repositories_from_0060_series( self ):
        category = self.create_category( name=category_0060_name, description='' )
        workflow_repository = self.get_or_create_repository( name='filtering_0060',
                                                             description="Galaxy's filtering tool",
                                                             long_description="Long description of Galaxy's filtering tool",
                                                             owner=common.test_user_1_name,
                                                             category_id=self.security.encode_id( category.id ),
                                                             strings_displayed=[] )
        if self.repository_is_new( workflow_repository ):
            workflow = open( self.get_filename( 'filtering_workflow/Workflow_for_0060_filter_workflow_repository.ga' ), 'r' ).read()
            workflow = workflow.replace(  '__TEST_TOOL_SHED_URL__', self.url.replace( 'http://', '' ) )
            workflow_filepath = self.generate_temp_path( 'test_0360', additional_paths=[ 'filtering_workflow' ] )
            if not os.path.exists( workflow_filepath ):
                os.makedirs( workflow_filepath )
            open( os.path.join( workflow_filepath, workflow_filename ), 'w+' ).write( workflow )
            self.upload_file( workflow_repository,
                              filename=workflow_filename,
                              filepath=workflow_filepath,
                              valid_tools_only=True,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded filtering workflow.',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            self.upload_file( workflow_repository,
                              filename='filtering/filtering_2.2.0.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded filtering 2.2.0 tarball.',
                              strings_displayed=[],
                              strings_not_displayed=[] )

    def test_9900_install_all_missing_repositories( self ):
        '''Call the install_repository method to ensure that all required repositories are installed.'''
        global repository_datatypes_count
        global base_datatypes_count
        global running_standalone
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        base_datatypes_count = int( self.get_datatypes_count() )
        self.install_repository( 'filtering_0000', common.test_user_1_name, category_0000_name, strings_displayed=[] )
        self.install_repository( 'freebayes_0010', common.test_user_1_name, category_0010_name, strings_displayed=[] )
        self.install_repository( 'emboss_0020', common.test_user_1_name, category_0020_name, strings_displayed=[] )
        self.install_repository( 'emboss_5_0030', common.test_user_1_name, category_0030_name, strings_displayed=[] )
        self.install_repository( 'freebayes_0050', common.test_user_1_name, category_0050_name, strings_displayed=[] )
        self.install_repository( 'filtering_0060', common.test_user_1_name, category_0060_name, strings_displayed=[] )
        current_datatypes = int( self.get_datatypes_count() )
        # If we are running this test by itself, installing the emboss repository should also install the emboss_datatypes
        # repository, and this should add datatypes to the datatypes registry. If that is the case, verify that datatypes
        # have been added, otherwise verify that the count is unchanged.
        if running_standalone:
            message = 'Installing emboss did not add new datatypes.\nFound: %d\nExpected: %d' % \
                ( current_datatypes, base_datatypes_count + repository_datatypes_count )
            assert current_datatypes > base_datatypes_count, message
        else:
            assert current_datatypes == base_datatypes_count, 'Installing emboss added new datatypes.'

    def test_9905_reset_metadata_on_all_repositories( self ):
        '''Reset metadata on all repositories, then verify that it has not changed.'''
        repository_metadata = dict()
        repositories = self.test_db_util.get_all_installed_repositories( actually_installed=True )
        for repository in repositories:
            repository_metadata[ self.security.encode_id( repository.id ) ] = repository.metadata
        self.reset_metadata_on_selected_installed_repositories( list(repository_metadata.keys()) )
        for repository in repositories:
            self.test_db_util.ga_refresh( repository )
            old_metadata = repository_metadata[ self.security.encode_id( repository.id ) ]
            # When a repository with tools to be displayed in a tool panel section is deactivated and reinstalled,
            # the tool panel section remains in the repository metadata. However, when the repository's metadata
            # is subsequently reset, the tool panel section is removed from the repository metadata. While this
            # is normal and expected behavior, the functional tests assume that repository metadata will not change
            # in any way after a reset. A workaround is to remove the tool panel section from the stored repository
            # metadata dict, in order to eliminate the misleading detection of changed metadata.
            if 'tool_panel_section' in old_metadata and 'tool_panel_section' not in repository.metadata:
                del old_metadata[ 'tool_panel_section' ]
            assert repository.metadata == old_metadata, 'Metadata for %s repository %s changed after reset. \nOld: %s\nNew: %s' % \
                ( repository.status, repository.name, old_metadata, repository.metadata )
