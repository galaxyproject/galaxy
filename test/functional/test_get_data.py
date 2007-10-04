from base.twilltestcase import TwillTestCase

""" Tests are executed in order, sorted by name"""

class UploadData( TwillTestCase ):

    def test_upload( self ):
        """test_get_data.test_upload: Testing single upload"""
        self.new_history()
        self.upload_file('MyData.bed',ftype='auto', dbkey='hg18')
        self.verify_dataset_correctness('MyData.bed', hid=1)
        self.verify_genome_build(dbkey='hg18')
    def test_multi_upload(self):
        """test_get_data.test_multi_upload: Testing multiple uploads"""
        self.new_history()
        self.upload_file('1.bed')
        self.verify_dataset_correctness('1.bed', hid=1)
        self.upload_file('2.bed', dbkey='hg17')
        self.verify_dataset_correctness('2.bed', hid=2)
        self.upload_file('3.bed', dbkey='hg17', ftype='bed')
        self.verify_dataset_correctness('3.bed', hid=3)

class GetEncodeData( TwillTestCase ):
    
    def test_get_encode_data( self ):
        """test_get_data.test_get_encode_data"""
        self.new_history()
        self.run_tool('encode_import_chromatin_and_chromosomes1', hg17=['cc.EarlyRepSeg.20051216.bed'] )
        #hg17=[ "cc.EarlyRepSeg.20051216.bed", "cc.EarlyRepSeg.20051216.gencode_partitioned.bed", "cc.LateRepSeg.20051216.bed", "cc.LateRepSeg.20051216.gencode_partitioned.bed", "cc.MidRepSeg.20051216.bed", "cc.MidRepSeg.20051216.gencode_partitioned.bed" ] )
        self.wait()
        self.verify_dataset_correctness('cc.EarlyRepSeg.20051216.bed', hid=1)
        #self.verify_dataset_correctness('cc.EarlyRepSeg.20051216.gencode_partitioned.bed', hid=2)
        #self.verify_dataset_correctness('cc.LateRepSeg.20051216.bed', hid=3)
        #self.verify_dataset_correctness('cc.LateRepSeg.20051216.gencode_partitioned.bed', hid=4)
        #self.verify_dataset_correctness('cc.MidRepSeg.20051216.bed', hid=5)
        #self.verify_dataset_correctness('cc.MidRepSeg.20051216.gencode_partitioned.bed', hid=6)
        self.run_tool('encode_import_gencode1', hg17=['gencode.CDS.20051206.bed'])
        self.wait()
        self.verify_dataset_correctness('sc_3D_cds.bed', hid=2)
        
class DataSources( TwillTestCase ):

    #def test_hbvar(self):
    #    """Getting hybrid gene mutations from HbVar"""
    #    #self.load_cookies("hbvar_cookie.txt")
    #    self.clear_history()
    #    self.run_tool('hbvar')
    #    params = dict(
    #        htyp="any hybrid gene",
    #    )
    #    self.submit_form(form=1, button="Submit Query", **params)
    #    params = dict(
    #        display_format="galaxy",
    #    )
    #    self.submit_form(form=1, button="Go", **params)
    #    params = dict(
    #        build="hg17",
    #    )
    #    self.submit_form(form=1, button="ok", **params);
    #    """
    #    TODO: Currently fails when using sqlite, although successful when
    #    using Postgres.  Upgrading our version of sqlite may fix this, but
    #    confirmation is required.
    #    """
    #    self.verify_dataset_correctness('hbvar_hybrid_genes.dat')
    pass
