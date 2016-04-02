from shed_functional.base.twilltestcase import common, ShedTwillTestCase

datatypes_repository_name = 'emboss_datatypes_0030'
datatypes_repository_description = "Galaxy applicable data formats used by Emboss tools."
datatypes_repository_long_description = "Galaxy applicable data formats used by Emboss tools.  This repository contains no tools."

emboss_repository_name = 'emboss_0030'
emboss_5_repository_name = 'emboss_5_0030'
emboss_6_repository_name = 'emboss_6_0030'
emboss_repository_description = 'Galaxy wrappers for Emboss version 5.0.0 tools for test 0030'
emboss_repository_long_description = 'Galaxy wrappers for Emboss version 5.0.0 tools for test 0030'


class TestRepositoryDependencyRevisions( ShedTwillTestCase ):
    '''Test dependencies on different revisions of a repository.'''

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

    def test_0005_create_category( self ):
        """Create a category for this test suite"""
        self.create_category( name='Test 0030 Repository Dependency Revisions', description='Testing repository dependencies by revision.' )

    def test_0010_create_emboss_5_repository( self ):
        '''Create and populate the emboss_5_0030 repository.'''
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        category = self.test_db_util.get_category_by_name( 'Test 0030 Repository Dependency Revisions' )
        repository = self.get_or_create_repository( name=emboss_5_repository_name,
                                                    description=emboss_repository_description,
                                                    long_description=emboss_repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ) )
        self.upload_file( repository,
                          filename='emboss/emboss.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded tool tarball.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0015_create_emboss_6_repository( self ):
        '''Create and populate the emboss_6_0030 repository.'''
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        category = self.test_db_util.get_category_by_name( 'Test 0030 Repository Dependency Revisions' )
        repository = self.get_or_create_repository( name=emboss_6_repository_name,
                                                    description=emboss_repository_description,
                                                    long_description=emboss_repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ) )
        self.upload_file( repository,
                          filename='emboss/emboss.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded tool tarball.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0020_create_emboss_datatypes_repository( self ):
        '''Create and populate the emboss_datatypes_0030 repository.'''
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        category = self.test_db_util.get_category_by_name( 'Test 0030 Repository Dependency Revisions' )
        repository = self.get_or_create_repository( name=datatypes_repository_name,
                                                    description=emboss_repository_description,
                                                    long_description=emboss_repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ) )
        self.upload_file( repository,
                          filename='emboss/datatypes/datatypes_conf.xml',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded datatypes_conf.xml.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0025_create_emboss_repository( self ):
        '''Create and populate the emboss_0030 repository.'''
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        category = self.test_db_util.get_category_by_name( 'Test 0030 Repository Dependency Revisions' )
        repository = self.get_or_create_repository( name=emboss_repository_name,
                                                    description=emboss_repository_description,
                                                    long_description=emboss_repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ) )
        self.upload_file( repository,
                          filename='emboss/emboss.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded the tool tarball.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0030_generate_repository_dependencies_for_emboss_5( self ):
        '''Generate a repository_dependencies.xml file specifying emboss_datatypes and upload it to the emboss_5 repository.'''
        datatypes_repository = self.test_db_util.get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        emboss_5_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_5_repository_name, common.test_user_1_name )
        repository_dependencies_path = self.generate_temp_path( 'test_0030', additional_paths=[ 'emboss5' ] )
        datatypes_tuple = ( self.url, datatypes_repository.name, datatypes_repository.user.username, self.get_repository_tip( datatypes_repository ) )
        self.create_repository_dependency( repository=emboss_5_repository, repository_tuples=[ datatypes_tuple ], filepath=repository_dependencies_path )

    def test_0035_generate_repository_dependencies_for_emboss_6( self ):
        '''Generate a repository_dependencies.xml file specifying emboss_datatypes and upload it to the emboss_6 repository.'''
        emboss_6_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_6_repository_name, common.test_user_1_name )
        datatypes_repository = self.test_db_util.get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        repository_dependencies_path = self.generate_temp_path( 'test_0030', additional_paths=[ 'emboss6' ] )
        datatypes_tuple = ( self.url, datatypes_repository.name, datatypes_repository.user.username, self.get_repository_tip( datatypes_repository ) )
        self.create_repository_dependency( repository=emboss_6_repository, repository_tuples=[ datatypes_tuple ], filepath=repository_dependencies_path )

    def test_0040_generate_repository_dependency_on_emboss_5( self ):
        '''Create and upload repository_dependencies.xml for the emboss_5_0030 repository.'''
        emboss_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        emboss_5_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_5_repository_name, common.test_user_1_name )
        repository_dependencies_path = self.generate_temp_path( 'test_0030', additional_paths=[ 'emboss', '5' ] )
        emboss_tuple = ( self.url, emboss_5_repository.name, emboss_5_repository.user.username, self.get_repository_tip( emboss_5_repository ) )
        self.create_repository_dependency( repository=emboss_repository, repository_tuples=[ emboss_tuple ], filepath=repository_dependencies_path )

    def test_0045_generate_repository_dependency_on_emboss_6( self ):
        '''Create and upload repository_dependencies.xml for the emboss_6_0030 repository.'''
        emboss_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        emboss_6_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_6_repository_name, common.test_user_1_name )
        repository_dependencies_path = self.generate_temp_path( 'test_0030', additional_paths=[ 'emboss', '5' ] )
        emboss_tuple = ( self.url, emboss_6_repository.name, emboss_6_repository.user.username, self.get_repository_tip( emboss_6_repository ) )
        self.create_repository_dependency( repository=emboss_repository, repository_tuples=[ emboss_tuple ], filepath=repository_dependencies_path )

    def test_0050_verify_repository_dependency_revisions( self ):
        '''Verify that different metadata revisions of the emboss repository have different repository dependencies.'''
        repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        repository_metadata = [ ( metadata.metadata, metadata.changeset_revision ) for metadata in self.get_repository_metadata( repository ) ]
        datatypes_repository = self.test_db_util.get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        datatypes_tip = self.get_repository_tip( datatypes_repository )
        strings_displayed = []
        # Iterate through all metadata revisions and check for repository dependencies.
        for metadata, changeset_revision in repository_metadata:
            # Add the dependency description and datatypes repository details to the strings to check.
            strings_displayed = [ 'emboss_datatypes_0030', 'user1', datatypes_tip ]
            strings_displayed.extend( [ 'Tool dependencies', 'emboss', '5.0.0', 'package' ] )
            self.display_manage_repository_page( repository,
                                                 changeset_revision=changeset_revision,
                                                 strings_displayed=strings_displayed )

    def test_0055_verify_repository_metadata( self ):
        '''Verify that resetting the metadata does not change it.'''
        emboss_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        emboss_5_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_5_repository_name, common.test_user_1_name )
        emboss_6_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_6_repository_name, common.test_user_1_name )
        datatypes_repository = self.test_db_util.get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        for repository in [ emboss_repository, emboss_5_repository, emboss_6_repository, datatypes_repository ]:
            self.verify_unchanged_repository_metadata( repository )
