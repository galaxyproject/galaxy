from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os


import logging

log = logging.getLogger( __name__ )

repository_name = 'filtering_0310'
repository_description = "Galaxy's filtering tool for test 0310"
repository_long_description = "Long description of Galaxy's filtering tool for test 0310"

category_name = 'Test 0310 - HTTP Repo features'
category_description = 'Test 0310 for verifying the tool shed http interface to mercurial.'

# Declare clone_path here so multiple tests can access it.
clone_path = None

'''
1. Create a repository.
2. Clone the repository to a local path.
3. Change a file and try to push as non-owner.
4. Change another file and push as owner.
5. Verify that the changesets have been applied.
'''

class TestHgWebFeatures( ShedTwillTestCase ):
    '''Test http mercurial interface.'''
    
    def test_0000_initiate_users( self ):
        """Create necessary user accounts and login as an admin user."""
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % test_user_1_email
        test_user_1_private_role = self.test_db_util.get_private_role( test_user_1 )
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        test_user_2 = self.test_db_util.get_user( common.test_user_2_email )
        assert test_user_2 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_2_email
        test_user_2_private_role = self.test_db_util.get_private_role( test_user_2 )
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = self.test_db_util.get_private_role( admin_user )

    def test_0005_create_filtering_repository( self ):
        '''Create and populate the filtering_0310 repository.'''
        '''
        We are at step 1 - Create a repository.
        Create and populate the filtering_0310 repository.
        '''
        category = self.create_category( name=category_name, description=category_description )
        self.logout()
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
        
    def test_0010_edit_and_commit( self ):
        '''Edit a file and attempt a push as a user that does not have write access.'''
        '''
        We are at step 3 - Change a file and try to push as non-owner.
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
        
        We will be prepending a comment to filtering.py.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        clone_path = self.generate_temp_path( 'test_0310', additional_paths=[ 'filtering_0310', 'user2' ] )
        self.clone_repository( repository, clone_path )
        hgrepo = self.get_hg_repo( clone_path )
        files_in_repository = os.listdir( clone_path )
        assert 'filtering.py' in files_in_repository, 'File not found in repository: filtering.py'
        filepath = os.path.join( clone_path, 'filtering.py' )
        file_contents = [ '# This is a dummy comment to generate a new changeset.' ]
        file_contents.extend( file( filepath, 'r' ).readlines() )
        file( filepath, 'w' ).write( '\n'.join( file_contents ) )
        commit_options = dict( user=common.test_user_2_name, message='Added a line to filtering.py' )
        # The repository is owned by test_user_1, so this operation should fail.
        authorized = self.commit_and_push( repository, hgrepo, commit_options, username=common.test_user_2_name, password='testuser' )
        assert authorized is False, 'Test user 2 was able to commit and push to the remote repository.'

    def test_0015_edit_and_commit( self ):
        '''Edit a file again and attempt a push as a user that does have write access.'''
        '''
        We are at step 4 - Change another file and try to push as non-owner.
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
        
        We will be prepending a second comment to filtering.py.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        clone_path = self.generate_temp_path( 'test_0310', additional_paths=[ 'filtering_0310', 'user1' ] )
        self.clone_repository( repository, clone_path )
        hgrepo = self.get_hg_repo( clone_path )
        files_in_repository = os.listdir( clone_path )
        assert 'filtering.py' in files_in_repository, 'File not found in repository: filtering.py'
        filepath = os.path.join( clone_path, 'filtering.py' )
        file_contents = [ '# This is another dummy comment to generate a new changeset.' ]
        file_contents.extend( file( filepath, 'r' ).readlines() )
        file( filepath, 'w' ).write( '\n'.join( file_contents ) )
        commit_options = dict( user=common.test_user_1_name, message='Added another line to filtering.py.' )
        # The repository is owned by test_user_1, so this operation should succeed.
        authorized = self.commit_and_push( repository, hgrepo, commit_options, username=common.test_user_1_name, password='testuser' )
        assert authorized is True, 'Test user 1 was not able to commit and push to the remote repository.'
        
    def test_0020_verify_new_changelog( self ):
        '''Verify that the authorized commit was applied, and the unauthorized commit was not..'''
        '''
        We are at step 5 - Verify that the changeset has been applied.
        
        The repository changelog should now look like:
        
        0:nnnnnnnnnnnn: Uploaded filtering 1.1.0.
        1:nnnnnnnnnnnn: Uploaded filtering test data.
        2:nnnnnnnnnnnn: Added another line to filtering.py.
        
        The commit from test_user_2 should not be present in the changelog, since the repositories were cloned to separate locations.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        strings_displayed = [ 'Uploaded filtering 1.1.0.', 'Uploaded filtering test data.',
                              'Added another line to filtering.py.' ]
        strings_not_displayed = [ 'Added a line to filtering.py' ]
        self.check_repository_changelog( repository, strings_displayed=strings_displayed, strings_not_displayed=[] )
        
