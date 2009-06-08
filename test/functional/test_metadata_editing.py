import galaxy.model
from galaxy.model.orm import *
from base.twilltestcase import TwillTestCase

class TestMetadataEdit( TwillTestCase ):

    def test_00_metadata_edit( self ):
        """test_metadata_edit: Testing metadata editing"""
        self.logout()
        self.login( email='test@bx.psu.edu' )
        self.new_history( name='Test Metadata Edit' )
        global history1
        history1 = galaxy.model.History.query() \
            .order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        self.upload_file( '1.bed' )
        latest_hda = galaxy.model.HistoryDatasetAssociation.query() \
            .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
        self.home()
        # Due to twill not being able to handle the permissions forms, we'll eliminate
        # DefaultHistoryPermissions prior to uploading a dataset so that the permission
        # form will not be displayed on ted edit attributes page.
        for dp in latest_hda.dataset.actions:
            dp.delete()
            dp.flush()
        latest_hda.dataset.refresh()
        self.check_history_for_string( '1.bed' )
        self.check_metadata_for_string( '1.bed uploaded file unspecified (\?) chromCol value="1" selected endCol value="3" is_strandCol value="true" checked', hid=1 )
        """test editing attributes"""
        self.edit_hda_attribute_info( hda_id=str( latest_hda.id ),
                                      new_name='Testdata',
                                      new_info="Uploaded my file",
                                      new_dbkey='hg16',
                                      new_startcol='6' )
        self.check_metadata_for_string( 'Testdata bed Uploaded my file hg16 "bed" selected="yes" "startCol" value="6" selected', hid=1 )
        """test Auto-detecting attributes"""
        self.auto_detect_metadata( hda_id=str( latest_hda.id ) )
        self.check_metadata_for_string('Testdata bed Uploaded my file hg16 "bed" selected="yes" "startCol" value="2" selected', hid=1 )
        """test converting formats"""
        self.convert_format( hda_id=str( latest_hda.id ), target_type='gff' )
        self.check_metadata_for_string( '"gff" selected="yes"', hid=1 )
        """test changing data type"""
        self.change_datatype( hda_id=str( latest_hda.id ), datatype='gff3' )
        self.check_metadata_for_string( 'gff3', hid=1 )
        self.delete_history( id=str( history1.id ) )
        self.logout()
