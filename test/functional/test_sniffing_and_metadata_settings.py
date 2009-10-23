import galaxy.model
from galaxy.model.orm import *
from galaxy.model.mapping import context as sa_session
from base.twilltestcase import TwillTestCase

class SniffingAndMetaDataSettings( TwillTestCase ):
    def test_000_axt_datatype( self ):
        """Testing correctly sniffing axt data type upon upload"""
        self.logout()
        self.login( email='test@bx.psu.edu' )
        global admin_user
        admin_user = sa_session.query( galaxy.model.User ).filter( galaxy.model.User.table.c.email=='test@bx.psu.edu' ).one()
        self.new_history( name='history1' )
        global history1
        history1 = sa_session.query( galaxy.model.History ) \
                             .filter( and_( galaxy.model.History.table.c.deleted==False,
                                            galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                             .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                             .first()
        assert history1 is not None, "Problem retrieving history1 from database"
        self.upload_file( '1.axt' )
        self.verify_dataset_correctness( '1.axt' )
        self.check_history_for_string( '1.axt format: <span class="axt">axt</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="1.axt" value="\?" Change data type selected value="axt" selected="yes"' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        assert latest_hda is not None, "Problem retrieving axt hda from the database"
        if not latest_hda.name == '1.axt' and not latest_hda.extension == 'axt':
            raise AssertionError, "axt data type was not correctly sniffed."
    def test_005_bed_datatype( self ):
        """Testing correctly sniffing bed data type upon upload"""
        self.upload_file( '1.bed' )
        self.verify_dataset_correctness( '1.bed' )
        self.check_history_for_string( '1.bed format: <span class="bed">bed</span>, database: \? Info: uploaded file')
        self.check_metadata_for_string( 'value="1.bed" value="\?"' )
        self.check_metadata_for_string( 'Chrom column: <option value="1" selected> Start column: <option value="2" selected>' )
        self.check_metadata_for_string( 'End column: <option value="3" selected> Strand column <option value="6" selected>' )
        self.check_metadata_for_string( 'Convert to new format value="bed">Convert Genomic Intervals To BED <option value="gff">Convert BED to GFF' )
        self.check_metadata_for_string( 'Change data type selected value="bed" selected="yes"' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        assert latest_hda is not None, "Problem retrieving bed hda from the database"
        if not latest_hda.name == '1.bed' and not latest_hda.extension == 'bed':
            raise AssertionError, "bed data type was not correctly sniffed."
    def test_010_blastxml_datatype( self ):
        """Testing correctly sniffing blastxml data type upon upload"""
        self.upload_file( 'megablast_xml_parser_test1.gz' )
        self.check_history_for_string( 'NCBI Blast XML data format: <span class="blastxml">blastxml</span>' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        assert latest_hda is not None, "Problem retrieving blastxml hda from the database"
        if not latest_hda.name == 'megablast_xml_parser_test1' and not latest_hda.extension == 'blastxml':
            raise AssertionError, "blastxml data type was not correctly sniffed."
    def test_015_csfasta_datatype( self ):
        """Testing correctly sniffing csfasta data type upon upload"""
        self.upload_file( 'shrimp_cs_test1.csfasta' )
        self.verify_dataset_correctness( 'shrimp_cs_test1.csfasta' )
        self.check_history_for_string( '162.6 Kb, format: <span class="csfasta">csfasta</span>, <td>&gt;2_14_26_F3,-1282216.0</td>' )
        self.check_metadata_for_string( 'value="shrimp_cs_test1.csfasta" value="\?" Change data type value="csfasta" selected="yes"' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        assert latest_hda is not None, "Problem retrieving csfasta hda from the database"
        if not latest_hda.name == 'shrimp_cs_test1.csfasta' and not latest_hda.extension == 'csfasta':
            raise AssertionError, "csfasta data type was not correctly sniffed."
    def test_020_customtrack_datatype( self ):
        """Testing correctly sniffing customtrack data type upon upload"""
        self.upload_file( '1.customtrack' )
        self.verify_dataset_correctness( '1.customtrack' )
        self.check_history_for_string( '1.customtrack format: <span class="customtrack">customtrack</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="1.customtrack" value="\?" Change data type selected value="customtrack" selected="yes"' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        assert latest_hda is not None, "Problem retrieving customtrack hda from the database"
        if not latest_hda.name == '1.customtrack' and not latest_hda.extension == 'customtrack':
            raise AssertionError, "customtrack data type was not correctly sniffed."
    def test_025_fasta_datatype( self ):
        """Testing correctly sniffing fasta data type upon upload"""
        self.upload_file( '1.fasta' )
        self.verify_dataset_correctness( '1.fasta' )
        self.check_history_for_string( '1.fasta format: <span class="fasta">fasta</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="1.fasta" value="\?" Change data type selected value="fasta" selected="yes"' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        assert latest_hda is not None, "Problem retrieving fasta hda from the database"
        if not latest_hda.name == '1.fasta' and not latest_hda.extension == 'fasta':
            raise AssertionError, "fasta data type was not correctly sniffed."
    def test_035_gff_datatype( self ):
        """Testing correctly sniffing gff data type upon upload"""
        self.upload_file( '5.gff' )
        self.verify_dataset_correctness( '5.gff' )
        self.check_history_for_string( '5.gff format: <span class="gff">gff</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="5.gff" value="\?"' )
        self.check_metadata_for_string( 'Convert to new format <option value="bed">Convert GFF to BED' )
        self.check_metadata_for_string( 'Change data type selected value="gff" selected="yes"' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        assert latest_hda is not None, "Problem retrieving gff hda from the database"
        if not latest_hda.name == '5.gff' and not latest_hda.extension == 'gff':
            raise AssertionError, "gff data type was not correctly sniffed."
    def test_040_gff3_datatype( self ):
        """Testing correctly sniffing gff3 data type upon upload"""
        self.upload_file( '5.gff3' )
        self.verify_dataset_correctness( '5.gff3' )
        self.check_history_for_string( '5.gff3 format: <span class="gff3">gff3</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="5.gff3" value="\?"' )
        self.check_metadata_for_string( 'Convert to new format <option value="bed">Convert GFF to BED' )
        self.check_metadata_for_string( 'Change data type selected value="gff3" selected="yes"' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        assert latest_hda is not None, "Problem retrieving gff3 hda from the database"
        if not latest_hda.name == '5.gff3' and not latest_hda.extension == 'gff3':
            raise AssertionError, "gff3 data type was not correctly sniffed."
        # TODO: the following test generates a data.hid == None, breaking this and all following tests
        # I am not currently able to track down why, and uploading inappropriate files outside of the
        # functional test framework seems to generate valid hids, so this needs to be tracked down and fixed
        # ASAP, un-commenting this test.
        #def test_045_html_datatype( self ):
        #"""Testing correctly sniffing html data type upon upload"""
        #self.upload_file( 'html_file.txt' )
        #self.check_history_for_string( 'An error occurred running this job: No data: you attempted to upload an inappropriate file.' )
        #latest_hda = galaxy.model.HistoryDatasetAssociation.query() \
        #    .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
        #assert latest_hda is not None, "Problem retrieving html hda from the database"
        #if not latest_hda.name == 'html_file.txt' and not latest_hda.extension == 'data':
        #    raise AssertionError, "html data type was not correctly sniffed."
    def test_050_interval_datatype( self ):
        """Testing correctly sniffing interval data type upon upload"""
        self.upload_file( '1.interval' )
        self.verify_dataset_correctness( '1.interval' )
        self.check_history_for_string( '1.interval format: <span class="interval">interval</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="1.interval" value="\?"' )
        self.check_metadata_for_string( 'Chrom column: <option value="1" selected> Start column: <option value="2" selected>' )
        self.check_metadata_for_string( 'End column: <option value="3" selected> Strand column <option value="6" selected>' )
        self.check_metadata_for_string( 'Convert to new format <option value="bed">Convert Genomic Intervals To BED' )
        self.check_metadata_for_string( 'Change data type selected value="interval" selected="yes"' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        assert latest_hda is not None, "Problem retrieving interval hda from the database"
        if not latest_hda.name == '1.interval' and not latest_hda.extension == 'interval':
            raise AssertionError, "interval data type was not correctly sniffed."
    def test_055_lav_datatype( self ):
        """Testing correctly sniffing lav data type upon upload"""
        self.upload_file( '1.lav' )
        self.verify_dataset_correctness( '1.lav' )
        self.check_history_for_string( '1.lav format: <span class="lav">lav</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="1.lav" value="\?"' )
        self.check_metadata_for_string( 'Change data type selected value="lav" selected="yes"' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        assert latest_hda is not None, "Problem retrieving lav hda from the database"
        if not latest_hda.name == '1.lav' and not latest_hda.extension == 'lav':
            raise AssertionError, "lav data type was not correctly sniffed."
    def test_060_maf_datatype( self ):
        """Testing correctly sniffing maf data type upon upload"""
        self.upload_file( '3.maf' )
        self.verify_dataset_correctness( '3.maf' )
        self.check_history_for_string( '3.maf format: <span class="maf">maf</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="3.maf" value="\?"' )
        self.check_metadata_for_string( 'Convert to new format <option value="interval">Convert MAF to Genomic Intervals <option value="fasta">Convert MAF to Fasta' )
        self.check_metadata_for_string( 'Change data type selected value="maf" selected="yes"' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        assert latest_hda is not None, "Problem retrieving maf hda from the database"
        if not latest_hda.name == '3.maf' and not latest_hda.extension == 'maf':
            raise AssertionError, "maf data type was not correctly sniffed."
    def test_065_qual454_datatype( self ):
        """Testing correctly sniffing qual454 data type upon upload"""
        self.upload_file( 'qualscores.qual454' )        
        self.verify_dataset_correctness( 'qualscores.qual454' )
        self.check_history_for_string( '5.6 Kb, format: <span class="qual454">qual454</span>, database: \?' )
        self.check_metadata_for_string( 'Change data type value="qual454" selected="yes">qual454' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        assert latest_hda is not None, "Problem retrieving qual454 hda from the database"
        if not latest_hda.name == 'qualscores.qual454' and not latest_hda.extension == 'qual454':
            raise AssertionError, "qual454 data type was not correctly sniffed."
    def test_070_qualsolid_datatype( self ):
        """Testing correctly sniffing qualsolid data type upon upload"""
        self.upload_file( 'qualscores.qualsolid' )        
        self.verify_dataset_correctness('qualscores.qualsolid' )
        self.check_history_for_string('2.5 Kb, format: <span class="qualsolid">qualsolid</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'Change data type value="qualsolid" selected="yes">qualsolid' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        assert latest_hda is not None, "Problem retrieving qualsolid hda from the database"
        if not latest_hda.name == 'qualscores.qualsolid' and not latest_hda.extension == 'qualsolid':
            raise AssertionError, "qualsolid data type was not correctly sniffed."
    def test_075_tabular_datatype( self ):
        """Testing correctly sniffing tabular data type upon upload"""
        self.upload_file( '1.tabular' )
        self.verify_dataset_correctness( '1.tabular' )
        self.check_history_for_string( '1.tabular format: <span class="tabular">tabular</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="1.tabular" value="\?"' )
        self.check_metadata_for_string( 'Change data type selected value="tabular" selected="yes"' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        assert latest_hda is not None, "Problem retrieving tabular hda from the database"
        if not latest_hda.name == '1.tabular' and not latest_hda.extension == 'tabular':
            raise AssertionError, "tabular data type was not correctly sniffed."
    def test_080_wig_datatype( self ):
        """Testing correctly sniffing wig data type upon upload"""
        self.upload_file( '1.wig' )
        self.verify_dataset_correctness( '1.wig' )
        self.check_history_for_string( '1.wig format: <span class="wig">wig</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="1.wig" value="\?"' )
        self.check_metadata_for_string( 'Change data type selected value="wig" selected="yes"' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        assert latest_hda is not None, "Problem retrieving wig hda from the database"
        if not latest_hda.name == '1.wig' and not latest_hda.extension == 'wig':
            raise AssertionError, "wig data type was not correctly sniffed."
    def test_090_sam_datatype( self ):
        """Testing correctly sniffing sam format upon upload"""
        self.upload_file( '1.sam' )
        self.verify_dataset_correctness( '1.sam' )
        self.check_history_for_string( '1.sam format: <span class="sam">sam</span>, database: \? Info: uploaded sam file' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        assert latest_hda is not None, "Problem retrieving sam hda from the database"
        if not latest_hda.name == '1.sam' and not latest_hda.extension == 'sam':
            raise AssertionError, "sam data type was not correctly sniffed."
    def test_095_fastq_datatype( self ):
        """Testing correctly sniffing fastq ( generic ) data type upon upload"""
        self.upload_file( '2gen.fastq' )
        self.verify_dataset_correctness( '2gen.fastq' )
        self.check_history_for_string( '2gen.fastq format: <span class="fastq">fastq</span>, database: \? Info: uploaded fastq file' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        assert latest_hda is not None, "Problem retrieving fastq hda from the database"
        if not latest_hda.name == '2gen.fastq' and not latest_hda.extension == 'fastq':
            raise AssertionError, "fastq data type was not correctly sniffed."
    def test_9999_clean_up( self ):
        self.delete_history( id=self.security.encode_id( history1.id ) )
        self.logout()
