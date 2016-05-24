from shed_functional.base.twilltestcase import common, ShedTwillTestCase

repository_name = 'bed_to_gff_0130'
repository_description = "Converter: BED to GFF"
repository_long_description = "Convert bed to gff"

category_name = 'Test 0130 Datatype Converters'
category_description = 'Test 0130 Datatype Converters'

'''
1) Install the bed_to_gff_converter repository.
2) Make sure the page section to select a tool panel section is NOT displayed since the tool will not be displayed in the Galaxy tool panel.
3) Make sure the bed_to_gff_converter tool is not displayed in the tool panel.
'''


class TestDatatypeConverters( ShedTwillTestCase ):
    '''Test features related to datatype converters.'''

    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        galaxy_admin_user = self.test_db_util.get_galaxy_user( common.admin_email )
        assert galaxy_admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        self.test_db_util.get_galaxy_private_role( galaxy_admin_user )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        self.test_db_util.get_private_role( test_user_1 )
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        self.test_db_util.get_private_role( admin_user )

    def test_0005_create_bed_to_gff_repository( self ):
        '''Create and populate bed_to_gff_0130.'''
        category = self.create_category( name=category_name, description=category_description )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        # Create a repository named bed_to_gff_0130 owned by user1.
        repository = self.get_or_create_repository( name=repository_name,
                                                    description=repository_description,
                                                    long_description=repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            # Upload bed_to_gff_converter.tar to the repository, if the repository is new.
            self.upload_file( repository,
                              filename='bed_to_gff_converter/bed_to_gff_converter.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded bed_to_gff_converter.tar.',
                              strings_displayed=[],
                              strings_not_displayed=[] )

    def test_0010_install_datatype_converter_to_galaxy( self ):
        '''Install bed_to_gff_converter_0130 into the running Galaxy instance.'''
        '''
        We are at step 1 - Install the bed_to_gff_converter repository.
        Install bed_to_gff_converter_0130, checking that the option to select the tool panel section is *not* displayed.
        '''
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        preview_strings_displayed = [ repository.name, self.get_repository_tip( repository ) ]
        strings_displayed = [ 'Choose the configuration file' ]
        strings_not_displayed = [ 'tool panel section' ]
        self.install_repository( repository_name,
                                 common.test_user_1_name,
                                 category_name,
                                 install_tool_dependencies=False,
                                 preview_strings_displayed=preview_strings_displayed,
                                 strings_displayed=strings_displayed,
                                 strings_not_displayed=strings_not_displayed,
                                 post_submit_strings_displayed=[ repository.name, 'New' ],
                                 includes_tools_for_display_in_tool_panel=False )

    def test_0015_uninstall_and_verify_tool_panel_section( self ):
        '''Uninstall bed_to_gff_converter_0130 and verify that the saved tool_panel_section is None.'''
        '''
        We are at step 3 - Make sure the bed_to_gff_converter tool is not displayed in the tool panel.
        The previous tool panel section for a tool is only recorded in the metadata when a repository is uninstalled,
        so we have to uninstall it first, then verify that it was not assigned a tool panel section.
        '''
        repository = self.test_db_util.get_installed_repository_by_name_owner( repository_name, common.test_user_1_name )
        self.uninstall_repository( repository )
        self.verify_installed_repository_no_tool_panel_section( repository )
