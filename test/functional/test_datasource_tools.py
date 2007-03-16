import os
from base.twilltestcase import TwillTestCase

class UcscTests(TwillTestCase):
    
    def test_00_first(self): # will run first due to its name
        """Clearing history"""
        self.clear_history()

    # def test_Biomart_Uniprot(self):
    #     """Connection to Biomart"""
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

    # def test_UCSC_interface(self):
    #     """Diffing first page of UCSC proxy."""
    #     # hgsid needs to be set or else we get a different one every time.
    #     self.go2myurl("http://www.genome.ucsc.edu/cgi-bin/hgTables?org=Human&db=hg18&hgsid=84962660&hgta_doMainPage=1")
    #     current_file = self.get_fname('new_ucsc_proxy_page.dat')
    #     diff_file = self.get_fname('ucsc_proxy_page.dat')
    #     
    #     currentpage = self.last_page()
    #     file(current_file, 'wb').write(currentpage)
    # 
    #     try:
    #         self.diff( current_file, diff_file )
    #         os.remove( current_file )
    #     except AssertionError, err:
    #         raise AssertionError( "UCSC Page has changed:\n" + str( err ) )
    # 
    #     # Note that execution will not reach this if there is an
    #     # error.  This is intended so that the new ucsc page will be
    #     # stored and can be easily checked by hand and updated.
     
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

    def test_hbvar(self):
        """Getting hybrid gene mutations from HbVar"""

        self.load_cookies("hbvar_cookie.txt")
        self.clear_history()

        self.run_tool('hbvar')
        params = dict(
            htyp="any hybrid gene",
        )
        self.submit_form(form=1, button="Submit Query", **params)
        
        params = dict(
            display_format="galaxy",
        )
        self.submit_form(form=1, button="Go", **params)
        
        params = dict(
            build="hg17",
        )
        self.submit_form(form=1, button="ok", **params);

        """
        TODO: Currently fails when using sqlite, although successful when
        using Postgres.  Upgrading our version of sqlite may fix this, but
        confirmation is required.
        """
        self.check_data('hbvar_hybrid_genes.dat')

