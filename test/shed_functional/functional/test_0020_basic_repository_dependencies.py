from shed_functional.base.twilltestcase import common, ShedTwillTestCase

datatypes_repository_name = 'emboss_datatypes_0020'
datatypes_repository_description = "Galaxy applicable data formats used by Emboss tools."
datatypes_repository_long_description = "Galaxy applicable data formats used by Emboss tools.  This repository contains no tools."

emboss_repository_name = 'emboss_0020'
emboss_repository_description = 'Galaxy wrappers for Emboss version 5.0.0 tools for test 0020'
emboss_repository_long_description = 'Galaxy wrappers for Emboss version 5.0.0 tools for test 0020'


class TestBasicRepositoryDependencies( ShedTwillTestCase ):
    '''Testing emboss 5 with repository dependencies.'''

    def test_0000_initiate_users( self ):
        """Create necessary user accounts and login as an admin user."""
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
        self.create_category( name='Test 0020 Basic Repository Dependencies', description='Testing basic repository dependency features.' )

    def test_0010_create_emboss_datatypes_repository_and_upload_tarball( self ):
        '''Create and populate the emboss_datatypes repository.'''
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        category = self.test_db_util.get_category_by_name( 'Test 0020 Basic Repository Dependencies' )
        repository = self.get_or_create_repository( name=datatypes_repository_name,
                                             description=datatypes_repository_description,
                                             long_description=datatypes_repository_long_description,
                                             owner=common.test_user_1_name,
                                             category_id=self.security.encode_id( category.id ),
                                             strings_displayed=[] )
        self.upload_file( repository,
                          filename='emboss/datatypes/datatypes_conf.xml',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded datatypes_conf.xml.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0015_verify_datatypes_in_datatypes_repository( self ):
        '''Verify that the emboss_datatypes repository contains datatype entries.'''
        repository = self.test_db_util.get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        self.display_manage_repository_page( repository, strings_displayed=[ 'Datatypes', 'equicktandem', 'hennig86', 'vectorstrip' ] )

    def test_0020_create_emboss_5_repository_and_upload_files( self ):
        '''Create and populate the emboss_5_0020 repository.'''
        category = self.test_db_util.get_category_by_name( 'Test 0020 Basic Repository Dependencies' )
        repository = self.get_or_create_repository( name=emboss_repository_name,
                                             description=emboss_repository_description,
                                             long_description=emboss_repository_long_description,
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

    def test_0025_generate_and_upload_repository_dependencies_xml( self ):
        '''Generate and upload the repository_dependencies.xml file'''
        repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        datatypes_repository = self.test_db_util.get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        repository_dependencies_path = self.generate_temp_path( 'test_0020', additional_paths=[ 'emboss', '5' ] )
        repository_tuple = ( self.url, datatypes_repository.name, datatypes_repository.user.username, self.get_repository_tip( datatypes_repository ) )
        self.create_repository_dependency( repository=repository, repository_tuples=[ repository_tuple ], filepath=repository_dependencies_path )

    def test_0030_verify_emboss_5_dependencies( self ):
        '''Verify that the emboss_5 repository now depends on the emboss_datatypes repository with correct name, owner, and changeset revision.'''
        repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        datatypes_repository = self.test_db_util.get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        changeset_revision = self.get_repository_tip( datatypes_repository )
        strings_displayed = [ 'Tool dependencies',
                              'emboss',
                              '5.0.0',
                              'package',
                              'emboss_datatypes_0020',
                              'user1',
                              changeset_revision,
                              'Repository dependencies' ]
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed )

    def test_0040_verify_repository_metadata( self ):
        '''Verify that resetting the metadata does not change it.'''
        emboss_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        datatypes_repository = self.test_db_util.get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        self.verify_unchanged_repository_metadata( emboss_repository )
        self.verify_unchanged_repository_metadata( datatypes_repository )
