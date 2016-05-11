import logging

from shed_functional.base.twilltestcase import common, ShedTwillTestCase

log = logging.getLogger( __name__ )

repositories = dict( column=dict( name='column_maker_0540',
                                  description='Description for column_maker_0540',
                                  long_description='Long description for column_maker_0540' ),
                     convert=dict( name='convert_chars_0540',
                                   description='Description for convert_chars_0540',
                                   long_description='Long description for convert_chars_0540' ),
                     bwa=dict( name='package_bwa_0_5_9_0540',
                               description='Description for package_bwa_0_5_9_0540',
                               long_description='Long description for package_bwa_0_5_9_0540' ) )

category_name = 'Test 0540'
category_description = 'Verify API endpoint to retrieve all metadata'

'''
1. Create repository column_maker_0540 as user user1.

2. Create repository convert_chars_0540 with dependency on column_maker_0540.

3. Create repository package_bwa_0_5_9_0540.

4. Create dependency on package_bwa_0_5_9_0540 for convert_chars_0540.

5. Load /api/repositories/convert_chars_0540.id/metadata and verify contents.
'''


class TestGetAllMetadata( ShedTwillTestCase ):
    '''Verify that the code correctly handles the repository admin role.'''

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

    def test_0005_create_bwa_package_repository( self ):
        '''Create and populate package_bwa_0_5_9_0540.'''
        category = self.create_category( name=category_name, description=category_description )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        # Create a repository named package_bwa_0_5_9_0100 owned by user1.
        repository = self.get_or_create_repository( name=repositories['bwa']['name'],
                                                    description=repositories['bwa']['description'],
                                                    long_description=repositories['bwa']['long_description'],
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        assert repository is not None, 'Error creating repository %s' % repositories['bwa']['name']
        self.upload_file( repository,
                          filename='0540_files/package_bwa/tool_dependencies.xml',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded tool_dependencies.xml.',
                          strings_displayed=[ 'This repository currently contains a single file named <b>tool_dependencies.xml</b>' ],
                          strings_not_displayed=[] )
        # Visit the manage repository page for package_bwa_0_5_9_0100.
        self.display_manage_repository_page( repository, strings_displayed=[ 'Tool dependencies', 'will not be', 'to this repository' ] )

    def test_0010_create_convert_repository( self ):
        '''Create the convert_chars_0540 repository.'''
        category = self.create_category( name=category_name, description=category_description )
        repository = self.get_or_create_repository( name=repositories['convert']['name'],
                                                    description=repositories['convert']['description'],
                                                    long_description=repositories['convert']['long_description'],
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        assert repository is not None, 'Error creating repository %s' % repositories['convert']['name']
        self.upload_file( repository,
                          filename='0540_files/convert_chars/convert_chars.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded column maker 1.0.',
                          strings_displayed=[],
                          strings_not_displayed=[] )
        # Add a dependency on BWA.
        self.upload_file( repository,
                          filename='0540_files/convert_chars/tool_dependencies.xml',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded column maker 1.0.',
                          strings_displayed=[],
                          strings_not_displayed=[] )
        # Visit the manage repository page for convert_chars_0540.
        self.display_manage_repository_page( repository, strings_displayed=[ repositories['bwa']['name'] ] )

    def test_0015_create_column_repository( self ):
        '''Create the column_maker_0540 repository.'''
        category = self.create_category( name=category_name, description=category_description )
        repository = self.get_or_create_repository( name=repositories['column']['name'],
                                                    description=repositories['column']['description'],
                                                    long_description=repositories['column']['long_description'],
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        assert repository is not None, 'Error creating repository %s' % repositories['column']['name']
        self.upload_file( repository,
                          filename='0540_files/column_maker/column_maker.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded column maker 1.0.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0020_create_repository_dependency( self ):
        '''Make column_maker depend on convert_chars.'''
        repository = self.test_db_util.get_repository_by_name_and_owner( repositories[ 'column' ][ 'name' ],
                                                                         common.test_user_1_name )
        self.upload_file( repository,
                          filename='0540_files/column_maker/repository_dependencies.xml',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded column maker 2.0.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0025_verify_dependency_json( self ):
        '''
        Load the API endpoint to retrieve all repository metadata and verify
        that all three repository names are displayed.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repositories[ 'column' ][ 'name' ],
                                                                         common.test_user_1_name )
        strings_displayed = [ repositories[ 'column' ][ 'name' ],
                              repositories[ 'convert' ][ 'name' ],
                              repositories[ 'bwa' ][ 'name' ] ]
        self.fetch_repository_metadata( repository, strings_displayed=strings_displayed, strings_not_displayed=None )
