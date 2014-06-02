from base.twilltestcase import TwillTestCase
from functional import database_contexts
import galaxy.model
from galaxy.model.orm import (
    and_,
    desc,
)


class TestMetadataEdit( TwillTestCase ):

    def test_00_metadata_edit( self ):
        """test_metadata_edit: Testing metadata editing"""
        sa_session = database_contexts.galaxy_context
        self.logout()
        self.login( email='test@bx.psu.edu', username='admin-user' )
        admin_user = sa_session.query( galaxy.model.User ) \
                              .filter( galaxy.model.User.table.c.email == 'test@bx.psu.edu' ) \
                              .one()
        self.new_history( name='Test Metadata Edit' )
        history1 = sa_session.query( galaxy.model.History ) \
                            .filter( and_( galaxy.model.History.table.c.deleted == False,
                                           galaxy.model.History.table.c.user_id == admin_user.id ) ) \
                            .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                            .first()
        self.upload_file( '1.bed' )
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
        self.check_history_for_string( '1.bed' )
        self.check_metadata_for_string( '1.bed uploaded file unspecified (\?) chromCol value="1" selected endCol value="3" is_strandCol value="true" checked', hid=str( latest_hda.hid ) )
        """test editing attributes"""
        self.edit_hda_attribute_info( hda_id=str( latest_hda.id ),
                                      new_name='Testdata',
                                      new_info="Uploaded my file",
                                      new_dbkey='hg16',
                                      new_startcol='6' )
        self.check_metadata_for_string( 'Testdata bed Uploaded my file hg16 "bed" selected="yes" "startCol" value="6" selected', hid=str( latest_hda.hid ) )
        """test Auto-detecting attributes"""
        self.auto_detect_metadata( hda_id=str( latest_hda.id ) )
        self.check_metadata_for_string('Testdata bed Uploaded my file hg16 "bed" selected="yes" "startCol" value="2" selected', hid=str( latest_hda.hid ) )
        """test converting formats"""
        self.convert_format( hda_id=str( latest_hda.id ), target_type='gff' )
        self.check_metadata_for_string( '"gff" selected="yes"', hid=str( latest_hda.hid ) )
        """test changing data type"""
        self.change_datatype( hda_id=str( latest_hda.id ), datatype='gff3' )
        self.check_metadata_for_string( 'gff3', hid=str( latest_hda.hid ) )
        self.delete_history( id=self.security.encode_id( history1.id ) )
        self.logout()
