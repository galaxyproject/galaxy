from galaxy.test.base.twilltestcase import TwillTestCase
#from twilltestcase import TwillTestCase

class EncodeTests(TwillTestCase):
    
    def test_00_first(self): # will run first due to its name
        """3B_GetEncodeData: Clearing history"""
        self.clear_history()

    def test_10_Encode_Data(self):
        """3B_GetEncodeData: Getting encode data"""

        self.run_tool('encode_import_chromatin_and_chromosomes1', hg17=['cc.EarlyRepSeg.20051216.bed'] )
#	hg17=[ "cc.EarlyRepSeg.20051216.bed", "cc.EarlyRepSeg.20051216.gencode_partitioned.bed", "cc.LateRepSeg.20051216.bed", "cc.LateRepSeg.20051216.gencode_partitioned.bed", "cc.MidRepSeg.20051216.bed", "cc.MidRepSeg.20051216.gencode_partitioned.bed" ] )
        
        self.wait()
        self.check_data('cc.EarlyRepSeg.20051216.bed', hid=1)
#        self.check_data('cc.EarlyRepSeg.20051216.gencode_partitioned.bed', hid=2)
#        self.check_data('cc.LateRepSeg.20051216.bed', hid=3)
#        self.check_data('cc.LateRepSeg.20051216.gencode_partitioned.bed', hid=4)
#        self.check_data('cc.MidRepSeg.20051216.bed', hid=5)
#        self.check_data('cc.MidRepSeg.20051216.gencode_partitioned.bed', hid=6)

