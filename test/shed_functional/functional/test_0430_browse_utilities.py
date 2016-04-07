import logging

from shed_functional.base.twilltestcase import common, ShedTwillTestCase

log = logging.getLogger( __name__ )

datatypes_repository_name = 'emboss_datatypes_0430'
datatypes_repository_description = 'Galaxy applicable datatypes for EMBOSS for test 0430'
datatypes_repository_long_description = 'Long description of Galaxy applicable datatypes for EMBOSS for test 0430'

emboss_repository_name = 'emboss_0430'
emboss_repository_description = 'EMBOSS tools for test 0430'
emboss_repository_long_description = 'Long description of EMBOSS tools for test 0430'

freebayes_repository_name = 'freebayes_0430'
freebayes_repository_description = 'Freebayes tool for test 0430'
freebayes_repository_long_description = 'Long description of Freebayes tool for test 0430'
'''
1. Create and populate repositories.
2. Browse Custom Datatypes.
3. Browse Tools.
4. Browse Repository Dependencies.
5. Browse Tool Dependencies.
'''


class TestToolShedBrowseUtilities( ShedTwillTestCase ):
    '''Test browsing for Galaxy utilities.'''

    def test_0000_initiate_users( self ):
        """Create necessary user accounts and login as an admin user."""
        """
        Create all the user accounts that are needed for this test script to run independently of other tests.
        Previously created accounts will not be re-created.
        """
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        self.test_db_util.get_private_role( test_user_1 )
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        self.test_db_util.get_private_role( admin_user )

    def test_0005_create_datatypes_repository( self ):
        """Create and populate the emboss_datatypes_0430 repository"""
        """
        We are at step 1.
        Create and populate the repository that will contain one or more datatypes.
        """
        category = self.create_category( name='Test 0430 Galaxy Utilities',
                                         description='Description of Test 0430 Galaxy Utilities category' )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        strings_displayed = self.expect_repo_created_strings(datatypes_repository_name)
        repository = self.get_or_create_repository( name=datatypes_repository_name,
                                                    description=datatypes_repository_description,
                                                    long_description=datatypes_repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=strings_displayed )
        self.upload_file( repository,
                          filename='emboss/datatypes/datatypes_conf.xml',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded datatypes_conf.xml.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0010_create_emboss_repository( self ):
        """Create and populate the emboss_0430 repository"""
        """
        We are at step 1.
        Create the emboss_0430 repository, and populate it with tools.
        """
        category = self.create_category( name='Test 0430 Galaxy Utilities',
                                         description='Description of Test 0430 Galaxy Utilities category' )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        strings_displayed = self.expect_repo_created_strings(emboss_repository_name)
        emboss_repository = self.get_or_create_repository( name=emboss_repository_name,
                                                    description=emboss_repository_description,
                                                    long_description=emboss_repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=strings_displayed )
        self.upload_file( emboss_repository,
                          filename='emboss/emboss.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded emboss.tar.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0015_create_dependency_on_datatypes_repository( self ):
        '''Create a dependency definition file that specifies emboss_datatypes_0430 and upload it to emboss_0430.'''
        emboss_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        datatypes_repository = self.test_db_util.get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        dependency_xml_path = self.generate_temp_path( 'test_0430', additional_paths=[ 'dependencies' ] )
        datatypes_tuple = ( self.url, datatypes_repository.name, datatypes_repository.user.username, self.get_repository_tip( datatypes_repository ) )
        self.create_repository_dependency( repository=emboss_repository, repository_tuples=[ datatypes_tuple ], filepath=dependency_xml_path )
        self.check_repository_dependency( emboss_repository, datatypes_repository )

    def test_0020_create_tool_dependency_repository( self ):
        """Create and populate the freebayes_0430 repository"""
        """
        We are at step 1.
        Create and populate the repository that will have a tool dependency defined.
        """
        category = self.create_category( name='Test 0430 Galaxy Utilities',
                                         description='Description of Test 0430 Galaxy Utilities category' )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        strings_displayed = self.expect_repo_created_strings(freebayes_repository_name)
        repository = self.get_or_create_repository( name=freebayes_repository_name,
                                                    description=freebayes_repository_description,
                                                    long_description=freebayes_repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=strings_displayed )
        self.upload_file( repository,
                          filename='freebayes/freebayes.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded freebayes.tar.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0025_browse_custom_datatypes( self ):
        '''Load the page to browse custom datatypes.'''
        '''
        We are at step 2.
        Verify that the uploaded emboss datatypes repository has added to the custom datatypes page.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        changeset_revision = self.get_repository_tip( repository )
        strings_displayed = [ 'equicktandem', 'est2genome', 'supermatcher', 'galaxy.datatypes.data:Text', changeset_revision, 'user1', 'emboss_datatypes_0430' ]
        self.browse_custom_datatypes( strings_displayed=strings_displayed )

    def test_0030_browse_tools( self ):
        '''Load the page to browse tools.'''
        '''
        We are at step 3.
        Verify the existence of emboss tools in the browse tools page.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        changeset_revision = self.get_repository_tip( repository )
        strings_displayed = [ 'EMBOSS', 'antigenic1', '5.0.0', changeset_revision, 'user1', 'emboss_0430' ]
        self.browse_tools( strings_displayed=strings_displayed )

    def test_0035_browse_repository_dependencies( self ):
        '''Browse repository dependencies and look for a dependency on emboss_datatypes_0430.'''
        '''
        We are at step 3.
        Verify that the browse repository dependencies page shows emboss_datatypes_0430 as a dependency of emboss_0430.
        '''
        emboss_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        datatypes_repository = self.test_db_util.get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        datatypes_changeset_revision = self.get_repository_tip( datatypes_repository )
        emboss_changeset_revision = self.get_repository_tip( emboss_repository )
        strings_displayed = [ datatypes_changeset_revision, emboss_changeset_revision, 'emboss_datatypes_0430', 'user1', 'emboss_0430' ]
        self.browse_repository_dependencies( strings_displayed=strings_displayed )

    def test_0040_browse_tool_dependencies( self ):
        '''Browse tool dependencies and look for the right versions of freebayes and samtools.'''
        '''
        We are at step 4.
        Verify that the browse tool dependencies page shows the correct dependencies defined for freebayes_0430.
        '''
        freebayes_repository = self.test_db_util.get_repository_by_name_and_owner( freebayes_repository_name, common.test_user_1_name )
        freebayes_changeset_revision = self.get_repository_tip( freebayes_repository )
        strings_displayed = [ freebayes_changeset_revision, 'freebayes_0430', 'user1', '0.9.4_9696d0ce8a96', 'freebayes', 'samtools', '0.1.18' ]
        self.browse_tool_dependencies( strings_displayed=strings_displayed )
