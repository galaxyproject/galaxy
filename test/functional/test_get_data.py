import galaxy.model
from galaxy.model.orm import *
from galaxy.model.mapping import context as sa_session
from base.twilltestcase import TwillTestCase
from base.test_db_util import *

class UploadData( TwillTestCase ):
    def test_0000_setup_upload_tests( self ):
        """Configuring upload tests, setting admin_user"""
        self.logout()
        self.login( email='test@bx.psu.edu' )
        global admin_user
        admin_user = get_user( email='test@bx.psu.edu' )
    def test_0005_upload_file( self ):               
        """Test uploading 1.bed, NOT setting the file format"""
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '1.bed' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.bed', hid=str( hda.hid ) )
        self.check_history_for_string( "<th>1.Chrom</th><th>2.Start</th><th>3.End</th>" )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0006_upload_file( self ):               
        """Test uploading 1.bed.spaces, with space to tab selected, NOT setting the file format"""
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '1.bed.spaces', space_to_tab = True )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.bed', hid=str( hda.hid ) )
        self.check_history_for_string( "<th>1.Chrom</th><th>2.Start</th><th>3.End</th>" )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0010_upload_file( self ):
        """Test uploading 4.bed.gz, manually setting the file format"""
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '4.bed.gz', dbkey='hg17', ftype='bed' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '4.bed', hid=str( hda.hid ) )
        self.check_history_for_string( "<th>1.Chrom</th><th>2.Start</th><th>3.End</th>" )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0012_upload_file( self ):
        """Test uploading 4.bed.bz2, manually setting the file format"""
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '4.bed.bz2', dbkey='hg17', ftype='bed' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '4.bed', hid=str( hda.hid ) )
        self.check_history_for_string( "<th>1.Chrom</th><th>2.Start</th><th>3.End</th>" )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0015_upload_file( self ):
        """Test uploading 1.scf, manually setting the file format"""
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '1.scf', ftype='scf' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.scf', hid=str( hda.hid ) )
        self.check_history_for_string( "Binary scf sequence file</pre>" )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0020_upload_file( self ):
        """Test uploading 1.scf, NOT setting the file format"""
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '1.scf' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.check_history_for_string( "File Format' to 'Scf' when uploading scf files" )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0025_upload_file( self ):
        """Test uploading 4.bed.zip, manually setting the file format"""
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '4.bed.zip', ftype='bed' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '4.bed', hid=str( hda.hid ) )
        self.check_history_for_string( "<th>1.Chrom</th><th>2.Start</th><th>3.End</th>" )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0030_upload_file( self ):
        """Test uploading 4.bed.zip, NOT setting the file format"""
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '4.bed.zip' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '4.bed', hid=str( hda.hid ) )
        self.check_history_for_string( "<th>1.Chrom</th><th>2.Start</th><th>3.End</th>" )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0035_upload_file( self ):
        """Test uploading 1.sam NOT setting the file format"""
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '1.sam' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.sam', hid=str( hda.hid ) )
        self.check_history_for_string( "<th>1.QNAME</th><th>2.FLAG</th><th>3.RNAME</th><th>4.POS</th>" )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0040_upload_file( self ):
        """Test uploading 1.sff, NOT setting the file format"""
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '1.sff' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.sff', hid=str( hda.hid ) )
        self.check_history_for_string( 'format: <span class="sff">sff' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0045_upload_file( self ):
        """Test uploading 454Score.pdf, NOT setting the file format"""
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '454Score.pdf' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.check_history_for_string( "1: 454Score.pdf</span>" )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0050_upload_file( self ):
        """Test uploading 454Score.png, NOT setting the file format"""
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '454Score.png' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.check_history_for_string( "454Score.png" )
    def test_0055_upload_file( self ):
        """Test uploading lped composite datatype file, manually setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        # lped data types include a ped_file and a map_file ( which is binary )
        self.upload_file( None, ftype='lped', metadata = [ { 'name':'base_name', 'value':'rgenetics' } ], composite_data = [ { 'name':'ped_file', 'value':'tinywga.ped' }, { 'name':'map_file', 'value':'tinywga.map'} ] )
        # Get the latest hid for testing
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        # We'll test against the resulting ped file and map file for correctness
        self.verify_composite_datatype_file_content( 'tinywga.ped', str( hda.id ), base_name = 'rgenetics.ped' )
        self.verify_composite_datatype_file_content( 'tinywga.map', str( hda.id ), base_name = 'rgenetics.map' )
        self.check_history_for_string( "rgenetics" )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0056_upload_file( self ):
        """Test uploading lped composite datatype file, manually setting the file format, and using space to tab on one file (tinywga.ped)"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        # lped data types include a ped_file and a map_file ( which is binary )
        self.upload_file( None, ftype='lped', metadata = [ { 'name':'base_name', 'value':'rgenetics' } ], composite_data = [ { 'name':'ped_file', 'value':'tinywga.ped', 'space_to_tab':True }, { 'name':'map_file', 'value':'tinywga.map'} ] )
        # Get the latest hid for testing
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        # We'll test against the resulting ped file and map file for correctness
        self.verify_composite_datatype_file_content( 'tinywga.ped.space_to_tab', str( hda.id ), base_name = 'rgenetics.ped' )
        self.verify_composite_datatype_file_content( 'tinywga.map', str( hda.id ), base_name = 'rgenetics.map' )
        self.check_history_for_string( "rgenetics" )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0060_upload_file( self ):
        """Test uploading pbed composite datatype file, manually setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        # pbed data types include a bim_file, a bed_file and a fam_file
        self.upload_file( None, ftype='pbed', metadata = [ { 'name':'base_name', 'value':'rgenetics' } ], composite_data = [ { 'name':'bim_file', 'value':'tinywga.bim' }, { 'name':'bed_file', 'value':'tinywga.bed'}, { 'name':'fam_file', 'value':'tinywga.fam' } ] )
        # Get the latest hid for testing
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        # We'll test against the resulting ped file and map file for correctness
        self.verify_composite_datatype_file_content( 'tinywga.bim', str( hda.id ), base_name = 'rgenetics.bim' )
        self.verify_composite_datatype_file_content( 'tinywga.bed', str( hda.id ), base_name = 'rgenetics.bed' )
        self.verify_composite_datatype_file_content( 'tinywga.fam', str( hda.id ), base_name = 'rgenetics.fam' )
        self.check_history_for_string( "rgenetics" )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0065_upload_file( self ):
        """Test uploading asian_chars_1.txt, NOT setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( 'asian_chars_1.txt' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( 'asian_chars_1.txt', hid=str( hda.hid ) )
        self.check_history_for_string( 'uploaded multi-byte char file' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0070_upload_file( self ):
        """Test uploading 2gen.fastq, NOT setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '2gen.fastq' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '2gen.fastq', hid=str( hda.hid ) )
        self.check_history_for_string( '2gen.fastq format: <span class="fastq">fastq</span>, database: \? Info: uploaded fastq file' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0075_upload_file( self ):
        """Test uploading 1.wig, NOT setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '1.wig' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.wig', hid=str( hda.hid ) )
        self.check_history_for_string( '1.wig format: <span class="wig">wig</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="1.wig" value="\?"' )
        self.check_metadata_for_string( 'Change data type selected value="wig" selected="yes"' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0080_upload_file( self ):
        """Test uploading 1.tabular, NOT setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '1.tabular' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.tabular', hid=str( hda.hid ) )
        self.check_history_for_string( '1.tabular format: <span class="tabular">tabular</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="1.tabular" value="\?"' )
        self.check_metadata_for_string( 'Change data type selected value="tabular" selected="yes"' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0085_upload_file( self ):
        """Test uploading qualscores.qualsolid, NOT setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( 'qualscores.qualsolid' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( 'qualscores.qualsolid', hid=str( hda.hid ) )
        self.check_history_for_string( '48 lines format: <span class="qualsolid">qualsolid</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'Change data type value="qualsolid" selected="yes">qualsolid' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0090_upload_file( self ):
        """Test uploading qualscores.qual454, NOT setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( 'qualscores.qual454' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( 'qualscores.qual454', hid=str( hda.hid ) )
        self.check_history_for_string( '49 lines format: <span class="qual454">qual454</span>, database: \?' )
        self.check_metadata_for_string( 'Change data type value="qual454" selected="yes">qual454' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0095_upload_file( self ):
        """Test uploading 3.maf, NOT setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '3.maf' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '3.maf', hid=str( hda.hid ) )
        self.check_history_for_string( '3.maf format: <span class="maf">maf</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="3.maf" value="\?"' )
        self.check_metadata_for_string( 'Convert to new format <option value="interval">Convert MAF to Genomic Intervals <option value="fasta">Convert MAF to Fasta' )
        self.check_metadata_for_string( 'Change data type selected value="maf" selected="yes"' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0100_upload_file( self ):
        """Test uploading 1.lav, NOT setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '1.lav' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.lav', hid=str( hda.hid ) )
        self.check_history_for_string( '1.lav format: <span class="lav">lav</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="1.lav" value="\?"' )
        self.check_metadata_for_string( 'Change data type selected value="lav" selected="yes"' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0105_upload_file( self ):
        """Test uploading 1.interval, NOT setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '1.interval' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.interval', hid=str( hda.hid ) )
        self.check_history_for_string( '1.interval format: <span class="interval">interval</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="1.interval" value="\?"' )
        self.check_metadata_for_string( 'Chrom column: <option value="1" selected> Start column: <option value="2" selected>' )
        self.check_metadata_for_string( 'End column: <option value="3" selected> Strand column <option value="6" selected>' )
        self.check_metadata_for_string( 'Convert to new format <option value="bed">Convert Genomic Intervals To BED' )
        self.check_metadata_for_string( 'Change data type selected value="interval" selected="yes"' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0110_upload_file( self ):
        """Test uploading 5.gff3, NOT setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '5.gff3' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '5.gff3', hid=str( hda.hid ) )
        self.check_history_for_string( '5.gff3 format: <span class="gff3">gff3</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="5.gff3" value="\?"' )
        self.check_metadata_for_string( 'Convert to new format <option value="bed">Convert GFF to BED' )
        self.check_metadata_for_string( 'Change data type selected value="gff3" selected="yes"' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0115_upload_file( self ):
        """Test uploading html_file.txt, NOT setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( 'html_file.txt' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.check_history_for_string( 'The uploaded file contains inappropriate content' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0120_upload_file( self ):
        """Test uploading 5.gff, NOT setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '5.gff' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '5.gff', hid=str( hda.hid ) )
        self.check_history_for_string( '5.gff format: <span class="gff">gff</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="5.gff" value="\?"' )
        self.check_metadata_for_string( 'Convert to new format <option value="bed">Convert GFF to BED' )
        self.check_metadata_for_string( 'Change data type selected value="gff" selected="yes"' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0125_upload_file( self ):
        """Test uploading 1.fasta, NOT setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '1.fasta' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.fasta', hid=str( hda.hid ) )
        self.check_history_for_string( '1.fasta format: <span class="fasta">fasta</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="1.fasta" value="\?" Change data type selected value="fasta" selected="yes"' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0130_upload_file( self ):
        """Test uploading 1.customtrack, NOT setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '1.customtrack' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.customtrack', hid=str( hda.hid ) )
        self.check_history_for_string( '1.customtrack format: <span class="customtrack">customtrack</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="1.customtrack" value="\?" Change data type selected value="customtrack" selected="yes"' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0135_upload_file( self ):
        """Test uploading shrimp_cs_test1.csfasta, NOT setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( 'shrimp_cs_test1.csfasta' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( 'shrimp_cs_test1.csfasta', hid=str( hda.hid ) )
        self.check_history_for_string( '2,500 sequences format: <span class="csfasta">csfasta</span>, <td>&gt;2_14_26_F3,-1282216.0</td>' )
        self.check_metadata_for_string( 'value="shrimp_cs_test1.csfasta" value="\?" Change data type value="csfasta" selected="yes"' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0140_upload_file( self ):
        """Test uploading megablast_xml_parser_test1.gz, NOT setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( 'megablast_xml_parser_test1.gz' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.check_history_for_string( 'NCBI Blast XML data format: <span class="blastxml">blastxml</span>' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0145_upload_file( self ):
        """Test uploading 1.axt, NOT setting the file format"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '1.axt' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.axt', hid=str( hda.hid ) )
        self.check_history_for_string( '1.axt format: <span class="axt">axt</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="1.axt" value="\?" Change data type selected value="axt" selected="yes"' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0150_upload_file( self ):
        """Test uploading 1.bam, which is a sorted Bam file creaed by the Galaxy sam_to_bam tool, NOT setting the file format"""
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '1.bam' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.bam', hid=str( hda.hid ), attributes={ 'ftype' : 'bam' } )
        self.check_history_for_string( '<span class="bam">bam</span>' )
        # Make sure the Bam index was created
        assert hda.metadata.bam_index is not None, "Bam index was not correctly created for 1.bam"
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0155_upload_file( self ):
        """Test uploading 3unsorted.bam, which is an unsorted Bam file, NOT setting the file format"""
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '3unsorted.bam' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        # Since 3unsorted.bam is not sorted, we cannot verify dataset correctness since the uploaded
        # dataset will be sorted.  However, the check below to see if the index was created is
        # sufficient.
        self.check_history_for_string( '<span class="bam">bam</span>' )
        # Make sure the Bam index was created
        assert hda.metadata.bam_index is not None, "Bam index was not correctly created for 3unsorted.bam"
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0160_url_paste( self ):
        """Test url paste behavior"""
        # Logged in as admin_user
        # Deleting the current history should have created a new history
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_url_paste( 'hello world' )
        self.check_history_for_string( 'Pasted Entry' )
        self.check_history_for_string( 'hello world' )
        self.upload_url_paste( u'hello world' )
        self.check_history_for_string( 'Pasted Entry' )
        self.check_history_for_string( 'hello world' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0165_upload_file( self ):
        """Test uploading 1.pileup, NOT setting the file format"""
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '1.pileup' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.pileup', hid=str( hda.hid ) )
        self.check_history_for_string( '1.pileup format: <span class="pileup">pileup</span>, database: \? Info: uploaded file' )
        self.check_metadata_for_string( 'value="1.pileup" value="\?" Change data type selected value="pileup" selected="yes"' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0170_upload_file( self ):
        """Test uploading 1.bigbed, NOT setting the file format"""
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '1.bigbed' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.bigbed', hid=str( hda.hid ) )
        self.check_history_for_string( '1.bigbed</span> database: \? Info: uploaded bigbed file' )
        self.check_metadata_for_string( 'value="1.bigbed" value="\?" Change data type selected value="bigbed" selected="yes"' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_0175_upload_file( self ):
        """Test uploading 1.bigwig, NOT setting the file format"""
        self.check_history_for_string( 'Your history is empty' )
        history = get_latest_history_for_user( admin_user )
        self.upload_file( '1.bigwig' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.bigwig', hid=str( hda.hid ) )
        self.check_history_for_string( '1.bigwig</span> database: \? Info: uploaded bigwig file' )
        self.check_metadata_for_string( 'value="1.bigwig" value="\?" Change data type selected value="bigwig" selected="yes"' )
        self.delete_history( id=self.security.encode_id( history.id ) )
    def test_9999_clean_up( self ):
        self.logout()
