from base.twilltestcase import TwillTestCase
#from twilltestcase import TwillTestCase

class FilterTests(TwillTestCase):
    
    def test_00_first(self): # will run first due to its name
        """3E_Filter: Clearing history"""
        self.clear_history()

#    def test_10_Genes(self):
#        """3E_Filter: Get UCSC known genes first(encode)"""
#        self.run_tool('ucsc_proxy')
#        params = dict(
#            hgta_regionType="encode",
#            hgta_outputType="bed",
#        )
#        self.submit_form(1, button="hgta_doTopSubmit", **params)
#        self.submit_form(1, button="hgta_doGetBed")
#        self.wait()
#        self.check_data('sc_3E_Genes.bed', hid=1)

    def test_10_upload(self):
        """3E_Filter: Get UCSC known genes first(encode)"""
        self.clear_history()
        self.upload_file('7.bed')
        self.check_data('sc_3E_Genes.bed', hid=1)


    def test_11_Filter1(self):
        """3E_Filter: Filter on condition"""
        self.run_tool("Filter1", cond="c1=='chr1' and c3-c2>=2000 and c6=='+'", input="7.bed")
        self.wait()
        self.check_data('sc_3E_filter.bed', hid=2)

    def test_21_Sort1(self):
        """3E_Filter: Sort on column one"""
        self.run_tool("sort1", input="7.bed")
        self.submit_form(1, column="1", order="ASC", style="alpha")
        self.wait()
        self.check_data('sc_3E_sort.bed')

    def test_31_select(self):
        """3E_Filter: Select on the pattern AY143171"""
        self.run_tool("Grep1", input="7.bed", invert="false", pattern="AY143171")
        self.wait()
        self.check_data('sc_3E_select.bed')

#    def test_40_knownToEnsembl(self):
#        """3E_Filter: Get UCSC knownToEnsembl"""
#        self.delete_data(4)
#        self.run_tool('ucsc_proxy')
#        params = dict(
#            hgta_table="knownToEnsembl",
#            hgta_regionType="genome",
#            hgta_outputType="primaryTable",
#        )
#        self.submit_form(1, button="hgta_doTopSubmit", **params)
#        self.wait()
#        self.check_data('sc_3E_knownToEnsembl.bed')

    def test_40_upload(self):
        """3E_Filter: Get UCSC knownToEnsembl"""
        self.upload_file('8.bed')
        self.check_data('sc_3E_knownToEnsembl.bed')

    def test_51_join1(self):
        """3E_Filter: Join UCSC knowntoEnsembl to UCSC knowngenes"""
        self.run_tool('join1', input1="7.bed", input2="8.bed")
        params = dict(
            field1="4",
            field2="1",
        )
        self.submit_form(1, button='runtool_btn', **params)
        self.wait()
        self.check_data('sc_3E_join.bed')

    def test_61_compare1(self):
        """3E_Filter: Compare two queries: knowntoEnsembl and knowngenes"""
#        self.delete_data(6)
        self.run_tool('comp1', input1="8.bed", input2="7.bed")
        params = dict(
            field1="1",
            field2="4",
            mode="N",
        )
        self.submit_form(1, button='runtool_btn', **params)
        self.wait()
        self.check_data('sc_3E_compare.bed')
