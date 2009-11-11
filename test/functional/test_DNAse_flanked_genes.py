import galaxy.model
from galaxy.model.orm import *
from galaxy.model.mapping import context as sa_session
from base.twilltestcase import TwillTestCase

""" A sample analysis"""

class AnalysisDNAseHSSFlankedGenes( TwillTestCase ):
    def test_get_DNAseHSS_flanked_genes( self ):
        self.logout()
        self.login( email='test@bx.psu.edu' )
        admin_user = sa_session.query( galaxy.model.User ) \
                               .filter( galaxy.model.User.table.c.email=='test@bx.psu.edu' ) \
                               .one()
        self.new_history( name='DNAseHSS_flanked_genes' )
        history1 = sa_session.query( galaxy.model.History ) \
                             .filter( and_( galaxy.model.History.table.c.deleted==False,
                                            galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                             .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                             .first()
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
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        # Due to twill not being able to handle the permissions forms, we'll eliminate
        # DefaultHistoryPermissions prior to uploading a dataset so that the permission
        # form will not be displayed on ted edit attributes page.
        for dp in latest_hda.dataset.actions:
            sa_session.delete( dp )
            sa_session.flush()
        sa_session.refresh( latest_hda.dataset )
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
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        for dp in latest_hda.dataset.actions:
            sa_session.delete( dp )
            sa_session.flush()
        sa_session.refresh( latest_hda.dataset )
        self.edit_hda_attribute_info( str( latest_hda.id ), new_name="Genes" )
        self.check_metadata_for_string( "Genes" )
        # Test 3
        self.run_tool( 'get_flanks1', input="2", region="whole", direction="Upstream", offset="0", size="500" )
        self.wait()
        self.verify_dataset_correctness( 'knownGeneUpstream500Flanks.dat' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        for dp in latest_hda.dataset.actions:
            sa_session.delete( dp )
            sa_session.flush()
        sa_session.refresh( latest_hda.dataset )
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
        self.delete_history( self.security.encode_id( history1.id ) )
        self.logout()
