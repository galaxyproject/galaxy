from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
import tool_shed.base.test_db_util as test_db_util

repository_name = 'filtering_0400'
repository_description = 'Galaxy filtering tool for test 0400'
repository_long_description = 'Long description of Galaxy filtering tool for test 0400'

class TestRepositoryComponentReviews( ShedTwillTestCase ):
    '''Test repository component review features.'''
    def test_0000_initiate_users( self ):
        """Create necessary user accounts and login as an admin user."""
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        test_user_1_private_role = test_db_util.get_private_role( test_user_1 )
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        test_user_2 = test_db_util.get_user( common.test_user_2_email )
        assert test_user_2 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_2_email
        test_user_2_private_role = test_db_util.get_private_role( test_user_2 )
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        admin_user_private_role = test_db_util.get_private_role( admin_user )
    def test_0005_grant_reviewer_role( self ):
        '''Grant the repository reviewer role to test_user_2.'''
        reviewer_role = test_db_util.get_role_by_name( 'Repository Reviewer' )
        test_user_2 = test_db_util.get_user( common.test_user_2_email )
        self.grant_role_to_user( test_user_2, reviewer_role )
    def test_0010_verify_repository_review_components( self ):
        '''Ensure that the required review components exist.'''
        strings_not_displayed=[ 'Repository dependencies' ]
        self.manage_review_components( strings_not_displayed=strings_not_displayed )
        self.add_repository_review_component( name='Repository dependencies', 
                                              description='Repository dependencies defined in a file named repository_dependencies.xml included in the repository' )
        strings_displayed=[ 'Data types', 'Functional tests', 'README', 'Repository dependencies', 'Tool dependencies', 'Tools', 'Workflows' ]
        self.manage_review_components( strings_displayed=strings_displayed )
    def test_0015_create_repository( self ):
        """Create and populate the filtering repository"""
        category = self.create_category( name='Test 0400 Repository Component Reviews', description='Test 0400 Repository Component Reviews' )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        strings_displayed = [ 'Repository %s' % "'%s'" % repository_name, 
                              'Repository %s has been created' % "'%s'" % repository_name ]
        repository = self.get_or_create_repository( name=repository_name, 
                                                    description=repository_description, 
                                                    long_description=repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=strings_displayed )
        self.upload_file( repository, 'filtering/filtering_1.1.0.tar', commit_message="Uploaded filtering 1.1.0" )
    def test_0020_review_initial_revision_data_types( self ):
        '''Review the datatypes component for the current tip revision.'''
        # Review this revision: 
        #    Data types (N/A)
        #    Functional tests (One star, comment 'functional tests missing')    
        #    README (N/A)
        #    Repository dependencies (N/A)
        #    Tool dependencies (N/A)
        #    Tools (5 stars, good review)
        #    Workflows (N/A)
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        review_contents_dict = { 'Data types': dict() }
        self.create_repository_review( repository, review_contents_dict )
    def test_0025_verify_datatype_review( self ):
        '''Verify that the datatypes component review displays correctly.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        strings_displayed = [ 'Data types', 'not_applicable' ]
        strings_not_displayed = [ 'Functional tests', 'README', 'Repository dependencies', 'Tool dependencies', 'Tools', 'Workflows' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed )
    def test_0030_review_initial_revision_functional_tests( self ):
        '''Review the datatypes component for the current tip revision.'''
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        review_contents_dict = { 'Functional tests': dict( rating=1, comment='Functional tests missing', approved='no', private='yes' ) }
        self.review_repository( repository, review_contents_dict, user )
#    def test_0030_verify_review_display( self ):
#        '''Verify that private reviews are restricted to owner and reviewer, and non-private views are viewable by others.'''
#        # Currently not implemented because third parties cannot view reviews whether they are private or not.
#        self.logout()
#        self.login( email=common.test_user_3_email, username=common.test_user_3_name )
    def test_0035_verify_functional_test_review( self ):
        '''Verify that the datatypes component review displays correctly.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        strings_displayed=[ 'Functional tests', 'Functional tests missing', 'no' ]
        strings_not_displayed = [ 'README', 'Repository dependencies', 'Tool dependencies', 'Tools', 'Workflows' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed )
    def test_0040_review_readme( self ):
        '''Review the readme component for the current tip revision.'''
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        review_contents_dict = { 'README': dict() }
        self.review_repository( repository, review_contents_dict, user )
    def test_0045_verify_readme_review( self ):
        '''Verify that the datatypes component review displays correctly.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        strings_displayed=[ 'README', 'not_applicable' ]
        strings_not_displayed = [ 'Repository dependencies', 'Tool dependencies', 'Tools', 'Workflows' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed )
    def test_0050_review_repository_dependencies( self ):
        '''Review the repository dependencies component for the current tip revision.'''
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        review_contents_dict = { 'Repository dependencies': dict() }
        self.review_repository( repository, review_contents_dict, user )
    def test_0055_verify_repository_dependency_review( self ):
        '''Verify that the datatypes component review displays correctly.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        strings_displayed=[ 'Repository dependencies', 'not_applicable' ]
        strings_not_displayed = [ 'Tool dependencies', 'Tools', 'Workflows' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed )
    def test_0060_review_tool_dependencies( self ):
        '''Review the tool dependencies component for the current tip revision.'''
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        review_contents_dict = { 'Tool dependencies': dict() }
        self.review_repository( repository, review_contents_dict, user )
    def test_0065_verify_tool_dependency_review( self ):
        '''Verify that the datatypes component review displays correctly.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        strings_displayed=[ 'Tool dependencies', 'not_applicable' ]
        strings_not_displayed = [ 'Tools', 'Workflows' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed )
    def test_0070_review_tools( self ):
        '''Review the tools component for the current tip revision.'''
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        review_contents_dict = { 'Tools': dict( rating=5, comment='Excellent tool, easy to use.', approved='yes', private='no' ) }
        self.review_repository( repository, review_contents_dict, test_db_util.get_user( common.test_user_2_email ) )
    def test_0075_verify_tools_review( self ):
        '''Verify that the datatypes component review displays correctly.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        strings_displayed=[ 'Tools', 'yes', 'Excellent tool, easy to use.' ]
        strings_not_displayed = [ 'Workflows' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed )
    def test_0080_review_workflows( self ):
        '''Review the workflows component for the current tip revision.'''
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        review_contents_dict = { 'Workflows': dict() }
        self.review_repository( repository, review_contents_dict, user )
    def test_0085_verify_workflows_review( self ):
        '''Verify that the datatypes component review displays correctly.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        strings_displayed=[ 'Workflows', 'not_applicable' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed )
    def test_0090_upload_readme_file( self ):
        '''Upload a readme file to the filtering repository.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        self.upload_file( repository, 'readme.txt', commit_message="Uploaded readme.txt" )
    def test_0095_review_new_changeset_readme_component( self ):
        '''Update the filtering repository's readme component review to reflect the presence of the readme file.'''
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        # Get the changeset immediately prior to the tip, and pass it to the create review method.
        changelog = self.get_repository_changelog( repository )
        changeset_revision, ctx_revision = changelog[-2]
        previous_review = test_db_util.get_repository_review_by_user_id_changeset_revision( user.id, repository.id, str( changeset_revision ) )
        review_contents_dict = { 'README': dict( rating=5, comment='Clear and concise readme file, a true pleasure to read.', approved='yes', private='no' ) }
        self.create_repository_review( repository, 
                                       review_contents_dict, 
                                       changeset_revision=self.get_repository_tip( repository ), 
                                       copy_from=( str( changeset_revision ), previous_review.id ) )
    def test_0100_verify_readme_review( self ):
        '''Verify that the readme component review displays correctly.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        strings_displayed = [ 'README', 'yes', 'Clear and concise readme file, a true pleasure to read.' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed )
    def test_0105_upload_test_data( self ):
        '''Upload the missing test data to the filtering repository.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        self.upload_file( repository, 'filtering/filtering_test_data.tar', commit_message="Uploaded test data." )
    def test_0110_review_new_changeset_functional_tests( self ):
        '''Update the filtering repository's readme component review to reflect the presence of the readme file.'''
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        # Get the changeset immediately prior to the tip, and pass it to the create review method.
        changelog = self.get_repository_changelog( repository )
        changeset_revision, ctx_revision = changelog[-2]
        previous_review = test_db_util.get_repository_review_by_user_id_changeset_revision( user.id, repository.id, str( changeset_revision ) )
        review_contents_dict = { 'Functional tests': dict( rating=5, comment='A good set of functional tests.', approved='yes', private='no' ) }
        self.create_repository_review( repository, 
                                       review_contents_dict, 
                                       changeset_revision=self.get_repository_tip( repository ), 
                                       copy_from=( str( changeset_revision ), previous_review.id ) )
    def test_0115_verify_functional_tests_review( self ):
        '''Verify that the functional tests component review displays correctly.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        strings_displayed=[ 'Functional tests', 'yes', 'A good set of functional tests.' ]
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed )
    def test_0120_upload_new_tool_version( self ):
        '''Upload filtering 2.2.0 to the filtering repository.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        self.upload_file( repository, 
                          'filtering/filtering_2.2.0.tar', 
                          commit_message="Uploaded filtering 2.2.0", 
                          remove_repo_files_not_in_tar='No' )
    def test_0125_review_new_changeset_functional_tests( self ):
        '''Update the filtering repository's review to apply to the new changeset with filtering 2.2.0.'''
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        # Get the changeset immediately prior to the tip, and pass it to the create review method.
        changelog = self.get_repository_changelog( repository )
        changeset_revision, ctx_revision = changelog[-2]
        previous_review = test_db_util.get_repository_review_by_user_id_changeset_revision( user.id, repository.id, str( changeset_revision ) )
        # Something needs to change so that the review will save.
        review_contents_dict = { 'Tools': dict( rating=5, comment='Version 2.2.0 does the impossible and improves this tool.', approved='yes', private='yes' ) }
        self.create_repository_review( repository, 
                                       review_contents_dict, 
                                       changeset_revision=self.get_repository_tip( repository ), 
                                       copy_from=( str( changeset_revision ), previous_review.id ) )
    def test_0135_verify_review_for_new_version( self ):
        '''Verify that the reviews display correctly for this changeset revision.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        user = test_db_util.get_user( common.test_user_2_email )
        strings_displayed = [ 'Data types', 'Functional tests', 'yes', 'A good set of functional tests.', 'README', 'yes', 'Workflows', 'Tools' ]
        strings_displayed.extend( [ 'Clear and concise readme file, a true pleasure to read.', 'Tool dependencies', 'not_applicable' ] )
        strings_displayed.extend( [ 'Repository dependencies', 'Version 2.2.0 does the impossible and improves this tool.'  ] )
        self.verify_repository_reviews( repository, reviewer=user, strings_displayed=strings_displayed )
