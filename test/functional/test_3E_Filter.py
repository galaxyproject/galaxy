from base.twilltestcase import TwillTestCase
#from twilltestcase import TwillTestCase

class FilterTests(TwillTestCase):
    
    def test_00_first(self): # will run first due to its name
        """3E_Filter: Clearing history"""
        self.clear_history()

    def test_10_Genes(self):
        """3E_Filter: Get UCSC known genes first(encode)"""
        self.run_tool('ucsc_proxy')
        params = dict(
            hgta_regionType="encode",
            hgta_outputType="bed",
        )
        self.submit_form(1, button="hgta_doTopSubmit", **params)
        self.submit_form(1, button="hgta_doGetBed")
        self.wait()
        self.check_data('sc_3E_Genes.bed', hid=1)

    def test_11_Filter1(self):
        """3E_Filter: Filter on condition"""
        self.run_tool("Filter1", cond="c1=='chr1' and c3-c2>=2000 and c6=='+'")
        self.wait()
        self.check_data('sc_3E_filter.bed', hid=2)

    def test_21_Sort1(self):
        """3E_Filter: Sort on column one"""
        self.delete_data(2)
        self.run_tool("sort1", input=1, column="1", order="ASC", style="alpha")
        self.wait()
        self.check_data('sc_3E_sort.bed', hid=3)

    def test_31_select(self):
        """3E_Filter: Select on the pattern AY143171"""
        self.delete_data(3)
        self.run_tool("Grep1", input=1, invert="false", pattern="AY143171")
        self.wait()
        self.check_data('sc_3E_select.bed', hid=4)

    def test_40_knownToEnsembl(self):
        """3E_Filter: Get UCSC knownToEnsembl"""
        self.delete_data(4)
        self.run_tool('ucsc_proxy')
        params = dict(
            hgta_table="knownToEnsembl",
            hgta_regionType="genome",
            hgta_outputType="primaryTable",
        )
        self.submit_form(1, button="hgta_doTopSubmit", **params)
        self.wait()
        self.check_data('sc_3E_knownToEnsembl.bed', hid=5)

    def test_51_join1(self):
        """3E_Filter: Join UCSC knowntoEnsembl to UCSC knowngenes"""
        self.run_tool('join1', input1=1, input2=5)
        params = dict(
            field1="4",
            field2="1",
        )
        self.submit_form(1, button='runtool_btn', **params)
        self.wait()
        self.check_data('sc_3E_join.bed', hid=6)

    def test_61_compare1(self):
        """3E_Filter: Compare two queries: knowntoEnsembl and knowngenes"""
        self.delete_data(6)
        self.run_tool('comp1', input1=5, input2=1)
        params = dict(
            field1="1",
            field2="4",
            mode="N",
        )
        self.submit_form(1, button='runtool_btn', **params)
        self.wait()
        self.check_data('sc_3E_compare.bed', hid=7)
