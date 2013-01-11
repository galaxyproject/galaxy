from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
import tool_shed.base.test_db_util as test_db_util

emboss_datatypes_repository_name = 'emboss_datatypes_0050'
emboss_datatypes_repository_description = "Datatypes for emboss"
emboss_datatypes_repository_long_description = "Long description of Emboss' datatypes"

emboss_repository_name = 'emboss_0050'
emboss_repository_description = "Galaxy's emboss tool"
emboss_repository_long_description = "Long description of Galaxy's emboss tool"

filtering_repository_name = 'filtering_0050'
filtering_repository_description = "Galaxy's filtering tool"
filtering_repository_long_description = "Long description of Galaxy's filtering tool"

freebayes_repository_name = 'freebayes_0050'
freebayes_repository_description = "Galaxy's freebayes tool"
freebayes_repository_long_description = "Long description of Galaxy's freebayes tool"

column_repository_name = 'column_maker_0050'
column_repository_description = "Add column"
column_repository_long_description = "Compute an expression on every row"

convert_repository_name = 'convert_chars_0050'
convert_repository_description = "Convert delimiters"
convert_repository_long_description = "Convert delimiters to tab"

bismark_repository_name = 'bismark_0050'
bismark_repository_description = "A flexible aligner."
bismark_repository_long_description = "A flexible aligner and methylation caller for Bisulfite-Seq applications."

category_name = 'Test 0050 Circular Dependencies 5 Levels'
category_description = 'Test circular dependency features'

running_standalone = False

