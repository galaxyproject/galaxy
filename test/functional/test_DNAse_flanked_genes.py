import galaxy.model
from galaxy.model.orm import *
from base.twilltestcase import TwillTestCase

""" A sample analysis"""

class AnalysisDNAseHSSFlankedGenes( TwillTestCase ):
    def test_get_DNAseHSS_flanked_genes( self ):
        self.login()
        self.new_history()
        global history1
        history1 = galaxy.model.History.query() \
            .order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
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
        # Test 1
        self.run_ucsc_main( track_params, output_params )
        self.wait()
        self.verify_dataset_correctness('DNAseHSS.dat')
        latest_hda = galaxy.model.HistoryDatasetAssociation.query() \
            .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
        # Due to twill not being able to handle the permissions forms, we'll eliminate
        # DefaultHistoryPermissions prior to uploading a dataset so that the permission
        # form will not be displayed on ted edit attributes page.
        for dp in latest_hda.dataset.actions:
            dp.delete()
            dp.flush()
        latest_hda.dataset.refresh()
        self.edit_hda_attribute_info( str( latest_hda.id ), new_name="DNAse HS" )
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
        # Test 2
        self.run_ucsc_main( track_params, output_params )
        self.wait()
        self.verify_dataset_correctness('hg17chr22KnownGenes.dat')
        latest_hda = galaxy.model.HistoryDatasetAssociation.query() \
            .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
        for dp in latest_hda.dataset.actions:
            dp.delete()
            dp.flush()
        latest_hda.dataset.refresh()
        self.edit_hda_attribute_info( str( latest_hda.id ), new_name="Genes" )
        self.check_metadata_for_string( "Genes" )
        # Test 3
        self.run_tool( 'get_flanks1', input="2", region="whole", direction="Upstream", offset="0", size="500" )
        self.wait()
        self.verify_dataset_correctness( 'knownGeneUpstream500Flanks.dat' )
        latest_hda = galaxy.model.HistoryDatasetAssociation.query() \
            .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
        for dp in latest_hda.dataset.actions:
            dp.delete()
            dp.flush()
        latest_hda.dataset.refresh()
        self.edit_hda_attribute_info( str( latest_hda.id ), new_name="Flanks" )
        self.check_metadata_for_string( "Flanks" )
        # Test 4
        self.run_tool( 'gops_join_1', input1="3", input2="1", min="1", fill="none"  )
        self.wait()
        # We cannot verify this dataset, because this tool spits out data in a non-deterministic order
        #self.verify_dataset_correctness( 'joinFlanksDNAse.dat' )
        # Test 5
        self.run_tool( 'Filter1', input="4", cond="c17==1000"  )
        self.wait()
        self.verify_dataset_correctness( 'filteredJoinedFlanksDNAse.dat' )
        self.delete_history()
        self.logout()
