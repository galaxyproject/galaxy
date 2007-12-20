from base.twilltestcase import TwillTestCase

""" Tests are executed in order, sorted by name"""

class UploadData( TwillTestCase ):

    def test_00_multi_upload( self ):
        """test_get_data.test_multi_upload: Testing multiple uploads"""
        self.login()
        self.upload_file('1.bed')
        self.verify_dataset_correctness('1.bed')
        self.upload_file('2.bed', dbkey='hg17')
        self.verify_dataset_correctness('2.bed')
        self.upload_file('3.bed', dbkey='hg17', ftype='bed')
        self.verify_dataset_correctness('3.bed')
        self.upload_file('4.bed.gz', dbkey='hg17', ftype='bed')
        self.verify_dataset_correctness('4.bed')
        self.upload_file('1.scf', ftype='scf')
        self.verify_dataset_correctness('1.scf')
        self.upload_file('1.scf.zip', ftype='binseq.zip')
        self.verify_dataset_correctness('1.scf.zip')
        self.delete_history_item( 1 )
        self.delete_history_item( 2 )
        self.delete_history_item( 3 )
        self.delete_history_item( 4 )
        self.delete_history_item( 5 )
        self.delete_history_item( 6 )
    def test_9999_clean_up( self ):
        self.delete_history()
        self.logout()

class GetEncodeData( TwillTestCase ):
    
    def test_00_get_encode_data( self ):
        """test_get_data.test_get_encode_data"""
        self.login()
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
        self.delete_history_item( 1 )
        self.delete_history_item( 2 )
    def test_9999_clean_up( self ):
        self.delete_history()
        self.logout()

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
