from base.twilltestcase import TwillTestCase

class UcscTests(TwillTestCase):
    
    def test_00_first(self): # will run first due to its name
        """Clearing history"""
        self.clear_history()

    def test_Biomart_Uniprot(self):
        """Connection to Biomart"""

        # some button indices are hardcoded (twill limitation)
        self.run_tool('biomart')
        
        self.submit_form(form='settings', button='stage_filter', 
            database='UNIPROTPROTOTYPE4-5(EBI)__default', dataset='uniprot'
        )
        
        self.submit_form(form='settings', button=6, 
            uniprot_collection_start=1, uniprot_collection_end=1,
            uniprot_component_start=1000, uniprot_component_end=2000
        )
        
        #self.submit_form(form='settings', button=5, 
        #    outtype='Features', outformat='tsv'
        #)
        
        #self.check_data('biomart_uniprot.dat')

    
    def test_UCSC_bed(self):
        """Getting bed files from UCSC"""

        self.clear_history()

        # in range
        self.run_tool('ucsc_proxy')
        params = dict(
            hgta_regionType="range",
            hgta_outputType="primaryTable",
        )
        self.submit_form(1, button="hgta_doTopSubmit", **params)

        # encode
        self.run_tool('ucsc_proxy')
        params = dict(
            hgta_regionType="encode",
            hgta_outputType="primaryTable",
        )
        self.submit_form(1, button="hgta_doTopSubmit", **params)
        
        self.wait()
        
        self.check_data('ucsc_proxy_range.dat', hid=1)
        self.check_data('ucsc_proxy_encode.dat', hid=2)