class TestInstallRepositoryCircularDependencies( ShedTwillTestCase ):
    '''Verify that the code correctly handles circular dependencies down to n levels.'''
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
    def test_0005_create_convert_repository( self ):
        '''Create and populate convert_chars_0050.'''
        category = self.create_category( name=category_name, description=category_description )
        global running_standalone
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=convert_repository_name, 
                                                    description=convert_repository_description, 
                                                    long_description=convert_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            running_standalone = True
            self.upload_file( repository, 
                              'convert_chars/convert_chars.tar', 
                              strings_displayed=[], 
                              commit_message='Uploaded convert_chars.tar.' )
    def test_0010_create_column_repository( self ):
        '''Create and populate convert_chars_0050.'''
        category = self.create_category( name=category_name, description=category_description )
        repository = self.get_or_create_repository( name=column_repository_name, 
                                                    description=column_repository_description, 
                                                    long_description=column_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            self.upload_file( repository, 
                              'column_maker/column_maker.tar', 
                              strings_displayed=[], 
                              commit_message='Uploaded column_maker.tar.' )
    def test_0015_create_emboss_datatypes_repository( self ):
        '''Create and populate emboss_datatypes_0050.'''
        category = self.create_category( name=category_name, description=category_description )
        repository = self.get_or_create_repository( name=emboss_datatypes_repository_name, 
                                                    description=emboss_datatypes_repository_description, 
                                                    long_description=emboss_datatypes_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            self.upload_file( repository, 
                              'emboss/datatypes/datatypes_conf.xml', 
                              strings_displayed=[], 
                              commit_message='Uploaded datatypes_conf.xml.' )
    def test_0020_create_emboss_repository( self ):
        '''Create and populate emboss_0050.'''
        category = self.create_category( name=category_name, description=category_description )
        repository = self.get_or_create_repository( name=emboss_repository_name, 
                                                    description=emboss_repository_description, 
                                                    long_description=emboss_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            self.upload_file( repository, 
                              'emboss/emboss.tar', 
                              strings_displayed=[], 
                              commit_message='Uploaded tool tarball.' )
    def test_0025_create_filtering_repository( self ):
        '''Create and populate filtering_0050.'''
        category = self.create_category( name=category_name, description=category_description )
        repository = self.get_or_create_repository( name=filtering_repository_name, 
                                                    description=filtering_repository_description, 
                                                    long_description=filtering_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            self.upload_file( repository, 
                              'filtering/filtering_1.1.0.tar', 
                              strings_displayed=[], 
                              commit_message='Uploaded filtering.tar.' )
    def test_0030_create_freebayes_repository( self ):
        '''Create and populate freebayes_0050.'''
        category = self.create_category( name=category_name, description=category_description )
        repository = self.get_or_create_repository( name=freebayes_repository_name, 
                                                    description=freebayes_repository_description, 
                                                    long_description=freebayes_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            self.upload_file( repository, 
                              'freebayes/freebayes.tar', 
                              strings_displayed=[], 
                              commit_message='Uploaded freebayes.tar.' )
    def test_0035_create_bismark_repository( self ):
        '''Create and populate bismark_0050.'''
        category = self.create_category( name=category_name, description=category_description )
        repository = self.get_or_create_repository( name=bismark_repository_name, 
                                                    description=bismark_repository_description, 
                                                    long_description=bismark_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            self.upload_file( repository, 
                              'bismark/bismark.tar', 
                              strings_displayed=[], 
                              valid_tools_only=False,
                              commit_message='Uploaded bismark.tar.' )
    def test_0040_create_and_upload_dependency_definitions( self ):
        '''Set up the dependency structure.'''
        global running_standalone
        if running_standalone:
            column_repository = test_db_util.get_repository_by_name_and_owner( column_repository_name, common.test_user_1_name )
            convert_repository = test_db_util.get_repository_by_name_and_owner( convert_repository_name, common.test_user_1_name )
            emboss_datatypes_repository = test_db_util.get_repository_by_name_and_owner( emboss_datatypes_repository_name, common.test_user_1_name )
            emboss_repository = test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
            filtering_repository = test_db_util.get_repository_by_name_and_owner( filtering_repository_name, common.test_user_1_name )
            freebayes_repository = test_db_util.get_repository_by_name_and_owner( freebayes_repository_name, common.test_user_1_name )
            bismark_repository = test_db_util.get_repository_by_name_and_owner( bismark_repository_name, common.test_user_1_name )
            dependency_xml_path = self.generate_temp_path( 'test_1050', additional_paths=[ 'dependencies' ] )
            self.create_repository_dependency( convert_repository, depends_on=[ column_repository ], filepath=dependency_xml_path )
            self.create_repository_dependency( column_repository, depends_on=[ convert_repository ], filepath=dependency_xml_path )
            self.create_repository_dependency( emboss_datatypes_repository, depends_on=[ bismark_repository ], filepath=dependency_xml_path )
            self.create_repository_dependency( emboss_repository, depends_on=[ emboss_datatypes_repository ], filepath=dependency_xml_path )
            self.create_repository_dependency( freebayes_repository, 
                                               depends_on=[ freebayes_repository, emboss_datatypes_repository, emboss_repository, column_repository ], 
                                               filepath=dependency_xml_path )
            self.create_repository_dependency( filtering_repository, depends_on=[ emboss_repository ], filepath=dependency_xml_path )
    def test_0045_verify_repository_dependencies( self ):
        '''Verify that the generated dependency circle does not cause an infinite loop.
        Expected structure:
        
        id: 2 key: http://toolshed.local:10001__ESEP__filtering__ESEP__test__ESEP__871602b4276b
            ['http://toolshed.local:10001', 'emboss_5', 'test', '8de5fe0d7b04']
             id: 3 key: http://toolshed.local:10001__ESEP__emboss_datatypes__ESEP__test__ESEP__dbd4f68bf507
                 ['http://toolshed.local:10001', 'freebayes', 'test', 'f40028114098']
             id: 4 key: http://toolshed.local:10001__ESEP__freebayes__ESEP__test__ESEP__f40028114098
                 ['http://toolshed.local:10001', 'emboss_datatypes', 'test', 'dbd4f68bf507']
                 ['http://toolshed.local:10001', 'emboss_5', 'test', '8de5fe0d7b04']
                 ['http://toolshed.local:10001', 'column_maker', 'test', '83e956bdbac0']
             id: 5 key: http://toolshed.local:10001__ESEP__column_maker__ESEP__test__ESEP__83e956bdbac0
                 ['http://toolshed.local:10001', 'convert_chars', 'test', 'b28134220c8a']
             id: 6 key: http://toolshed.local:10001__ESEP__convert_chars__ESEP__test__ESEP__b28134220c8a
                 ['http://toolshed.local:10001', 'column_maker', 'test', '83e956bdbac0']
             id: 7 key: http://toolshed.local:10001__ESEP__emboss_5__ESEP__test__ESEP__8de5fe0d7b04
                 ['http://toolshed.local:10001', 'emboss_datatypes', 'test', 'dbd4f68bf507']
        '''
        emboss_datatypes_repository = test_db_util.get_repository_by_name_and_owner( emboss_datatypes_repository_name, common.test_user_1_name )
        emboss_repository = test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        filtering_repository = test_db_util.get_repository_by_name_and_owner( filtering_repository_name, common.test_user_1_name )
        freebayes_repository = test_db_util.get_repository_by_name_and_owner( freebayes_repository_name, common.test_user_1_name )
        column_repository = test_db_util.get_repository_by_name_and_owner( column_repository_name, common.test_user_1_name )
        convert_repository = test_db_util.get_repository_by_name_and_owner( convert_repository_name, common.test_user_1_name )
        bismark_repository = test_db_util.get_repository_by_name_and_owner( bismark_repository_name, common.test_user_1_name )
        self.check_repository_dependency( convert_repository, column_repository )
        self.check_repository_dependency( column_repository, convert_repository )
        self.check_repository_dependency( emboss_datatypes_repository, bismark_repository )
        self.check_repository_dependency( emboss_repository, emboss_datatypes_repository )
        self.check_repository_dependency( filtering_repository, emboss_repository )
        for repository in [ emboss_datatypes_repository, emboss_repository, column_repository ]:
            self.check_repository_dependency( freebayes_repository, repository )
        freebayes_dependencies = [ freebayes_repository, emboss_datatypes_repository, emboss_repository, column_repository ]
        strings_displayed = [ '%s depends on %s.' % ( freebayes_repository.name, ', '.join( repo.name for repo in freebayes_dependencies ) ) ]
        self.display_manage_repository_page( freebayes_repository, strings_displayed=strings_displayed )
    def test_0050_verify_tool_dependencies( self ):
        '''Check that freebayes and emboss display tool dependencies.'''
        freebayes_repository = test_db_util.get_repository_by_name_and_owner( freebayes_repository_name, common.test_user_1_name )
        emboss_repository = test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        self.display_manage_repository_page( freebayes_repository, 
                                             strings_displayed=[ 'freebayes', '0.9.4_9696d0ce8a9', 'samtools', '0.1.18', 'Tool dependencies' ] )
        self.display_manage_repository_page( emboss_repository, strings_displayed=[ 'Tool dependencies', 'emboss', '5.0.0', 'package' ] )
    def test_0055_install_column_repository( self ):
        '''Install column_maker with repository dependencies.'''
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        self.install_repository( column_repository_name, 
                                 common.test_user_1_name, 
                                 category_name, 
                                 install_tool_dependencies=False, 
                                 install_repository_dependencies=True, 
                                 new_tool_panel_section='column_maker' )
        installed_repositories = [ ( column_repository_name, common.test_user_1_name ), 
                                   ( convert_repository_name, common.test_user_1_name ) ]
        uninstalled_repositories = [ ( emboss_datatypes_repository_name, common.test_user_1_name ), 
                                     ( emboss_repository_name, common.test_user_1_name ), 
                                     ( filtering_repository_name, common.test_user_1_name ), 
                                     ( freebayes_repository_name, common.test_user_1_name ), 
                                     ( bismark_repository_name, common.test_user_1_name ) ]
        self.verify_installed_uninstalled_repositories( installed_repositories=installed_repositories, uninstalled_repositories=uninstalled_repositories )
    def test_0060_install_emboss_repository( self ):
        '''Install emboss_5 with repository dependencies.'''
        global running_standalone
        original_datatypes = self.get_datatypes_count()
        self.install_repository( emboss_repository_name, 
                                 common.test_user_1_name, 
                                 category_name, 
                                 install_tool_dependencies=False, 
                                 install_repository_dependencies=True, 
                                 new_tool_panel_section='emboss_5_0050' )
        if running_standalone:
            assert original_datatypes < self.get_datatypes_count(), 'Installing a repository that depends on emboss_datatypes did not add datatypes.'
        installed_repositories = [ ( emboss_datatypes_repository_name, common.test_user_1_name ), 
                                   ( column_repository_name, common.test_user_1_name ), 
                                   ( emboss_repository_name, common.test_user_1_name ), 
                                   ( convert_repository_name, common.test_user_1_name ), 
                                   ( bismark_repository_name, common.test_user_1_name ) ]
        uninstalled_repositories = [ ( filtering_repository_name, common.test_user_1_name ), 
                                     ( freebayes_repository_name, common.test_user_1_name ) ]
        self.verify_installed_uninstalled_repositories( installed_repositories=installed_repositories, uninstalled_repositories=uninstalled_repositories )
    def test_0065_deactivate_datatypes_repository( self ):
        '''Deactivate emboss_datatypes and verify that the datatypes count is reduced.'''
        original_datatypes = self.get_datatypes_count()
        repository = test_db_util.get_installed_repository_by_name_owner( emboss_datatypes_repository_name, common.test_user_1_name )
        self.uninstall_repository( repository, remove_from_disk=False )
        assert original_datatypes > self.get_datatypes_count(), 'Deactivating emboss_datatypes did not remove datatypes.'
        installed_repositories = [ ( column_repository_name, common.test_user_1_name ), 
                                   ( emboss_repository_name, common.test_user_1_name ), 
                                   ( convert_repository_name, common.test_user_1_name ), 
                                   ( bismark_repository_name, common.test_user_1_name ) ]
        uninstalled_repositories = [ ( emboss_datatypes_repository_name, common.test_user_1_name ), 
                                     ( filtering_repository_name, common.test_user_1_name ), 
                                     ( freebayes_repository_name, common.test_user_1_name ) ]
        self.verify_installed_uninstalled_repositories( installed_repositories=installed_repositories, uninstalled_repositories=uninstalled_repositories )
        strings_not_displayed = [ repository.name, repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_not_displayed=strings_not_displayed )
    def test_0070_uninstall_emboss_repository( self ):
        '''Uninstall the emboss_5 repository.'''
        repository = test_db_util.get_installed_repository_by_name_owner( emboss_repository_name, common.test_user_1_name )
        self.uninstall_repository( repository, remove_from_disk=True )
        strings_not_displayed = [ repository.name, repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_not_displayed=strings_not_displayed )
        test_db_util.ga_refresh( repository )
        self.check_galaxy_repository_tool_panel_section( repository, 'emboss_5_0050' )
        installed_repositories = [ ( column_repository_name, common.test_user_1_name ), 
                                   ( convert_repository_name, common.test_user_1_name ), 
                                   ( bismark_repository_name, common.test_user_1_name ) ]
        uninstalled_repositories = [ ( emboss_datatypes_repository_name, common.test_user_1_name ), 
                                     ( emboss_repository_name, common.test_user_1_name ), 
                                     ( filtering_repository_name, common.test_user_1_name ), 
                                     ( freebayes_repository_name, common.test_user_1_name ) ]
        self.verify_installed_uninstalled_repositories( installed_repositories=installed_repositories, uninstalled_repositories=uninstalled_repositories )
    def test_0075_install_freebayes_repository( self ):
        '''Install freebayes with repository dependencies. This should also automatically reactivate emboss_datatypes and reinstall emboss_5.'''
        original_datatypes = self.get_datatypes_count()
        strings_displayed = [ 'Handle', 'tool dependencies', 'freebayes', '0.9.4_9696d0ce8a9', 'samtools', '0.1.18' ]
        self.install_repository( freebayes_repository_name, 
                                 common.test_user_1_name, 
                                 category_name, 
                                 strings_displayed=strings_displayed,
                                 install_tool_dependencies=False, 
                                 install_repository_dependencies=True, 
                                 new_tool_panel_section='freebayes' )
        assert original_datatypes < self.get_datatypes_count(), 'Installing a repository that depends on emboss_datatypes did not add datatypes.'
        emboss_repository = test_db_util.get_installed_repository_by_name_owner( emboss_repository_name, common.test_user_1_name )
        datatypes_repository = test_db_util.get_installed_repository_by_name_owner( emboss_datatypes_repository_name, common.test_user_1_name )
        strings_displayed = [ emboss_repository.name, 
                              emboss_repository.installed_changeset_revision, 
                              datatypes_repository.name, 
                              datatypes_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
        installed_repositories = [ ( column_repository_name, common.test_user_1_name ), 
                                   ( emboss_datatypes_repository_name, common.test_user_1_name ), 
                                   ( emboss_repository_name, common.test_user_1_name ), 
                                   ( freebayes_repository_name, common.test_user_1_name ),
                                   ( convert_repository_name, common.test_user_1_name ), 
                                   ( bismark_repository_name, common.test_user_1_name ) ]
        uninstalled_repositories = [ ( filtering_repository_name, common.test_user_1_name ) ]
        self.verify_installed_uninstalled_repositories( installed_repositories=installed_repositories, uninstalled_repositories=uninstalled_repositories )

