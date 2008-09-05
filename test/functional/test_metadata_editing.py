from base.twilltestcase import TwillTestCase

class TestMetadataEdit( TwillTestCase ):

    def test_00_metadata_edit(self):
        """test_metadata_edit: Testing metadata editing"""
        self.login()
        self.upload_file('1.bed')
        self.check_history_for_string('\? bed')
        self.check_metadata_for_string('1.bed uploaded file unspecified (\?) chromCol value="1" selected endCol value="3" is_strandCol value="true" checked', hid=1)
        """test editing attributes"""
        self.edit_metadata(hid=1, form_no=0,  name='Testdata', info="Uploaded my file", dbkey='hg16', startCol='6')
        self.check_metadata_for_string('Testdata bed Uploaded my file hg16 "bed" selected="yes" "startCol" value="6" selected', hid=1)
        """test Auto-detecting attributes"""
        self.edit_metadata(hid=1, form_no=1)
        self.check_metadata_for_string('Testdata bed Uploaded my file hg16 "bed" selected="yes" "startCol" value="2" selected', hid=1)
        """test converting formats"""
        self.edit_metadata(hid=1, form_no=2, target_type='gff')
        self.check_history_for_string('hg16 Testdata Convert BED to GFF')
        self.check_metadata_for_string('"gff" selected="yes"', hid=1)
        """test changing data type"""
        self.edit_metadata(hid=1, form_no=3, datatype='gff3')
        self.check_history_for_string('hg16 Testdata Convert BED to GFF format: gff3')
        self.delete_history_item( 1 )
    def test_9999_clean_up( self ):
        self.delete_history()
        self.logout()
