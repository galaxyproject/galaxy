from shed_functional.base.twilltestcase import common, ShedTwillTestCase

repository_name = 'filtering_0400'
repository_description = 'Galaxy filtering tool for test 0400'
repository_long_description = 'Long description of Galaxy filtering tool for test 0400'

'''
1. Create users.
2. Grant reviewer role to test_user_2.
3. Check that the review components that are to be tested are defined in this tool shed instance.
4. Create a repository, owned by test_user_1, to be reviewed by test_user_2.
5. Review the datatypes component on the repository.
6. Check that no other components besides datatypes display as reviewed.
7. Review the functional tests component on the repository.
8. Check that only functional tests and datatypes display as reviewed.
9. Review the readme component on the repository.
10. Check that only functional tests, datatypes, and readme display as reviewed.
11. Review the repository dependencies component.
12. Check that only repository dependencies, functional tests, datatypes, and readme display as reviewed.
13. Review the tool dependencies component.
14. Check that only tool dependencies, repository dependencies, functional tests, datatypes, and readme display as reviewed.
15. Review the tools component.
16. Check that only tools, tool dependencies, repository dependencies, functional tests, datatypes, and readme display as reviewed.
17. Review the workflows component.
18. Check that all components display as reviewed.
19. Upload readme.txt to the repository.
20. Copy the previous review, and update the readme component review to reflect the existence of a readme file.
21. Check that the readme component review has been updated, and the other component reviews are present.
22. Upload test data to the repository. This will also create a new changeset revision.
23. Review the functional tests component on the repository, copying the other components from the previous review.
24. Verify that the functional tests component review has been updated, and as in step 21, the other reviews are unchanged.
25. Upload a new version of the tool.
26. Review the new revision's functional tests component.
27. Verify that the functional tests component review displays correctly.
'''


