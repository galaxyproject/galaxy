from base.twilltestcase import TwillTestCase

""" A sample analysis"""



class AnalysisDNAseHSSFlankedGenes( TwillTestCase ):
    
    def test_get_DNAseHSS_flanked_genes( self ):
        self.login()
        
        self.new_history()
    
        track_params = dict(
            db="hg17",
            hgta_group="regulation",
            hgta_table="dukeDnaseCd4Sites",
            hgta_track="dukeDnaseCd4Sites",
            hgta_regionType="range",
            position="chr22",
            hgta_outputType="bed",
            sendToGalaxy="1"
        )
        output_params = dict(
            fbQual="whole",
        )
        
        self.run_ucsc_main( track_params, output_params )
        self.wait()
        self.verify_dataset_correctness('DNAseHSS.dat')
        
        self.edit_metadata( name="DNAse HS" )
        self.check_metadata_for_string( "DNAse HS" )
        
        track_params = dict(
            db="hg17",
            hgta_group="genes",
            hgta_table="knownGene",
            hgta_track="knownGene",
            hgta_regionType="range",
            position="chr22",
            hgta_outputType="bed",
            sendToGalaxy="1"
        )
        output_params = dict(
            fbQual="whole",
        )
        
        self.run_ucsc_main( track_params, output_params )
        self.wait()
        self.verify_dataset_correctness('hg17chr22KnownGenes.dat')
        
        self.edit_metadata( name="Genes" )
        self.check_metadata_for_string( "Genes" )
        
        
        self.run_tool( 'get_flanks1', input="2", region="whole", direction="Upstream", offset="0", size="500" )
        self.wait()
        self.verify_dataset_correctness( 'knownGeneUpstream500Flanks.dat' )
        
        self.edit_metadata( name="Flanks" )
        self.check_metadata_for_string( "Flanks" )
        
        
        self.run_tool( 'gops_join_1', input1="3", input2="1", min="1", fill="none"  )
        self.wait()
        #self.verify_dataset_correctness( 'joinFlanksDNAse.dat' ) #we cannot verify this dataset, because this tool spits out data in a non-deterministic order
        
        
        self.run_tool( 'Filter1', input="4", cond="c17==1000"  )
        self.wait()
        self.verify_dataset_correctness( 'filteredJoinedFlanksDNAse.dat' )
        
        
        self.delete_history()
        self.logout()
        
        
        
