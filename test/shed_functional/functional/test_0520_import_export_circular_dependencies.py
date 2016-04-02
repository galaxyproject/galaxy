import logging

from shed_functional.base.twilltestcase import common, ShedTwillTestCase

log = logging.getLogger( __name__ )

filtering_repository_name = 'filtering_0520'
filtering_repository_description = "Galaxy's filtering tool for test 0520"
filtering_repository_long_description = "Long description of Galaxy's filtering tool for test 0520"
freebayes_repository_name = 'freebayes_0520'
freebayes_repository_description = "Galaxy's freebayes tool"
freebayes_repository_long_description = "Long description of Galaxy's freebayes tool for test 0520"

category_name = 'Test 0520 Circular Dependency Import Export'
category_description = 'Test script 0520 for importing and exporting repositories with circular dependencies.'

'''
1) Upload a capsule with 2 repositories that define simple repository dependencies on each other, resulting in circular
   dependencies to a tool shed.
2) Make sure each repository contains an invalid repository dependency after the capsule has been uploaded (they should
   be invalid because their toolshed and changeset_revision attributes could not be auto-populated).
3) Make sure each repository's repository_metadata record has the downloadable column marked as False.
'''


class TestExportImportRepository( ShedTwillTestCase ):
    '''Test exporting and importing repositories.'''

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

    def test_0005_import_repository_capsule( self ):
        """Import the filter_0520 repository capsule with dependencies."""
        '''
        This is step 1 - Upload a capsule with 2 repositories that define simple repository dependencies on each other, resulting in
        circular dependencies to a tool shed.
        '''
        self.login( email=common.admin_email, username=common.admin_username )
        self.create_category( name=category_name, description=category_description )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        self.import_capsule( self.get_filename( 'repository_capsules/0520_filtering.tar.gz' ),
                             strings_displayed=[ filtering_repository_name, freebayes_repository_name, '<b>Exists' ],
                             strings_not_displayed=[ ' Exists' ],
                             strings_displayed_after_submit=[ 'Repository <b>filtering_0520</b> has been created.' ],
                             strings_not_displayed_after_submit=[ 'Import not necessary' ] )

    def test_0010_verify_invalid_dependency( self ):
        '''Verify that the repository dependencies are marked as invalid.'''
        '''
        This is step 2 - Make sure each repository contains an invalid repository dependency after the capsule has been uploaded
        (they should be invalid because their toolshed and changeset_revision attributes could not be auto-populated).
        '''
        freebayes_repository = self.test_db_util.get_repository_by_name_and_owner( freebayes_repository_name, common.test_user_1_name )
        filtering_repository = self.test_db_util.get_repository_by_name_and_owner( filtering_repository_name, common.test_user_1_name )
        strings_displayed = [ 'Ignoring repository dependency definition', self.url, 'filtering_0520', 'name is invalid' ]
        self.display_manage_repository_page( freebayes_repository,
                                             strings_displayed=strings_displayed,
                                             strings_not_displayed=[ 'Repository dependencies' ] )
        self.display_manage_repository_page( filtering_repository,
                                             strings_displayed=[ 'Repository dependencies', self.get_repository_tip( freebayes_repository ) ],
                                             strings_not_displayed=[] )

    def test_0015_verify_repository_metadata( self ):
        '''Verify that the repositories are not marked as downloadable.'''
        '''
        This is step 3 - Make sure each repository's repository_metadata record has the downloadable column marked as False.
        '''
        freebayes_repository = self.test_db_util.get_repository_by_name_and_owner( freebayes_repository_name, common.test_user_1_name )
        filtering_repository = self.test_db_util.get_repository_by_name_and_owner( filtering_repository_name, common.test_user_1_name )
        freebayes_metadata = self.get_repository_metadata_by_changeset_revision( freebayes_repository, self.get_repository_tip( freebayes_repository ) )
        filtering_metadata = self.get_repository_metadata_by_changeset_revision( filtering_repository, self.get_repository_tip( filtering_repository ) )
        assert not filtering_metadata.downloadable, 'Repository filtering_0520 is incorrectly marked as downloadable.'
        assert not freebayes_metadata.downloadable, 'Repository freebayes_0520 is incorrectly marked as downloadable.'
