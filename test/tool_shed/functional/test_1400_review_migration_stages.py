from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
import tool_shed.base.test_db_util as test_db_util


class TestToolMigrationStages( ShedTwillTestCase ):
    '''Verify that the migration stages display correctly.'''

    def test_0000_initiate_users( self ):
        """Create necessary user accounts and login as an admin user."""
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        admin_user_private_role = test_db_util.get_private_role( admin_user )
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        admin_user = test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        admin_user_private_role = test_db_util.get_private_role( admin_user )

    def test_0005_load_migration_stages_page( self ):
        '''Load the migration page and check for the appropriate migration stages.'''
        stages = [ 
                      'emboss_5', 'emboss_datatypes', 'emboss', '5.0.0', '0002_tools.sh', 
                      'freebayes', '0.9.4_9696d0ce8a962f7bb61c4791be5ce44312b81cf8', 'samtools', '0.1.18', 'FreeBayes requires g++',
                      'ncurses', 'zlib', '0003_tools.sh',
                      'ncbi_blast_plus', 'blast_datatypes', 'blast+', '2.2.26+', 'blast.ncbi.nlm.nih.gov', 'NCBI BLAST+ tools', '0004_tools.sh',
                      'bwa_wrappers', '0.5.9', 'zlib and libpthread', 'Map with BWA for Illumina', '0005_tools.sh',
                      'picard', '1.56.0', 'FASTQ to BAM', '0006_tools.sh',
                      'lastz', '1.02.00', 'bowtie', '0.12.7', 'Map with Bowtie for Illumina', 'Bowtie requires libpthread', '0007_tools.sh'
                 ]
        self.load_galaxy_tool_migrations_page( strings_displayed=stages )
        
