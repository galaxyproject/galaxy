from base.twilltestcase import TwillTestCase
from base.test_db_util import (
    get_user,
    get_latest_history_for_user,
    get_latest_hda,
)

admin_user = None


class UploadData( TwillTestCase ):

    def test_0000_setup_upload_tests( self ):
        """
        Configuring upload tests, setting admin_user
        """
        self.logout()
        self.login( email='test@bx.psu.edu' )
        global admin_user
        admin_user = get_user( email='test@bx.psu.edu' )

    def create_fresh_history( self, user ):
        """
        Deletes latest history for the given user, checks for an empty history,
        and returns that new, empty history
        """
        # in order to remove a lot of boiler plate - and not have cascading errors
        history = get_latest_history_for_user( user )
        self.delete_history( id=self.security.encode_id( history.id ) )
        self.is_history_empty()
        return get_latest_history_for_user( user )

    def test_0005_upload_file( self ):
        """
        Test uploading 1.bed, NOT setting the file format
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '1.bed' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.bed', hid=str( hda.hid ) )
        self.check_history_for_string( "<th>1.Chrom</th><th>2.Start</th><th>3.End</th>" )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0006_upload_file( self ):
        """
        Test uploading 1.bed.spaces, with space to tab selected, NOT setting the file format
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '1.bed.spaces', space_to_tab=True )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.bed', hid=str( hda.hid ) )
        self.check_history_for_string( "<th>1.Chrom</th><th>2.Start</th><th>3.End</th>" )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0010_upload_file( self ):
        """
        Test uploading 4.bed.gz, manually setting the file format
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '4.bed.gz', dbkey='hg17', ftype='bed' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '4.bed', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ),
            "peek", "<th>1.Chrom</th><th>2.Start</th><th>3.End</th>", use_string_contains=True )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0012_upload_file( self ):
        """
        Test uploading 4.bed.bz2, manually setting the file format
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '4.bed.bz2', dbkey='hg17', ftype='bed' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"

        self.verify_dataset_correctness( '4.bed', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ),
            "peek", "<th>1.Chrom</th><th>2.Start</th><th>3.End</th>", use_string_contains=True )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0015_upload_file( self ):
        """
        Test uploading 1.scf, manually setting the file format
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '1.scf', ftype='scf' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.scf', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ),
            "peek", "Binary scf sequence file", use_string_contains=True )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0020_upload_file( self ):
        """
        Test uploading 1.scf, NOT setting the file format
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '1.scf' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ),
            "misc_info", "File Format' to 'Scf' when uploading scf files", use_string_contains=True )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0025_upload_file( self ):
        """
        Test uploading 4.bed.zip, manually setting the file format
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '4.bed.zip', ftype='bed' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '4.bed', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ),
            "peek", "<th>1.Chrom</th><th>2.Start</th><th>3.End</th>", use_string_contains=True )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0030_upload_file( self ):
        """
        Test uploading 4.bed.zip, NOT setting the file format
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '4.bed.zip' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '4.bed', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ),
            "peek", "<th>1.Chrom</th><th>2.Start</th><th>3.End</th>", use_string_contains=True )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0035_upload_file( self ):
        """
        Test uploading 1.sam NOT setting the file format
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '1.sam' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.sam', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ),
            "peek", "<th>1.QNAME</th><th>2.FLAG</th><th>3.RNAME</th><th>4.POS</th>", use_string_contains=True )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0040_upload_file( self ):
        """
        Test uploading 1.sff, NOT setting the file format
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '1.sff' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.sff', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ),
            "misc_info", "sff", use_string_contains=True )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0045_upload_file( self ):
        """
        Test uploading 454Score.pdf, NOT setting the file format
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '454Score.pdf' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ),
            "name", "454Score.pdf" )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0050_upload_file( self ):
        """
        Test uploading 454Score.png, NOT setting the file format
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '454Score.png' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ),
            "name", "454Score.png" )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0055_upload_file( self ):
        """
        Test uploading lped composite datatype file, manually setting the file format
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        # lped data types include a ped_file and a map_file ( which is binary )
        self.upload_file( None, ftype='lped', metadata=[ { 'name':'base_name', 'value':'rgenetics' } ], composite_data=[ { 'name':'ped_file', 'value':'tinywga.ped' }, { 'name':'map_file', 'value':'tinywga.map'} ] )
        # Get the latest hid for testing
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        # We'll test against the resulting ped file and map file for correctness
        self.verify_composite_datatype_file_content( 'tinywga.ped', str( hda.id ), base_name='rgenetics.ped' )
        self.verify_composite_datatype_file_content( 'tinywga.map', str( hda.id ), base_name='rgenetics.map' )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ),
            "metadata_base_name", "rgenetics", use_string_contains=True )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0056_upload_file( self ):
        """
        Test uploading lped composite datatype file, manually setting the file format, and using space to tab on one file (tinywga.ped)
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        # lped data types include a ped_file and a map_file ( which is binary )
        self.upload_file( None, ftype='lped', metadata=[ { 'name':'base_name', 'value':'rgenetics' } ], composite_data=[ { 'name':'ped_file', 'value':'tinywga.ped', 'space_to_tab':True }, { 'name':'map_file', 'value':'tinywga.map'} ] )
        # Get the latest hid for testing
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        # We'll test against the resulting ped file and map file for correctness
        self.verify_composite_datatype_file_content( 'tinywga.ped.space_to_tab', str( hda.id ), base_name='rgenetics.ped' )
        self.verify_composite_datatype_file_content( 'tinywga.map', str( hda.id ), base_name='rgenetics.map' )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ),
            "metadata_base_name", "rgenetics", use_string_contains=True )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0060_upload_file( self ):
        """
        Test uploading pbed composite datatype file, manually setting the file format
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        # pbed data types include a bim_file, a bed_file and a fam_file
        self.upload_file( None, ftype='pbed',
            metadata=[ { 'name':'base_name', 'value':'rgenetics' } ],
            composite_data=[
                { 'name':'bim_file', 'value':'tinywga.bim' },
                { 'name':'bed_file', 'value':'tinywga.bed' },
                { 'name':'fam_file', 'value':'tinywga.fam' } ])
        # Get the latest hid for testing
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        # We'll test against the resulting ped file and map file for correctness
        self.verify_composite_datatype_file_content( 'tinywga.bim', str( hda.id ), base_name='rgenetics.bim' )
        self.verify_composite_datatype_file_content( 'tinywga.bed', str( hda.id ), base_name='rgenetics.bed' )
        self.verify_composite_datatype_file_content( 'tinywga.fam', str( hda.id ), base_name='rgenetics.fam' )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ),
            "metadata_base_name", "rgenetics", use_string_contains=True )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0065_upload_file( self ):
        """
        Test uploading asian_chars_1.txt, NOT setting the file format
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        self.upload_file( 'asian_chars_1.txt' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( 'asian_chars_1.txt', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ),
            "misc_info", "uploaded multi-byte char file", use_string_contains=True )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0070_upload_file( self ):
        """
        Test uploading 2gen.fastq, NOT setting the file format
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        self.upload_file( '2gen.fastq' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '2gen.fastq', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "fastq" )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0075_upload_file( self ):
        """
        Test uploading 1.wig, NOT setting the file format
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        self.upload_file( '1.wig' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.wig', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "wig" )
        self.check_metadata_for_string( 'value="1.wig" value="\?"' )
        self.check_metadata_for_string( 'Change data type selected value="wig" selected="yes"' )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0080_upload_file( self ):
        """
        Test uploading 1.tabular, NOT setting the file format
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        self.upload_file( '1.tabular' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.tabular', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "tabular" )
        self.check_metadata_for_string( 'value="1.tabular" value="\?"' )
        self.check_metadata_for_string( 'Change data type selected value="tabular" selected="yes"' )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0085_upload_file( self ):
        """
        Test uploading qualscores.qualsolid, NOT setting the file format
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        self.upload_file( 'qualscores.qualsolid' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( 'qualscores.qualsolid', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "qualsolid" )
        self.check_metadata_for_string( 'Change data type value="qualsolid" selected="yes">qualsolid' )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0090_upload_file( self ):
        """
        Test uploading qualscores.qual454, NOT setting the file format
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        self.upload_file( 'qualscores.qual454' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( 'qualscores.qual454', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "qual454" )
        self.check_metadata_for_string( 'Change data type value="qual454" selected="yes">qual454' )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0095_upload_file( self ):
        """
        Test uploading 3.maf, NOT setting the file format
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        self.upload_file( '3.maf' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '3.maf', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "maf" )
        self.check_metadata_for_string( 'value="3.maf" value="\?"' )
        self.check_metadata_for_string( 'Convert to new format <option value="interval">Convert MAF to Genomic Intervals <option value="fasta">Convert MAF to Fasta' )
        self.check_metadata_for_string( 'Change data type selected value="maf" selected="yes"' )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0100_upload_file( self ):
        """
        Test uploading 1.lav, NOT setting the file format
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        self.upload_file( '1.lav' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.lav', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "lav" )
        self.check_metadata_for_string( 'value="1.lav" value="\?"' )
        self.check_metadata_for_string( 'Change data type selected value="lav" selected="yes"' )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0105_upload_file( self ):
        """
        Test uploading 1.interval, NOT setting the file format
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        self.upload_file( '1.interval' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.interval', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "interval" )
        self.check_metadata_for_string( 'value="1.interval" value="\?"' )
        self.check_metadata_for_string( 'Chrom column: <option value="1" selected> Start column: <option value="2" selected>' )
        self.check_metadata_for_string( 'End column: <option value="3" selected> Strand column <option value="6" selected>' )
        self.check_metadata_for_string( 'Convert to new format <option value="bed">Convert Genomic Intervals To BED' )
        self.check_metadata_for_string( 'Change data type selected value="interval" selected="yes"' )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0110_upload_file( self ):
        """
        Test uploading 5.gff3, NOT setting the file format
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        self.upload_file( '5.gff3' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '5.gff3', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "gff3" )
        self.check_metadata_for_string( 'value="5.gff3" value="\?"' )
        self.check_metadata_for_string( 'Convert to new format <option value="bed">Convert GFF to BED' )
        self.check_metadata_for_string( 'Change data type selected value="gff3" selected="yes"' )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0115_upload_file( self ):
        """
        Test uploading html_file.txt, NOT setting the file format
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        self.upload_file( 'html_file.txt' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ),
            "misc_info", "The uploaded file contains inappropriate HTML content", use_string_contains=True )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0120_upload_file( self ):
        """
        Test uploading 5.gff, NOT setting the file format

        Test sniffer for gff.
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '5.gff' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '5.gff', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "gff" )
        self.check_metadata_for_string( 'value="5.gff" value="\?"' )
        self.check_metadata_for_string( 'Convert to new format <option value="bed">Convert GFF to BED' )
        self.check_metadata_for_string( 'Change data type selected value="gff" selected="yes"' )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0125_upload_file( self ):
        """
        Test uploading 1.fasta, NOT setting the file format
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        self.upload_file( '1.fasta' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.fasta', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "fasta" )
        self.check_metadata_for_string( 'value="1.fasta" value="\?" Change data type selected value="fasta" selected="yes"' )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0130_upload_file( self ):
        """
        Test uploading 1.customtrack, NOT setting the file format
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        self.upload_file( '1.customtrack' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.customtrack', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "customtrack" )
        self.check_metadata_for_string( 'value="1.customtrack" value="\?" Change data type selected value="customtrack" selected="yes"' )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0135_upload_file( self ):
        """
        Test uploading shrimp_cs_test1.csfasta, NOT setting the file format
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        self.upload_file( 'shrimp_cs_test1.csfasta' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( 'shrimp_cs_test1.csfasta', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "csfasta" )
        self.check_metadata_for_string( 'value="shrimp_cs_test1.csfasta" value="\?" Change data type value="csfasta" selected="yes"' )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0145_upload_file( self ):
        """
        Test uploading 1.axt, NOT setting the file format
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        self.upload_file( '1.axt' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.axt', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "axt" )
        self.check_metadata_for_string( 'value="1.axt" value="\?" Change data type selected value="axt" selected="yes"' )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0150_upload_file( self ):
        """
        Test uploading 1.bam, which is a sorted Bam file creaed by the Galaxy sam_to_bam tool, NOT setting the file format
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '1.bam' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.bam', hid=str( hda.hid ), attributes={ 'ftype' : 'bam' } )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "bam" )
        # Make sure the Bam index was created
        assert hda.metadata.bam_index is not None, "Bam index was not correctly created for 1.bam"

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0155_upload_file( self ):
        """
        Test uploading 3unsorted.bam, which is an unsorted Bam file, NOT setting the file format
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '3unsorted.bam' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        # Since 3unsorted.bam is not sorted, we cannot verify dataset correctness since the uploaded
        # dataset will be sorted.  However, the check below to see if the index was created is
        # sufficient.
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "bam" )
        # Make sure the Bam index was created
        assert hda.metadata.bam_index is not None, "Bam index was not correctly created for 3unsorted.bam"

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0160_url_paste( self ):
        """
        Test url paste behavior
        """
        # Logged in as admin_user
        history = self.create_fresh_history( admin_user )

        self.upload_url_paste( 'hello world' )
        self.check_history_for_exact_string( 'Pasted Entry' )
        self.check_history_for_exact_string( 'hello world' )
        self.upload_url_paste( u'hello world' )
        self.check_history_for_exact_string( 'Pasted Entry' )
        self.check_history_for_exact_string( 'hello world' )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0165_upload_file( self ):
        """
        Test uploading 1.pileup, NOT setting the file format
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '1.pileup' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.pileup', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "pileup" )
        self.check_metadata_for_string( 'value="1.pileup" value="\?" Change data type selected value="pileup" selected="yes"' )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0170_upload_file( self ):
        """
        Test uploading 1.bigbed, NOT setting the file format
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '1.bigbed' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.bigbed', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "bigbed" )
        self.check_metadata_for_string( 'value="1.bigbed" value="\?" Change data type selected value="bigbed" selected="yes"' )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_0175_upload_file( self ):
        """
        Test uploading 1.bigwig, NOT setting the file format
        """
        history = self.create_fresh_history( admin_user )

        self.upload_file( '1.bigwig' )
        hda = get_latest_hda()
        assert hda is not None, "Problem retrieving hda from database"
        self.verify_dataset_correctness( '1.bigwig', hid=str( hda.hid ) )
        self.check_hda_json_for_key_value( self.security.encode_id( hda.id ), "data_type", "bigwig" )
        self.check_metadata_for_string( 'value="1.bigwig" value="\?" Change data type selected value="bigwig" selected="yes"' )

        self.delete_history( id=self.security.encode_id( history.id ) )

    def test_9999_clean_up( self ):
        self.logout()