class TestRepositoryComponentReviews( ShedTwillTestCase ):
    '''Test repository component review features.'''
    def test_0000_initiate_users( self ):
        """Create necessary user accounts and login as an admin user."""
        """
        We are at step 1.
        Create all the user accounts that are needed for this test script to run independently of other test.
        Previously created accounts will not be re-created.
        """
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

    def test_0005_grant_reviewer_role( self ):
        '''Grant the repository reviewer role to test_user_2.'''
        """
        We are at step 2.
        We now have an admin user (admin_user) and two non-admin users (test_user_1 and test_user_2). Grant the repository
        reviewer role to test_user_2, who will not be the owner of the reviewed repositories.
        """
        reviewer_role = self.test_db_util.get_role_by_name( 'Repository Reviewer' )
        test_user_2 = self.test_db_util.get_user( common.test_user_2_email )
        self.grant_role_to_user( test_user_2, reviewer_role )

    def test_0010_verify_repository_review_components( self ):
        '''Ensure that the required review components exist.'''
        """
        We are at step 3.
        We now have an admin user (admin_user) and two non-admin users (test_user_1 and test_user_2). Grant the repository
        reviewer role to test_user_2, who will not be the owner of the reviewed repositories.
        """
        strings_not_displayed = [ 'Repository dependencies' ]
        self.manage_review_components( strings_not_displayed=strings_not_displayed )
        self.add_repository_review_component( name='Repository dependencies',
                                              description='Repository dependencies defined in a file named repository_dependencies.xml included in the repository' )
        strings_displayed = [ 'Data types', 'Functional tests', 'README', 'Repository dependencies', 'Tool dependencies', 'Tools', 'Workflows' ]
        self.manage_review_components( strings_displayed=strings_displayed )

    def test_0015_create_repository( self ):
        """Create and populate the filtering repository"""
        """
        We are at step 4.
        Log in as test_user_1 and create the filtering repository, then upload a basic set of
        components to be reviewed in subsequent tests.
        """
        category = self.create_category( name='Test 0400 Repository Component Reviews', description='Test 0400 Repository Component Reviews' )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        strings_displayed = self.expect_repo_created_strings(repository_name)
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

    def test_0020_review_initial_revision_data_types( self ):
        '''Review the datatypes component for the current tip revision.'''
        """
        We are at step 5.
        Log in as test_user_2 and review the data types component of the filtering repository owned by test_user_1.
        # Review this revision:
        #    Data types (N/A)
        """
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        # The create_repository_review method takes a dict( component label=review contents ).
        # If review_contents is empty, it marks that component as not applicable. The review
        # contents dict should have the structure:
        # {
        #   rating: 1-5,
        #   comment: <text>
        #   approved: yes/no
        #   private: yes/no
        # }
        review_contents_dict = { 'Data types': dict() }
        self.create_repository_review( repository, review_contents_dict )

    def test_0025_verify_datatype_review( self ):
        '''Verify that the datatypes component review displays correctly.'''
        """
        We are at step 6.
        Log in as test_user_1 and check that the filtering repository only has a review for the data types component.
        """
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        strings_displayed = [ 'Data types', 'not_applicable' ]
        strings_not_displayed = [ 'Functional tests', 'README', 'Repository dependencies', 'Tool dependencies', 'Tools', 'Workflows' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed )

    def test_0030_review_initial_revision_functional_tests( self ):
        '''Review the functional tests component for the current tip revision.'''
        """
        We are at step 7.
        Log in as test_user_2 and review the functional tests component for this repository. Since the repository
        has not been altered, this will update the existing review to add a component.
        # Review this revision:
        #    Data types (N/A)
        #    Functional tests (One star, comment 'functional tests missing')
        """
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        # The create_repository_review method takes a dict( component label=review contents ).
        # If review_contents is empty, it marks that component as not applicable. The review
        # contents dict should have the structure:
        # {
        #   rating: 1-5,
        #   comment: <text>
        #   approved: yes/no
        #   private: yes/no
        # }
        review_contents_dict = { 'Functional tests': dict( rating=1, comment='Functional tests missing', approved='no', private='yes' ) }
        self.review_repository( repository, review_contents_dict, user )

