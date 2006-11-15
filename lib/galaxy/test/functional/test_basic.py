from galaxy.test.base.twilltestcase import TwillTestCase

class BasicFunctions(TwillTestCase):
    
    def test_init(self):
        """Testing home page"""
        self.home()

    def test_single_upload(self):
        """Testing single upload"""
        self.clear_history()
        self.upload_file('1.bed')

    def test_multi_upload(self):
        """Checking data for multiple uploads"""
        self.clear_history()
        self.upload_file('1.bed')
        self.check_data('1.bed')
        
        self.upload_file('2.bed', dbkey='hg17')
        self.check_data('2.bed')

        self.upload_file('3.bed', dbkey='hg17', ftype='bed')
        self.check_data('3.bed')
        self.clear_history()
    
    def test_edit(self):
        """Testing metadata editing"""
        self.clear_history()
        self.upload_file('1.bed', dbkey='hg15')
        self.check_history('hg15 bed')
        
        self.edit_data(hid=1, dbkey='hg16', name='Testdata')
        self.check_history('hg16 Testdata bed')
        
        # test switching types
        self.edit_data(hid=1, dbkey='hg16', chromCol='')
        self.check_history('hg16 Testdata tabular')
        
        self.edit_data(hid=1, dbkey='hg15', chromCol='1', info='foo')
        self.check_history('hg15 Testdata interval foo')

    def test_delete(self):
        """Testing individual deletes"""
        self.clear_history()
        self.upload_file('1.bed', dbkey='hg15')
        self.check_history('hg15 bed')
        self.assertEqual ( len(self.get_data_list()), 1)
        self.delete_data(1)
        self.check_history("Your history is empty")
        self.assertEqual ( len(self.get_data_list()), 0)
