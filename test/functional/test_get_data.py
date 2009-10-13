import galaxy.model
from galaxy.model.orm import *
from base.twilltestcase import TwillTestCase

class UploadData( TwillTestCase ):
    def test_000_upload_files_from_disk( self ):
        """Test uploading data files from disk"""
        self.logout()
        self.login( email='test@bx.psu.edu' )
        global admin_user
        admin_user = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test@bx.psu.edu' ).one()
        history1 = galaxy.model.History.filter( and_( galaxy.model.History.table.c.deleted==False,
                                                      galaxy.model.History.table.c.user_id==admin_user.id ) ) \
            .order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        self.upload_file( '1.bed' )
        hda1 = galaxy.model.HistoryDatasetAssociation.query() \
            .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
        assert hda1 is not None, "Problem retrieving hda1 from database"
        self.verify_dataset_correctness( '1.bed', hid=str( hda1.hid ) )
        self.upload_file( '2.bed', dbkey='hg17' )
        hda2 = galaxy.model.HistoryDatasetAssociation.query() \
            .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
        assert hda2 is not None, "Problem retrieving hda2 from database"
        self.verify_dataset_correctness( '2.bed', hid=str( hda2.hid ) )
        self.upload_file( '3.bed', dbkey='hg17', ftype='bed' )
        hda3 = galaxy.model.HistoryDatasetAssociation.query() \
            .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
        assert hda3 is not None, "Problem retrieving hda3 from database"
        self.verify_dataset_correctness( '3.bed', hid=str( hda3.hid ) )
        self.upload_file( '4.bed.gz', dbkey='hg17', ftype='bed' )
        hda4 = galaxy.model.HistoryDatasetAssociation.query() \
            .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
        assert hda4 is not None, "Problem retrieving hda4 from database"
        self.verify_dataset_correctness( '4.bed', hid=str( hda4.hid ) )
        self.upload_file( '1.scf', ftype='scf' )
        hda5 = galaxy.model.HistoryDatasetAssociation.query() \
            .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
        assert hda5 is not None, "Problem retrieving hda5 from database"
        self.verify_dataset_correctness( '1.scf', hid=str( hda5.hid ) )
        self.upload_file( '1.scf.zip', ftype='binseq.zip' )
        hda6 = galaxy.model.HistoryDatasetAssociation.query() \
            .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
        assert hda6 is not None, "Problem retrieving hda6 from database"
        self.verify_dataset_correctness( '1.scf.zip', hid=str( hda6.hid ) )
        self.delete_history( id=self.security.encode_id( history1.id ) )
    def test_005_url_paste( self ):
        """Test url paste behavior"""
        # Logged in as admin_user
        # Deleting the current history should have created a new history
        self.check_history_for_string( 'Your history is empty' )
        history2 = galaxy.model.History.filter( and_( galaxy.model.History.table.c.deleted==False,
                                                      galaxy.model.History.table.c.user_id==admin_user.id ) ) \
            .order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        self.upload_url_paste( 'hello world' )
        self.check_history_for_string( 'Pasted Entry' )
        self.check_history_for_string( 'hello world' )
        self.upload_url_paste( u'hello world' )
        self.check_history_for_string( 'Pasted Entry' )
        self.check_history_for_string( 'hello world' )
        self.delete_history( id=self.security.encode_id( history2.id ) )
    def test_010_upload_lped_composite_datatype_files( self ):
        """Test uploading lped composite datatype files"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history3 = galaxy.model.History.filter( and_( galaxy.model.History.table.c.deleted==False,
                                                      galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                                       .order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        # lped data types include a ped_file and a map_file ( which is binary )
        self.upload_composite_datatype_file( 'lped', ped_file='tinywga.ped', map_file='tinywga.map', base_name='rgenetics' )
        # Get the latest hid for testing
        hda1 = galaxy.model.HistoryDatasetAssociation.query() \
            .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
        assert hda1 is not None, "Problem retrieving hda1 from database"
        # We'll test against the resulting ped file and map file for correctness
        self.verify_composite_datatype_file_content( 'rgenetics.ped', str( hda1.id ) )
        self.verify_composite_datatype_file_content( 'rgenetics.map', str( hda1.id ) )
        self.delete_history( id=self.security.encode_id( history3.id ) )
    def test_015_upload_pbed_composite_datatype_files( self ):
        """Test uploading pbed composite datatype files"""
        # Logged in as admin_user
        self.check_history_for_string( 'Your history is empty' )
        history4 = galaxy.model.History.filter( and_( galaxy.model.History.table.c.deleted==False,
                                                      galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                                       .order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        # pbed data types include a bim_file, a bed_file and a fam_file
        self.upload_composite_datatype_file( 'pbed', bim_file='tinywga.bim', bed_file='tinywga.bed', fam_file='tinywga.fam', base_name='rgenetics' )
        # Get the latest hid for testing
        hda1 = galaxy.model.HistoryDatasetAssociation.query() \
            .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
        assert hda1 is not None, "Problem retrieving hda1 from database"
        # We'll test against the resulting ped file and map file for correctness
        self.verify_composite_datatype_file_content( 'rgenetics.bim', str( hda1.id ) )
        self.verify_composite_datatype_file_content( 'rgenetics.bed', str( hda1.id ) )
        self.verify_composite_datatype_file_content( 'rgenetics.fam', str( hda1.id ) )
        self.delete_history( id=self.security.encode_id( history4.id ) )
