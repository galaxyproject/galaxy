from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
import tool_shed.base.test_db_util as test_db_util

freebayes_repository_name = 'freebayes_0040'
freebayes_repository_description = "Galaxy's freebayes tool"
freebayes_repository_long_description = "Long description of Galaxy's freebayes tool"

filtering_repository_name = 'filtering_0040'
filtering_repository_description = "Galaxy's filtering tool"
filtering_repository_long_description = "Long description of Galaxy's filtering tool"

class TestRepositoryCircularDependencies( ShedTwillTestCase ):
    '''Verify that the code correctly displays repositories with circular repository dependencies.'''
    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % test_user_1_email
        test_user_1_private_role = test_db_util.get_private_role( test_user_1 )
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = test_db_util.get_private_role( admin_user )
    def test_0005_create_category( self ):
        """Create a category for this test suite"""
        self.create_category( name='test_0040_repository_circular_dependencies', description='Testing handling of circular repository dependencies.' )
    def test_0010_create_freebayes_repository( self ):
        '''Create and populate freebayes_0040.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=freebayes_repository_name, 
                                                    description=freebayes_repository_description, 
                                                    long_description=freebayes_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    categories=[ 'test_0040_repository_circular_dependencies' ], 
                                                    strings_displayed=[] )
        self.upload_file( repository, 
                          'freebayes/freebayes.tar', 
                          strings_displayed=[], 
                          commit_message='Uploaded freebayes.tar.' )
    def test_0015_create_filtering_repository( self ):
        '''Create and populate filtering_0040.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=filtering_repository_name, 
                                                    description=filtering_repository_description, 
                                                    long_description=filtering_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    categories=[ 'test_0040_repository_circular_dependencies' ], 
                                                    strings_displayed=[] )
        self.upload_file( repository, 
                          'filtering/filtering_1.1.0.tar', 
                          strings_displayed=[], 
                          commit_message='Uploaded filtering.tar.' )
    def test_0020_create_dependency_on_freebayes( self ):
        '''Upload a repository_dependencies.xml file that specifies the current revision of freebayes to the filtering_0040 repository.'''
        # The dependency structure should look like:
        # Filtering revision 0 -> freebayes revision 0.
        # Freebayes revision 0 -> filtering revision 1.
        # Filtering will have two revisions, one with just the filtering tool, and one with the filtering tool and a dependency on freebayes.
        repository = test_db_util.get_repository_by_name_and_owner( freebayes_repository_name, common.test_user_1_name )
        filtering_repository = test_db_util.get_repository_by_name_and_owner( filtering_repository_name, common.test_user_1_name )
        repository_dependencies_path = self.generate_temp_path( 'test_0040', additional_paths=[ 'filtering' ] )
        self.generate_repository_dependency_xml( [ repository ], 
                                                 self.get_filename( 'repository_dependencies.xml', filepath=repository_dependencies_path ), 
                                                 dependency_description='Filtering 1.1.0 depends on the freebayes repository.' )
        self.upload_file( filtering_repository, 
                          'repository_dependencies.xml', 
                          filepath=repository_dependencies_path, 
                          commit_message='Uploaded dependency on freebayes' )
    def test_0025_create_dependency_on_filtering( self ):
        '''Upload a repository_dependencies.xml file that specifies the current revision of filtering to the freebayes_0040 repository.'''
        # The dependency structure should look like:
        # Filtering revision 0 -> freebayes revision 0.
        # Freebayes revision 0 -> filtering revision 1.
        # Filtering will have two revisions, one with just the filtering tool, and one with the filtering tool and a dependency on freebayes.
        repository = test_db_util.get_repository_by_name_and_owner( filtering_repository_name, common.test_user_1_name )
        freebayes_repository = test_db_util.get_repository_by_name_and_owner( freebayes_repository_name, common.test_user_1_name )
        repository_dependencies_path = self.generate_temp_path( 'test_0040', additional_paths=[ 'freebayes' ] )
        self.generate_repository_dependency_xml( [ repository ], 
                                                 self.get_filename( 'repository_dependencies.xml', filepath=repository_dependencies_path ), 
                                                 dependency_description='Freebayes depends on the filtering repository.' )
        self.upload_file( freebayes_repository, 
                          'repository_dependencies.xml', 
                          filepath=repository_dependencies_path, 
                          commit_message='Uploaded dependency on filtering' )
    def test_0030_verify_repository_dependencies( self ):
        '''Verify that each repository can depend on the other without causing an infinite loop.'''
        filtering_repository = test_db_util.get_repository_by_name_and_owner( filtering_repository_name, common.test_user_1_name )
        freebayes_repository = test_db_util.get_repository_by_name_and_owner( freebayes_repository_name, common.test_user_1_name )
        # The dependency structure should look like:
        # Filtering revision 0 -> freebayes revision 0.
        # Freebayes revision 0 -> filtering revision 1.
        # Filtering will have two revisions, one with just the filtering tool, and one with the filtering tool and a dependency on freebayes.
        # In this case, the displayed dependency will specify the tip revision, but this will not always be the case.
        self.check_repository_dependency( filtering_repository, freebayes_repository, self.get_repository_tip( freebayes_repository ) )
        self.check_repository_dependency( freebayes_repository, filtering_repository, self.get_repository_tip( filtering_repository ) )
    def test_0035_verify_repository_metadata( self ):
        '''Verify that resetting the metadata does not change it.'''
        freebayes_repository = test_db_util.get_repository_by_name_and_owner( freebayes_repository_name, common.test_user_1_name )
        filtering_repository = test_db_util.get_repository_by_name_and_owner( filtering_repository_name, common.test_user_1_name )
        for repository in [ freebayes_repository, filtering_repository ]:
            self.verify_unchanged_repository_metadata( repository )
    def test_0040_verify_tool_dependencies( self ):
        '''Verify that freebayes displays tool dependencies.'''
        repository = test_db_util.get_repository_by_name_and_owner( freebayes_repository_name, common.test_user_1_name )
        self.display_manage_repository_page( repository, 
                                             strings_displayed=[ 'freebayes', '0.9.4_9696d0ce8a9', 'samtools', '0.1.18', 'Valid tools' ],
                                             strings_not_displayed=[ 'Invalid tools' ] )
