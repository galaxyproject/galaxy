import logging
import os

from shed_functional.base.twilltestcase import common, ShedTwillTestCase

log = logging.getLogger( __name__ )

repository_name = 'filtering_0490'
repository_description = "Galaxy's filtering tool for test 0490"
repository_long_description = "Long description of Galaxy's filtering tool for test 0490"

category_name = 'Test 0490 Repository Import Export'
category_description = 'Test script 0490 for importing and exporting single repositories.'

'''
First test:

1. Import a repository capsule containing a repository with no dependencies, e.g. filter1.
2. Check that the repository to be imported is not marked as preexisting. The word ' Exists' should not be displayed, but '<b>Exists</b>' will.
3. Export that repository. Check the capsule's contents, verify that changeset revision and tool shed are not set.
4. Import the capsule again. Check that the repository to be imported is marked as preexisting. The word ' Exists' should be
   displayed, as will '<b>Exists</b>'.

'''

capsule_filepath = ''


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
        """Import the filter_0490 repository capsule."""
        '''
        This is step 1 - Import a repository capsule containing a repository with no dependencies, e.g. filter1.
        Check that the repository to be imported is not marked as preexisting. The string ' Exists' should not
        be displayed, but '<b>Exists</b>' should.
        '''
        self.login( email=common.admin_email, username=common.admin_username )
        self.create_category( name=category_name, description=category_description )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        self.import_capsule( self.get_filename( 'repository_capsules/0490_filtering.tar.gz' ),
                             strings_displayed=[ repository_name, '<b>Exists' ],
                             strings_not_displayed=[ ' Exists' ],
                             strings_displayed_after_submit=[ 'Repository <b>filtering_0490</b> has been created.' ],
                             strings_not_displayed_after_submit=[ 'Import not necessary' ] )

    def test_0010_export_repository_capsule( self ):
        '''Export the repository that was imported in the previous step.'''
        '''
        This is step 2 - Export that repository.
        Export the repository to a temporary location.
        '''
        global capsule_filepath
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        capsule_filepath = self.export_capsule( repository, aggressive=True, includes_dependencies=False )
        assert os.path.exists( capsule_filepath ), 'Exported repository capsule file path %s not found.' % capsule_filepath

    def test_0015_verify_exported_capsule( self ):
        '''Verify the exported capsule contents.'''
        '''
        This is step 3 - Check the capsule's contents, verify that changeset revision and tool shed are not set.
        Extract the exported capsule tarball to a temporary path, and confirm that the manifest does not specify
        a tool shed or changeset revision.
        '''
        global capsule_filepath
        self.verify_capsule_contents( capsule_filepath, owner=common.test_user_1_name )

    def test_0020_import_repository_capsule( self ):
        '''Import the exported repository capsule.'''
        '''
        This is step 4 - Import the capsule again. Check that the repository to be imported is marked as preexisting.
        The string ' Exists' should be displayed, as should '<b>Exists</b>'.
        '''
        global capsule_filepath
        self.import_capsule( capsule_filepath,
                             strings_displayed=[ repository_name, ' Exists', self.url ],
                             strings_not_displayed_after_submit=[ 'Repository <b>filtering_0490</b> has been created.' ],
                             strings_displayed_after_submit=[ 'Import not necessary', 'Exists' ] )
