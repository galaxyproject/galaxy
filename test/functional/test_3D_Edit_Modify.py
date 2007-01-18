from base.twilltestcase import TwillTestCase
#from twilltestcase import TwillTestCase

class EditModifyTests(TwillTestCase):
    
    def test_00_first(self): # will run first due to its name
        """3D_Edit_Modify: Clearing history"""
        self.clear_history()

    def test_10_Encode_cds(self):
        """3D_Edit_Modify: Get Encode CDs first"""
        self.clear_history()

        self.run_tool('encode_import_gencode1', hg17=['gencode.CDS.20051206.bed'])
        self.wait()
        self.check_data('sc_3D_cds.bed', hid=1)

    def test_11_Add_column_1(self):
        """3D_Edit_Modify: Add value 1 to cds"""
        self.run_tool("addValue", exp="1", iterate="no")
        self.wait()
        self.check_data('sc_3D_cds_add_1.bed', hid=2)

    def test_12_Add_column_Mycds(self):
        """3D_Edit_Modify: Add value 'My.cds' to cds"""
        self.delete_data(2)
        self.run_tool("addValue", exp="My.cds", iterate="no")
        self.wait()
        self.check_data('sc_3D_cds_add_mycds.bed', hid=3)

    def test_21_compute1(self):
        """3D_Edit_Modify: Compute expression c3-c2"""
        self.delete_data(3)
        self.run_tool('Add a column1', cond='c3-c2')
        self.wait()
        self.check_data('sc_3D_cds_compute1.bed', hid=4)

    def test_22_compute2(self):
        """3D_Edit_Modify: Compute expression(c3-c2)*100"""
        self.delete_data(4)
        self.run_tool('Add a column1', cond='(c3-c2)*100')
        self.wait()
        self.check_data('sc_3D_cds_compute2.bed', hid=5)

    def test_30_concatenate(self):
        """3D_Edit_Modify: Concatenate cd and cds"""
        self.delete_data(5)
        self.run_tool('cat1')
        self.wait()
        self.check_data('sc_3D_cds_concat.bed', hid=6)

    def test_40_create_single_interval(self):
        """3D_Edit_Modify: Create single interval"""
        self.delete_data(6)
        self.run_tool('createInterval', chrom='chr7', start='100', end='1000', name='myInterval', strand='plus')
        self.wait()
        self.check_data('sc_3D_cds_createInterval.bed', hid=7)

    def test_50_cut(self):
        """3D_Edit_Modify: cut c1, c2"""
        self.delete_data(7)
        self.run_tool('Cut1', columnList='c1,c2', delimiter='T')
        self.wait()
        self.check_data('sc_3D_cds_cut.bed', hid=8)

    def test_60_paste(self):
        """3D_Edit_Modify: paste"""
        self.delete_data(8)
        self.run_tool('Paste1', delimiter='T')
        self.wait()
        self.check_data('sc_3D_cds_paste.bed', hid=9)
        self.delete_data(9)
