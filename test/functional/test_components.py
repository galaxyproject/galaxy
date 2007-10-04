from base.twilltestcase import TwillTestCase

class TestHistory( TwillTestCase ):

    def test_new_history( self ):
        """test_componments.test_new_history: Testing creating a new history"""
        self.new_history()
        if len(self.get_datasets_in_history()) > 0:
            raise AssertionError("test_framework.test_new_history failed")
    def test_delete_history_item( self ):
        """test_components.test_delete_history_item: Testing deleting history item"""
        self.new_history()
        self.upload_file('1.bed', dbkey='hg15')
        self.check_history_for_string('hg15 bed')
        self.assertEqual ( len(self.get_datasets_in_history()), 1)
        self.delete_history_item(1)
        self.check_history_for_string("Your history is empty")
        self.assertEqual ( len(self.get_datasets_in_history()), 0)

class TestMetadata( TwillTestCase ):

    def test_metadata_edit(self):
        """test_components.test_metadata_edit: Testing metadata editing"""
        self.new_history()
        self.upload_file('1.bed')
        self.check_history_for_string('\? bed')
        self.check_metadata_for_string('1.bed uploaded file unspecified (\?) chromCol value="1" selected endCol value="3" is_strandCol value="true" checked', hid=1)
        """test editing attributes"""
        self.edit_metadata(hid=1, form=1,  name='Testdata', info="Uploaded my file", dbkey='hg16')
        self.check_metadata_for_string('Testdata bed Uploaded my file hg16 "bed" selected="yes"', hid=1)
        """test converting formats"""
        self.edit_metadata(hid=1, form=2, target_type='gff')
        self.check_history_for_string('hg16 Testdata Convert BED to GFF')
        self.check_metadata_for_string('"gff" selected="yes"', hid=1)
        """test changing data type"""
        self.edit_metadata(hid=1, form=3, datatype='gff3')
        self.check_history_for_string('hg16 Testdata Convert BED to GFF format: gff3')
        