#    def test_0030_verify_review_display( self ):
#        '''Verify that private reviews are restricted to owner and reviewer, and non-private views are viewable by others.'''
#        # Currently not implemented because third parties cannot view reviews whether they are private or not.
#        self.login( email=common.test_user_3_email, username=common.test_user_3_name )

    def test_0035_verify_functional_test_review( self ):
        '''Verify that the functional tests component review displays correctly.'''
        """
        We are at step 8.
        Log in as test_user_1 and check that the filtering repository now has reviews
        for the data types and functional tests components. Since the functional tests component was not marked as 'Not applicable',
        also check for the review comment.
        """
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        strings_displayed = [ 'Functional tests', 'Functional tests missing', 'no' ]
        strings_not_displayed = [ 'README', 'Repository dependencies', 'Tool dependencies', 'Tools', 'Workflows' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed )

    def test_0040_review_readme( self ):
        '''Review the readme component for the current tip revision.'''
        """
        We are at step 9.
        Log in as test_user_2 and update the review with the readme component marked as 'Not applicable'.
        # Review this revision:
        #    Data types (N/A)
        #    Functional tests (One star, comment 'functional tests missing')
        #    README (N/A)
        """
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        # The create_repository_review method takes a dict( component label=review contents ).
        # If review_contents is empty, it marks that component as not applicable. The review
        # contents dict should have the structure:
        # {
        #   rating: 1-5,
        #   comment: <text>
        #   approved: yes/no
        #   private: yes/no
        # }
        review_contents_dict = { 'README': dict() }
        self.review_repository( repository, review_contents_dict, user )

    def test_0045_verify_readme_review( self ):
        '''Verify that the readme component review displays correctly.'''
        """
        We are at step 10.
        Log in as test_user_1 and verify that the repository component reviews now include a review for the readme component.
        """
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        strings_displayed = [ 'README', 'not_applicable' ]
        strings_not_displayed = [ 'Repository dependencies', 'Tool dependencies', 'Tools', 'Workflows' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed )

    def test_0050_review_repository_dependencies( self ):
        '''Review the repository dependencies component for the current tip revision.'''
        """
        We are at step 11.
        Log in as test_user_2 and update the review with the repository dependencies component marked as 'Not applicable'.
        # Review this revision:
        #    Data types (N/A)
        #    Functional tests (One star, comment 'functional tests missing')
        #    README (N/A)
        #    Repository dependencies (N/A)
        """
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        # The create_repository_review method takes a dict( component label=review contents ).
        # If review_contents is empty, it marks that component as not applicable. The review
        # contents dict should have the structure:
        # {
        #   rating: 1-5,
        #   comment: <text>
        #   approved: yes/no
        #   private: yes/no
        # }
        review_contents_dict = { 'Repository dependencies': dict() }
        self.review_repository( repository, review_contents_dict, user )

    def test_0055_verify_repository_dependency_review( self ):
        '''Verify that the repository dependencies component review displays correctly.'''
        """
        We are at step 12.
        Log in as test_user_1 and verify that the repository component reviews now include a review
        for the repository dependencies component.
        """
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        strings_displayed = [ 'Repository dependencies', 'not_applicable' ]
        strings_not_displayed = [ 'Tool dependencies', 'Tools', 'Workflows' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed )

    def test_0060_review_tool_dependencies( self ):
        '''Review the tool dependencies component for the current tip revision.'''
        """
        We are at step 13.
        Log in as test_user_2 and update the review with the tool dependencies component marked as 'Not applicable'.
        # Review this revision:
        #    Data types (N/A)
        #    Functional tests (One star, comment 'functional tests missing')
        #    README (N/A)
        #    Repository dependencies (N/A)
        #    Tool dependencies (N/A)
        """
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        # The create_repository_review method takes a dict( component label=review contents ).
        # If review_contents is empty, it marks that component as not applicable. The review
        # contents dict should have the structure:
        # {
        #   rating: 1-5,
        #   comment: <text>
        #   approved: yes/no
        #   private: yes/no
        # }
        review_contents_dict = { 'Tool dependencies': dict() }
        self.review_repository( repository, review_contents_dict, user )

    def test_0065_verify_tool_dependency_review( self ):
        '''Verify that the tool dependencies component review displays correctly.'''
        """
        We are at step 14.
        Log in as test_user_1 and verify that the repository component reviews now include a review
        for the tool dependencies component.
        """
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        strings_displayed = [ 'Tool dependencies', 'not_applicable' ]
        strings_not_displayed = [ 'Tools', 'Workflows' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed )

    def test_0070_review_tools( self ):
        '''Review the tools component for the current tip revision.'''
        """
        We are at step 15.
        Log in as test_user_2 and update the review with the tools component given
        a favorable review, with 5 stars, and approved status.
        # Review this revision:
        #    Data types (N/A)
        #    Functional tests (One star, comment 'functional tests missing')
        #    README (N/A)
        #    Repository dependencies (N/A)
        #    Tool dependencies (N/A)
        #    Tools (5 stars, good review)
        """
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        # The create_repository_review method takes a dict( component label=review contents ).
        # If review_contents is empty, it marks that component as not applicable. The review
        # contents dict should have the structure:
        # {
        #   rating: 1-5,
        #   comment: <text>
        #   approved: yes/no
        #   private: yes/no
        # }
        review_contents_dict = { 'Tools': dict( rating=5, comment='Excellent tool, easy to use.', approved='yes', private='no' ) }
        self.review_repository( repository, review_contents_dict, user )

    def test_0075_verify_tools_review( self ):
        '''Verify that the tools component review displays correctly.'''
        """
        We are at step 16.
        Log in as test_user_1 and verify that the repository component reviews now include a review
        for the tools component. As before, check for the presence of the comment on this review.
        """
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        strings_displayed = [ 'Tools', 'yes', 'Excellent tool, easy to use.' ]
        strings_not_displayed = [ 'Workflows' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed )

    def test_0080_review_workflows( self ):
        '''Review the workflows component for the current tip revision.'''
        """
        We are at step 17.
        Log in as test_user_2 and update the review with the workflows component marked as 'Not applicable'.
        # Review this revision:
        #    Data types (N/A)
        #    Functional tests (One star, comment 'functional tests missing')
        #    README (N/A)
        #    Repository dependencies (N/A)
        #    Tool dependencies (N/A)
        #    Tools (5 stars, good review)
        #    Workflows (N/A)
        """
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        # The create_repository_review method takes a dict( component label=review contents ).
        # If review_contents is empty, it marks that component as not applicable. The review
        # contents dict should have the structure:
        # {
        #   rating: 1-5,
        #   comment: <text>
        #   approved: yes/no
        #   private: yes/no
        # }
        review_contents_dict = { 'Workflows': dict() }
        self.review_repository( repository, review_contents_dict, user )

    def test_0085_verify_workflows_review( self ):
        '''Verify that the workflows component review displays correctly.'''
        """
        We are at step 18.
        Log in as test_user_1 and verify that the repository component reviews now include a review
        for the workflows component.
        """
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        strings_displayed = [ 'Workflows', 'not_applicable' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed )

    def test_0090_upload_readme_file( self ):
        '''Upload a readme file to the filtering repository.'''
        """
        We are at step 19.
        Log in as test_user_1, the repository owner, and upload readme.txt to the repository. This will create
        a new changeset revision for this repository, which will need to be reviewed.
        """
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository,
                          filename='readme.txt',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded readme.txt.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0095_review_new_changeset_readme_component( self ):
        '''Update the filtering repository's readme component review to reflect the presence of the readme file.'''
        """
        We are at step 20.
        There is now a new changeset revision in the repository's changelog, but it has no review associated with it.
        Get the previously reviewed changeset hash, and pass that and the review id to the create_repository_review
        method, in order to copy the previous review's contents. Then update the new review to reflect the presence of
        a readme file.
        """
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        # Get the last changeset revision that has a review associated with it.
        last_review = self.get_last_reviewed_revision_by_user( user, repository )
        if last_review is None:
            raise AssertionError( 'Previous review expected, none found.' )
        # The create_repository_review method takes a dict( component label=review contents ).
        # If review_contents is empty, it marks that component as not applicable. The review
        # contents dict should have the structure:
        # {
        #   rating: 1-5,
        #   comment: <text>
        #   approved: yes/no
        #   private: yes/no
        # }
        review_contents_dict = { 'README': dict( rating=5, comment='Clear and concise readme file, a true pleasure to read.', approved='yes', private='no' ) }
        self.create_repository_review( repository,
                                       review_contents_dict,
                                       changeset_revision=self.get_repository_tip( repository ),
                                       copy_from=( str( last_review.changeset_revision ), last_review.id ) )

    def test_0100_verify_readme_review( self ):
        '''Verify that the readme component review displays correctly.'''
        """
        We are at step 21.
        Log in as the repository owner (test_user_1) and check the repository component reviews to
        verify that the readme component is now reviewed and approved.
        """
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        strings_displayed = [ 'README', 'yes', 'Clear and concise readme file, a true pleasure to read.' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed )

    def test_0105_upload_test_data( self ):
        '''Upload the missing test data to the filtering repository.'''
        """
        We are at step 22.
        Remain logged in as test_user_1 and upload test data to the repository. This will also create a
        new changeset revision that needs to be reviewed. This will replace the changeset hash associated with
        the last dowloadable revision, but the last repository review will still be associated with the
        last dowloadable revision hash.
        """
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository,
                          filename='filtering/filtering_test_data.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded filtering test data.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0110_review_new_changeset_functional_tests( self ):
        '''Update the filtering repository's readme component review to reflect the presence of the readme file.'''
        """
        We are at step 23.
        Log in as test_user_2 and get the last reviewed changeset hash, and pass that and the review id to
        the create_repository_review method, then update the copied review to approve the functional tests
        component.
        """
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        # Get the changeset immediately prior to the tip, and pass it to the create review method.
        last_review = self.get_last_reviewed_revision_by_user( user, repository )
        # The create_repository_review method takes a dict( component label=review contents ).
        # If review_contents is empty, it marks that component as not applicable. The review
        # contents dict should have the structure:
        # {
        #   rating: 1-5,
        #   comment: <text>
        #   approved: yes/no
        #   private: yes/no
        # }
        review_contents_dict = { 'Functional tests': dict( rating=5, comment='A good set of functional tests.', approved='yes', private='no' ) }
        self.create_repository_review( repository,
                                       review_contents_dict,
                                       changeset_revision=self.get_repository_tip( repository ),
                                       copy_from=( str( last_review.changeset_revision ), last_review.id ) )

    def test_0115_verify_functional_tests_review( self ):
        '''Verify that the functional tests component review displays correctly.'''
        """
        We are at step 24.
        Log in as the repository owner, test_user_1, and verify that the new revision's functional tests component
        review has been updated with an approved status and favorable comment.
        """
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        strings_displayed = [ 'Functional tests', 'yes', 'A good set of functional tests.' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed )

    def test_0120_upload_new_tool_version( self ):
        '''Upload filtering 2.2.0 to the filtering repository.'''
        """
        We are at step 25.
        Log in as test_user_1 and upload a new version of the tool to the filtering repository. This will create
        a new downloadable revision, with no associated repository component reviews.
        """
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository,
                          filename='filtering/filtering_2.2.0.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded filtering 2.2.0 tarball.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0125_review_new_changeset_functional_tests( self ):
        '''Update the filtering repository's review to apply to the new changeset with filtering 2.2.0.'''
        """
        We are at step 26.
        Log in as test_user_2 and copy the last review for this repository to the new changeset. Then
        update the tools component review to refer to the new tool version.
        """
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        last_review = self.get_last_reviewed_revision_by_user( user, repository )
        # Something needs to change so that the review will save.
        # The create_repository_review method takes a dict( component label=review contents ).
        # If review_contents is empty, it marks that component as not applicable. The review
        # contents dict should have the structure:
        # {
        #   rating: 1-5,
        #   comment: <text>
        #   approved: yes/no
        #   private: yes/no
        # }
        review_contents_dict = { 'Tools': dict( rating=5, comment='Version 2.2.0 does the impossible and improves this tool.', approved='yes', private='yes' ) }
        self.create_repository_review( repository,
                                       review_contents_dict,
                                       changeset_revision=self.get_repository_tip( repository ),
                                       copy_from=( str( last_review.changeset_revision ), last_review.id ) )

    def test_0135_verify_review_for_new_version( self ):
        '''Verify that the reviews display correctly for this changeset revision.'''
        """
        We are at step 27.
        Log in as test_user_1 and check that the tools component review is for filtering 2.2.0, but that the other component
        reviews had their contents copied from the last reviewed changeset.
        """
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = self.test_db_util.get_user( common.test_user_2_email )
        strings_displayed = [ 'Data types', 'Functional tests', 'yes', 'A good set of functional tests.', 'README', 'yes', 'Workflows', 'Tools' ]
        strings_displayed.extend( [ 'Clear and concise readme file, a true pleasure to read.', 'Tool dependencies', 'not_applicable' ] )
        strings_displayed.extend( [ 'Repository dependencies', 'Version 2.2.0 does the impossible and improves this tool.'  ] )
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed )
