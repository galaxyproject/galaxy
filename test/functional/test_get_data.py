from base.twilltestcase import TwillTestCase

""" The numbering of the tests is essential as they will be executed in order, sorted by name"""

class UploadData( TwillTestCase ):

    def test_upload( self ):
        """test_get_data.test_upload: Testing single upload"""
        self.new_history()
        self.upload_file('MyData.bed')
        self.check_data('MyData.bed', hid=1)
        self.check_genome_build('hg17')
        self.new_history()
        self.upload_file('7.bed')
        self.check_data('sc_3E_Genes.bed', hid=1)
        self.new_history()
        self.upload_file('8.bed', ftype='bed')
        self.check_data('sc_3E_knownToEnsembl.bed', hid=1)
    def test_30_multi_upload(self):
        """test_get_data.test_multi_upload: Testing multiple uploads"""
        self.new_history()
        self.upload_file('1.bed')
        self.check_data('1.bed', hid=1)
        self.upload_file('2.bed', dbkey='hg17')
        self.check_data('2.bed', hid=2)
        self.upload_file('3.bed', dbkey='hg17', ftype='bed')
        self.check_data('3.bed', hid=3)

class GetEncodeData( TwillTestCase ):
    
    def test_get_encode_data( self ):
        """test_get_data.test_get_encode_data"""
        self.new_history()
        self.run_tool('encode_import_chromatin_and_chromosomes1', hg17=['cc.EarlyRepSeg.20051216.bed'] )
        #hg17=[ "cc.EarlyRepSeg.20051216.bed", "cc.EarlyRepSeg.20051216.gencode_partitioned.bed", "cc.LateRepSeg.20051216.bed", "cc.LateRepSeg.20051216.gencode_partitioned.bed", "cc.MidRepSeg.20051216.bed", "cc.MidRepSeg.20051216.gencode_partitioned.bed" ] )
        self.wait()
        self.check_data('cc.EarlyRepSeg.20051216.bed', hid=1)
        #self.check_data('cc.EarlyRepSeg.20051216.gencode_partitioned.bed', hid=2)
        #self.check_data('cc.LateRepSeg.20051216.bed', hid=3)
        #self.check_data('cc.LateRepSeg.20051216.gencode_partitioned.bed', hid=4)
        #self.check_data('cc.MidRepSeg.20051216.bed', hid=5)
        #self.check_data('cc.MidRepSeg.20051216.gencode_partitioned.bed', hid=6)
        self.run_tool('encode_import_gencode1', hg17=['gencode.CDS.20051206.bed'])
        self.wait()
        self.check_data('sc_3D_cds.bed', hid=2)
        
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
    #    self.check_data('hbvar_hybrid_genes.dat')
    pass
