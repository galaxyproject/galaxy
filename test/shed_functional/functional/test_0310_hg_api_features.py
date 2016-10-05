import logging
import os

from shed_functional.base.twilltestcase import common, ShedTwillTestCase

log = logging.getLogger( __name__ )

repository_name = 'filtering_0310'
repository_description = "Galaxy's filtering tool for test 0310"
repository_long_description = "Long description of Galaxy's filtering tool for test 0310"

category_name = 'Test 0310 - HTTP Repo features'
category_description = 'Test 0310 for verifying the tool shed http interface to mercurial.'

'''
1. Create a repository.
2. Clone the repository to a local path.
'''


class TestHgWebFeatures( ShedTwillTestCase ):
    '''Test http mercurial interface.'''

    def test_0000_initiate_users( self ):
        """Create necessary user accounts and login as an admin user."""
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        self.test_db_util.get_private_role( test_user_1 )
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        test_user_2 = self.test_db_util.get_user( common.test_user_2_email )
        assert test_user_2 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_2_email
        self.test_db_util.get_private_role( test_user_2 )
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        self.test_db_util.get_private_role( admin_user )

    def test_0005_create_filtering_repository( self ):
        '''Create and populate the filtering_0310 repository.'''
        '''
        We are at step 1 - Create a repository.
        Create and populate the filtering_0310 repository.
        '''
        category = self.create_category( name=category_name, description=category_description )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=repository_name,
                                                    description=repository_description,
                                                    long_description=repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        self.upload_file( repository,
                          filename='filtering/filtering_1.1.0.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=True,
                          commit_message="Uploaded filtering 1.1.0.",
                          strings_displayed=[],
                          strings_not_displayed=[] )
        self.upload_file( repository,
                          filename='filtering/filtering_test_data.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message="Uploaded filtering test data.",
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0010_clone( self ):
        '''Clone the repository to a local path.'''
        '''
        We are at step 2 - Clone the repository to a local path.
        The repository should have the following files:

        filtering.py
        filtering.xml
        test-data/
        test-data/1.bed
        test-data/7.bed
        test-data/filter1_in3.sam
        test-data/filter1_inbad.bed
        test-data/filter1_test1.bed
        test-data/filter1_test2.bed
        test-data/filter1_test3.sam
        test-data/filter1_test4.bed
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        clone_path = self.generate_temp_path( 'test_0310', additional_paths=[ 'filtering_0310', 'user2' ] )
        self.clone_repository( repository, clone_path )
        files_in_repository = os.listdir( clone_path )
        assert 'filtering.py' in files_in_repository, 'File not found in repository: filtering.py'
