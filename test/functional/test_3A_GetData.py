from base.twilltestcase import TwillTestCase
#from twilltestcase import TwillTestCase

class UcscTests(TwillTestCase):
    
    def test_00_first(self): # will run first due to its name
        """3A_GetData: Clearing history"""
        self.clear_history()

    def test_10_upload(self):
        """3A_GetData: Testing single upload"""
        self.clear_history()

        self.upload_file('MyData.bed')
        self.check_data('MyData.bed', hid=1)
        self.check_genome_build()

    #def test_20_UCSC_bed(self):
    #    """3A_GetData: Getting bed files from UCSC"""
    #    self.clear_history()
    #
    #    self.run_tool('ucsc_proxy')
    #    params = dict(
    #        hgta_regionType="range",
    #        hgta_outputType="bed",
    #    )
    #    self.submit_form(1, button="hgta_doTopSubmit", **params)
    #    self.submit_form(1, button="hgta_doGetBed" )
    #    self.wait()
    #    self.check_data('3A_GetData_ucsc_bed_range.dat', hid=1)
    #
    # def test_30_Biomart_Uniprot(self):
    #     """3A_GetData: Connection to Biomart"""
    #     #All this test does, is check to see if biomart is accessible through Galaxy. A dataset is never retrieved or checked.
    # 
    #     # some button indices are hardcoded (twill limitation)
    #     self.run_tool('biomart')
    #     
    #     self.submit_form(form='mainform', button='get_count_button', 
    #         dataBase='default____UNIPROT PROTOTYPE 4-5  (EBI)', dataset='uniprot'
    #     )
    #     
    #     #self.submit_form(form='settings', button='stage_filter', 
    #     #    database='UNIPROTPROTOTYPE4-5(EBI)__default', dataset='uniprot'
    #     #)
    #     
    #     #self.submit_form(form='settings', button=6, 
    #     #    uniprot_collection_start=1, uniprot_collection_end=1,
    #     #    uniprot_component_start=1000, uniprot_component_end=2000
    #     #)
    #     
    #     #self.submit_form(form='settings', button=5, 
    #     #    outtype='Features', outformat='tsv'
    #     #)
    #     
    #     #self.check_data('biomart_uniprot.dat')

