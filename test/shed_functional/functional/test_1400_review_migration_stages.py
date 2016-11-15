from shed_functional.base.twilltestcase import common, ShedTwillTestCase


class TestToolMigrationStages( ShedTwillTestCase ):
    '''Verify that the migration stages display correctly.'''

    def test_0000_initiate_users( self ):
        """Create necessary user accounts and login as an admin user."""
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        self.test_db_util.get_private_role( admin_user )
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        self.test_db_util.get_private_role( admin_user )

    def test_0005_load_migration_stages_page( self ):
        '''Load the migration page and check for the appropriate migration stages.'''
        stages = []
        migration_message_strings = [ 'The&nbsp;Emboss&nbsp;5.0.0&nbsp;tools&nbsp;have&nbsp;been&nbsp;eliminated',
                                      'The&nbsp;freebayes&nbsp;tool&nbsp;has&nbsp;been&nbsp;eliminated',
                                      'The&nbsp;NCBI&nbsp;BLAST+&nbsp;tools',
                                      'The&nbsp;tools&nbsp;&#34;Map&nbsp;with&nbsp;BWA&nbsp;for&nbsp;Illumina&#34;',
                                      'FASTQ&nbsp;to&nbsp;BAM,&nbsp;SAM&nbsp;to&nbsp;FASTQ,&nbsp;BAM&nbsp;',
                                      'Map&nbsp;with&nbsp;Bowtie&nbsp;for&nbsp;Illumina,&nbsp;',
                                      'BAM-to-SAM&nbsp;converts&nbsp;BAM&nbsp;format' ]
        migrated_repository_names = [ 'emboss_5', 'emboss_datatypes', 'freebayes', 'ncbi_blast_plus',
                                      'blast_datatypes', 'bwa_wrappers', 'picard', 'lastz',
                                      'lastz_paired_reads', 'bowtie_color_wrappers', 'bowtie_wrappers',
                                      'xy_plot', 'bam_to_sam' ]
        migrated_tool_dependencies = [ 'emboss', '5.0.0', 'freebayes', '0.9.4_a46483351fd0196637614121868fb5c386612b55',
                                       'samtools', '0.1.18', 'blast+', '2.2.26+', 'bwa', '0.5.9', 'picard', '1.56.0',
                                       'lastz', '1.02.00', 'bowtie', '0.12.7', 'FreeBayes requires g++', 'ncurses', 'zlib',
                                       'blast.ncbi.nlm.nih.gov', 'fastx_toolkit', '0.0.13', 'samtools', '0.1.16', 'cufflinks',
                                       '2.1.1', 'R', '2.11.0' ]
        migration_scripts = [ '0002_tools.sh', '0003_tools.sh', '0004_tools.sh', '0005_tools.sh', '0006_tools.sh',
                              '0007_tools.sh', '0008_tools.sh' ]
        stages.extend( migration_scripts + migrated_tool_dependencies + migrated_repository_names )
        stages.extend( migration_message_strings )
        self.load_galaxy_tool_migrations_page( strings_displayed=stages )
