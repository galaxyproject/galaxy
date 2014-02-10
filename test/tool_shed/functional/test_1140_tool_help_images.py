from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os


import logging
log = logging.getLogger(__name__)

repository_name = 'htseq_count_0140'
repository_description = "Converter: BED to GFF"
repository_long_description = "Convert bed to gff"

category_name = 'Test 0140 Tool Help Images'
category_description = 'Test 0140 Tool Help Images'

'''
1) Create and populate the htseq_count_0140 repository.
2) Visit the manage_repository page, then the tool page, and look for the image string 
similar to the following string where the encoded repository_id is previously determined:

src="/repository/static/images/<id>/count_modes.png"

Galaxy side:
1) Install the htseq_count repository from the tool shed into Galaxy.
2) In the center tool panel, look for the image string similar to the following string where the encoded_repository_id is previously determined as the installed ToolShedRepository id:

src="/tool_runner/static/images/<id>/count_modes.png"
'''

class TestToolHelpImages( ShedTwillTestCase ):
    '''Test features related to tool help images.'''
    
    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % test_user_1_email
        test_user_1_private_role = self.test_db_util.get_private_role( test_user_1 )
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = self.test_db_util.get_private_role( admin_user )
        
    def test_0005_create_htseq_count_repository( self ):
        '''Create and populate htseq_count_0140.'''
        '''
        We are at step 1 - Create and populate the htseq_count_0140 repository.
        Create the htseq_count_0140 repository and upload the tarball.
        '''
        category = self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        # Create a repository named htseq_count_0140 owned by user1.
        repository = self.get_or_create_repository( name=repository_name, 
                                                    description=repository_description, 
                                                    long_description=repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            # Upload htseq_count.tar to the repository if it hasn't already been populated.
            self.upload_file( repository, 
                              filename='htseq_count/htseq_count.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False, 
                              commit_message='Uploaded htseq_count.tar.',
                              strings_displayed=[], 
                              strings_not_displayed=[] )
    
    def test_0010_load_tool_page( self ):
        '''Load the tool page and check for the image URL.'''
        '''
        This is a duplicate of test method _0010 in test_0140_tool_help_images.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        # Get the repository tip.
        changeset_revision = self.get_repository_tip( repository )
        self.display_manage_repository_page( repository )
        # Generate the image path.
        image_path = 'src="/repository/static/images/%s/count_modes.png"' % self.security.encode_id( repository.id )
        # The repository uploaded in this test should only have one metadata revision, with one tool defined, which
        # should be the tool that contains a link to the image.
        repository_metadata = repository.metadata_revisions[ 0 ].metadata
        tool_path = repository_metadata[ 'tools' ][ 0 ][ 'tool_config' ]
        self.load_display_tool_page( repository, tool_path, changeset_revision, strings_displayed=[ image_path ], strings_not_displayed=[] )

    def test_0015_install_htseq_count_repository( self ):
        '''Install the htseq_count_0140 repository into Galaxy.'''
        '''
        We are at step 1 - Install the htseq_count_0140 repository from the tool shed into Galaxy.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        self.install_repository( 'htseq_count_0140', 
                                 'user1', 
                                 category_name,
                                 strings_displayed=[],
                                 install_tool_dependencies=False, 
                                 install_repository_dependencies=False )

    def test_0020_verify_tool_image_link( self ):
        '''Load the tool page and verify the image link.'''
        '''
        We are at step 2
        
        In the center tool panel, look for the image string similar to the following string where the
        encoded_repository_id is previously determined as the installed ToolShedRepository id:

        src="admin_toolshed/static/images/<id>/count_modes.png"
        '''
        repository = self.test_db_util.get_installed_repository_by_name_owner( repository_name, common.test_user_1_name )
        image_path = 'src="admin_toolshed/static/images/%s/count_modes.png"' % self.security.encode_id( repository.id )
        # The repository uploaded in this test should only define one tool, which should be the tool that contains a link to an image.
        repository_metadata = repository.metadata
        tool_id = repository_metadata[ 'tools' ][ 0 ][ 'guid' ]
        self.load_page_for_installed_tool( tool_id, strings_displayed=[ image_path ] )
