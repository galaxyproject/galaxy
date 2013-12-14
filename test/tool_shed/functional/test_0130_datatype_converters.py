from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
repository_name = 'bed_to_gff_0130'
repository_description = "Converter: BED to GFF"
repository_long_description = "Convert bed to gff"

category_name = 'Test 0130 Datatype Converters'
category_description = 'Test 0130 Datatype Converters'

'''
1) Create a populate the bed_to_gff_converter repository
2) Visit the manage repository page and make sure there is the appropriate valid too and datatype
3) Visit the view tool metadata page and make sure that "Display in tool panel" is False
'''

class TestDatatypeConverters( ShedTwillTestCase ):
    '''Test features related to datatype converters.'''
    
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
        
    def test_0005_create_bed_to_gff_repository( self ):
        '''Create and populate bed_to_gff_0130.'''
        '''
        We are at step 1 - Create and populate the bed_to_gff_0130 repository.
        Create the bed_to_gff_0130 repository and populate it with the files needed for this test.
        '''
        category = self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        # Create a repository named bed_to_gff_0130 owned by user1.
        repository = self.get_or_create_repository( name=repository_name, 
                                                    description=repository_description, 
                                                    long_description=repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        # Upload bed_to_gff_converter.tar to the repository.
        self.upload_file( repository, 
                          filename='bed_to_gff_converter/bed_to_gff_converter.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False, 
                          commit_message='Uploaded bed_to_gff_converter.tar.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        
    def test_0010_verify_tool_and_datatype( self ):
        '''Verify that a valid tool and datatype are contained within the repository.'''
        '''
        We are at step 2 - Visit the manage repository page and make sure there is the appropriate valid tool and datatype.
        There should be a 'Convert BED to GFF' tool and a 'galaxy.datatypes.interval:Bed' datatype with extension 'bed'
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        strings_displayed = [ 'Convert BED to GFF', 'galaxy.datatypes.interval:Bed', 'bed', 'Valid tools', 'Datatypes' ]
        strings_not_displayed = [ 'Invalid tools' ]
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed )
    
    def test_0015_verify_tool_panel_display( self ):
        '''Verify that the tool is configured not to be displayed in the tool panel.'''
        '''
        We are at step 3
        Datatype converters that are associated with a datatype should have display in tool panel = False in the tool metadata.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        metadata = self.get_repository_metadata_by_changeset_revision( repository, self.get_repository_tip( repository ) )
        tool_metadata_strings_displayed = '<label>Display in tool panel:</label>\n                    False'
        self.check_repository_tools_for_changeset_revision( repository, 
                                                            self.get_repository_tip( repository ), 
                                                            tool_metadata_strings_displayed=tool_metadata_strings_displayed )
