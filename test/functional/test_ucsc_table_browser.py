from base import test_db_util
from base.twilltestcase import TwillTestCase

""" A sample analysis"""


class UCSCMain( TwillTestCase ):

    def test_0000_create_users( self ):
        self.logout()
        self.login( email='test@bx.psu.edu' )
        admin_user = test_db_util.get_user( 'test@bx.psu.edu' )
        assert admin_user is not None, 'Problem retrieving user with email "test@bx.psu.edu" from the database'
    
    def test_0005_get_mm10_5HTT_sequence( self ):
        self.logout()
        self.login( email='test@bx.psu.edu' )
        admin_user = test_db_util.get_user( 'test@bx.psu.edu' )
        self.new_history( name='UCSC_Main' )
        track_params = dict(
            db="mm10",
            hgta_group="genes",
            hgta_table="knownGene",
            hgta_track="knownGene",
            hgta_regionType="range",
            position="chr5:34761740-34912521",
            hgta_outputType="sequence",
            sendToGalaxy="1"
        )
        output_params = dict(
            fbQual="whole",
        )
        self.run_ucsc_main( track_params, output_params )
        self.wait()
        self.verify_dataset_correctness( 'GRCm38mm10_chr5_34761740-34912521.fa' )
