from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
repository_name = 'filtering_0410'
repository_description = 'Galaxy filtering tool for test 0410'
repository_long_description = 'Long description of Galaxy filtering tool for test 0410'

'''
1. Create a repository in the tool shed owned by test_user_1.
2. Have test_user_2 complete a review of the repository.
3. Have test_user_1 browse the review.
4. Have test_user_3 browse the repository and make sure they are not allowed to browse the review.
5. Have test_user_1 give write permission on the repository to the test_user_3.
6. Have test_user_3 browse the repository again and they should now have the ability to browse the review.
7. Have test_user_3 browse the review.
'''


class TestRepositoryComponentReviews( ShedTwillTestCase ):
    '''Test repository component review features.'''
    def test_0000_initiate_users( self ):
        """Create necessary user accounts and login as an admin user."""
        """
        Create all the user accounts that are needed for this test script to run independently of other test.
        Previously created accounts will not be re-created.
        """
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        test_user_1_private_role = self.test_db_util.get_private_role( test_user_1 )
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        test_user_2 = self.test_db_util.get_user( common.test_user_2_email )
        assert test_user_2 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_2_email
        test_user_2_private_role = self.test_db_util.get_private_role( test_user_2 )
        self.logout()
        self.login( email=common.test_user_3_email, username=common.test_user_3_name )
        test_user_3 = self.test_db_util.get_user( common.test_user_3_email )
        assert test_user_3 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_3_email
        test_user_3_private_role = self.test_db_util.get_private_role( test_user_3 )
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        admin_user_private_role = self.test_db_util.get_private_role( admin_user )
    def test_0005_grant_reviewer_role( self ):
        '''Grant the repository reviewer role to test_user_2.'''
        """
        We now have an admin user (admin_user) and three non-admin users (test_user_1, test_user_2, and test_user_3). Grant the repository 
        reviewer role to test_user_2, who will not be the owner of the reviewed repositories, and do not grant any roles to test_user_3 yet.
        """
        reviewer_role = self.test_db_util.get_role_by_name( 'Repository Reviewer' )
        test_user_2 = self.test_db_util.get_user( common.test_user_2_email )
        self.grant_role_to_user( test_user_2, reviewer_role )
    def test_0010_verify_repository_review_components( self ):
        '''Ensure that the required review components exist.'''
        """
        Make sure all the components we are to review are recorded in the database.
        """
        self.add_repository_review_component( name='Repository dependencies', 
                                              description='Repository dependencies defined in a file named repository_dependencies.xml included in the repository' )
        strings_displayed=[ 'Data types', 'Functional tests', 'README', 'Repository dependencies', 'Tool dependencies', 'Tools', 'Workflows' ]
        self.manage_review_components( strings_displayed=strings_displayed )
    def test_0015_create_repository( self ):
        """Create and populate the filtering repository"""
        """
        We are at step 1.
        Log in as test_user_1 and create the filtering repository, then upload a basic set of 
        components to be reviewed in subsequent tests.
        """
        category = self.create_category( name='Test 0400 Repository Component Reviews', description='Test 0400 Repository Component Reviews' )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        strings_displayed = [ 'Repository %s' % "'%s'" % repository_name, 
                              'Repository %s has been created' % "<b>%s</b>" % repository_name ]
        repository = self.get_or_create_repository( name=repository_name, 
                                                    description=repository_description, 
                                                    long_description=repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=strings_displayed )
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
                          filename='filtering/filtering_test_data.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False, 
                          commit_message='Uploaded filtering test data.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        self.upload_file( repository, 
                          filename='readme.txt',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False, 
                          commit_message='Uploaded readme.txt.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
    def test_0020_review_repository( self ):
        '''Complete a review of the filtering repository.'''
        '''
        We are at step 2 - Have test_user_2 complete a review of the repository.
        Review all components of the filtering repository, with the appropriate contents and approved/not approved/not applicable status.
        '''
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        review_contents_dict = { 
                                 'Data types': dict(), 
                                 'README': dict( rating=5, comment='Clear and concise readme file, a true pleasure to read.', approved='yes', private='no' ),
                                 'Functional tests': dict( rating=5, comment='A good set of functional tests.', approved='yes', private='no' ),
                                 'Repository dependencies': dict(),
                                 'Tool dependencies': dict(),
                                 'Tools': dict( rating=5, comment='Excellent tool, easy to use.', approved='yes', private='no' ),
                                 'Workflows': dict()
                               }
        self.create_repository_review( repository, review_contents_dict )
    def test_0025_verify_repository_review( self ):
        '''Verify that the review was completed and displays properly.'''
        '''
        We are at step 3 - Have test_user_1 browse the review.
        Verify that all the review components were submitted, and that the repository owner can see the review.
        '''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        strings_displayed = [ 'Data types', 'Functional tests', 'yes', 'A good set of functional tests.', 'README', 'yes', 'Workflows', 'Tools' ]
        strings_displayed.extend( [ 'Clear and concise readme file, a true pleasure to read.', 'Tool dependencies', 'not_applicable' ] )
        strings_displayed.extend( [ 'Repository dependencies', 'Excellent tool, easy to use.'  ] )
        strings_displayed = [ 'Browse reviews of this repository' ]
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed )
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed )
    def test_0030_browse_with_other_user( self ):
        '''Verify that test_user_3 is blocked from browsing the review.'''
        '''
        We are at step 4 - Have test_user_3 browse the repository and make sure they are not allowed to browse the review.
        '''
        self.logout()
        self.login( email=common.test_user_3_email, username=common.test_user_3_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        strings_not_displayed = [ 'Browse reviews of this repository' ]
        self.display_manage_repository_page( repository, strings_not_displayed=strings_not_displayed )
        strings_not_displayed = [ 'A good set of functional tests.', 'Clear and concise readme file, a true pleasure to read.' ]
        strings_not_displayed.append( 'Excellent tool, easy to use.' )
        changeset_revision = self.get_repository_tip( repository )
        review = self.test_db_util.get_repository_review_by_user_id_changeset_revision( user.id, repository.id, changeset_revision )
        self.browse_component_review( review, strings_not_displayed=strings_not_displayed )
    def test_0035_grant_write_access_to_other_user( self ):
        '''Grant write access on the filtering_0410 repository to test_user_3.'''
        '''
        We are at step 5 - Have test_user_1 give write permission on the repository to the test_user_3.
        '''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.grant_write_access( repository, usernames=[ common.test_user_3_name ] )
    def test_0040_verify_test_user_3_can_browse_reviews( self ):
        '''Check that test_user_3 can now browse reviews.'''
        '''
        We are at step 6 - Have test_user_3 browse the repository again and they should now have the ability to browse the review.
        '''
        self.logout()
        self.login( email=common.test_user_3_email, username=common.test_user_3_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        strings_displayed = [ 'Browse reviews of this repository' ]
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed )
    def test_0045_verify_browse_review_with_write_access( self ):
        '''Check that test_user_3 can now display reviews.'''
        '''
        We are at step 7 - Have test_user_3 browse the review.
        '''
        self.logout()
        self.login( email=common.test_user_3_email, username=common.test_user_3_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        strings_displayed = [ 'A&nbsp;good&nbsp;set&nbsp;of&nbsp;functional&nbsp;tests.', 
                              'Clear&nbsp;and&nbsp;concise&nbsp;readme&nbsp;file',
                              'a&nbsp;true&nbsp;pleasure&nbsp;to&nbsp;read.',
                              'Excellent&nbsp;tool,&nbsp;easy&nbsp;to&nbsp;use.' ]
        changeset_revision = self.get_repository_tip( repository )
        review = self.test_db_util.get_repository_review_by_user_id_changeset_revision( user.id, repository.id, changeset_revision )
        self.browse_component_review( review, strings_displayed=strings_displayed )
        
