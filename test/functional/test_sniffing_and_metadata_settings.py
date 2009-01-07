from base.twilltestcase import TwillTestCase

class SniffingAndMetaDataSettings( TwillTestCase ):

    def test_00_axt_datatype( self ):
        """Testing correctly sniffing axt data type upon upload"""
        self.login()
        self.upload_file('1.axt')
        self.verify_dataset_correctness('1.axt')
        self.check_history_for_string('1.axt format: <span class="axt">axt</span>, database: \? Info: uploaded file')
        self.check_metadata_for_string('value="1.axt" value="\?" Change data type selected value="axt" selected="yes"')
        self.delete_history_item( 1 )
    def test_05_bed_datatype( self ):
        """Testing correctly sniffing bed data type upon upload"""
        self.upload_file('1.bed')
        self.verify_dataset_correctness('1.bed')
        self.check_history_for_string('1.bed format: <span class="bed">bed</span>, database: \? Info: uploaded file')
        self.check_metadata_for_string('value="1.bed" value="\?"')
        self.check_metadata_for_string('Chrom column: <option value="1" selected> Start column: <option value="2" selected>')
        self.check_metadata_for_string('End column: <option value="3" selected> Strand column <option value="6" selected>')
        self.check_metadata_for_string('Convert to new format <option value="bed">Genomic Intervals To BED <option value="gff">BED to GFF')
        self.check_metadata_for_string('Change data type selected value="bed" selected="yes"')
        self.delete_history_item( 1 )
    def test_10_customtrack_datatype( self ):
        """Testing correctly sniffing customtrack data type upon upload"""
        self.upload_file('1.customtrack')
        self.verify_dataset_correctness('1.customtrack')
        self.check_history_for_string('1.customtrack format: <span class="customtrack">customtrack</span>, database: \? Info: uploaded file')
        self.check_metadata_for_string('value="1.customtrack" value="\?" Change data type selected value="customtrack" selected="yes"')
        self.delete_history_item( 1 )
    def test_15_fasta_datatype( self ):
        """Testing correctly sniffing fasta data type upon upload"""
        self.upload_file('1.fasta')
        self.verify_dataset_correctness('1.fasta')
        self.check_history_for_string('1.fasta format: <span class="fasta">fasta</span>, database: \? Info: uploaded file')
        self.check_metadata_for_string('value="1.fasta" value="\?" Change data type selected value="fasta" selected="yes"')
        self.delete_history_item( 1 )
    def test_18_fastqsolexa_datatype( self ):
        """Testing correctly sniffing fastqsolexa ( the Solexa variant ) data type upon upload"""
        self.upload_file('1.fastqsolexa')
        self.verify_dataset_correctness('1.fastqsolexa')
        self.check_history_for_string('1.fastqsolexa format: <span class="fastqsolexa">fastqsolexa</span>, database: \? Info: uploaded fastqsolexa file')
        self.delete_history_item( 1 )
    def test_20_gff_datatype( self ):
        """Testing correctly sniffing gff data type upon upload"""
        self.upload_file('5.gff')
        self.verify_dataset_correctness('5.gff')
        self.check_history_for_string('5.gff format: <span class="gff">gff</span>, database: \? Info: uploaded file')
        self.check_metadata_for_string('value="5.gff" value="\?"')
        self.check_metadata_for_string('Convert to new format <option value="bed">GFF to BED')
        self.check_metadata_for_string('Change data type selected value="gff" selected="yes"')
        self.delete_history_item( 1 )
    def test_25_gff3_datatype( self ):
        """Testing correctly sniffing gff3 data type upon upload"""
        self.upload_file('5.gff3')
        self.verify_dataset_correctness('5.gff3')
        self.check_history_for_string('5.gff3 format: <span class="gff3">gff3</span>, database: \? Info: uploaded file')
        self.check_metadata_for_string('value="5.gff3" value="\?"')
        self.check_metadata_for_string('Convert to new format <option value="bed">GFF to BED')
        self.check_metadata_for_string('Change data type selected value="gff3" selected="yes"')
        self.delete_history_item( 1 )
    def test_30_html_datatype( self ):
        """Testing correctly sniffing html data type upon upload"""
        self.upload_file('html_file.txt')
        self.check_history_for_string('No data: attempted to upload an empty or inappropriate file')
        self.delete_history_item( 1 )
    def test_35_interval_datatype( self ):
        """Testing correctly sniffing interval data type upon upload"""
        self.upload_file('1.interval')
        self.verify_dataset_correctness('1.interval')
        self.check_history_for_string('1.interval format: <span class="interval">interval</span>, database: \? Info: uploaded file')
        self.check_metadata_for_string('value="1.interval" value="\?"')
        self.check_metadata_for_string('Chrom column: <option value="1" selected> Start column: <option value="2" selected>')
        self.check_metadata_for_string('End column: <option value="3" selected> Strand column <option value="6" selected>')
        self.check_metadata_for_string('Convert to new format <option value="bed">Genomic Intervals To BED')
        self.check_metadata_for_string('Change data type selected value="interval" selected="yes"')
        self.delete_history_item( 1 )
    def test_40_lav_datatype( self ):
        """Testing correctly sniffing lav data type upon upload"""
        self.upload_file('1.lav')
        self.verify_dataset_correctness('1.lav')
        self.check_history_for_string('1.lav format: <span class="lav">lav</span>, database: \? Info: uploaded file')
        self.check_metadata_for_string('value="1.lav" value="\?"')
        self.check_metadata_for_string('Change data type selected value="lav" selected="yes"')
        self.delete_history_item( 1 )
    def test_45_maf_datatype( self ):
        """Testing correctly sniffing maf data type upon upload"""
        self.upload_file('3.maf')
        self.verify_dataset_correctness('3.maf')
        self.check_history_for_string('3.maf format: <span class="maf">maf</span>, database: \? Info: uploaded file')
        self.check_metadata_for_string('value="3.maf" value="\?"')
        self.check_metadata_for_string('Convert to new format <option value="interval">MAF to Genomic Intervals <option value="fasta">MAF to Fasta')
        self.check_metadata_for_string('Change data type selected value="maf" selected="yes"')
        self.delete_history_item( 1 )
    def test_50_tabular_datatype( self ):
        """Testing correctly sniffing tabular data type upon upload"""
        self.upload_file('1.tabular')
        self.verify_dataset_correctness('1.tabular')
        self.check_history_for_string('1.tabular format: <span class="tabular">tabular</span>, database: \? Info: uploaded file')
        self.check_metadata_for_string('value="1.tabular" value="\?"')
        self.check_metadata_for_string('Change data type selected value="tabular" selected="yes"')
        self.delete_history_item( 1 )
    def test_55_wig_datatype( self ):
        """Testing correctly sniffing wig data type upon upload"""
        self.upload_file('1.wig')
        self.verify_dataset_correctness('1.wig')
        self.check_history_for_string('1.wig format: <span class="wig">wig</span>, database: \? Info: uploaded file')
        self.check_metadata_for_string('value="1.wig" value="\?"')
        self.check_metadata_for_string('Change data type selected value="wig" selected="yes"')
        self.delete_history_item( 1 )
    def test_60_blastxml_datatype( self ):
        """Testing correctly sniffing blastxml data type upon upload"""
        self.upload_file( 'megablast_xml_parser_test1.blastxml' )
        self.verify_dataset_correctness( 'megablast_xml_parser_test1.blastxml' )
        self.check_history_for_string( 'NCBI Blast XML data' )
        self.check_history_for_string( 'format: <span class="blastxml">blastxml</span>' )
        self.delete_history_item( 1 )
    def test_9999_clean_up( self ):
        self.delete_history()
        self.logout()
