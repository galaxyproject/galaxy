import os.path

from galaxy.model import (
    Dataset,
    History,
    HistoryDatasetAssociation,
)
from galaxy.util import galaxy_directory
from .util import BaseParameterTestCase


def get_test_data_path(name: str):
    path = os.path.join(galaxy_directory(), "test-data", name)
    assert os.path.isfile(path), f"{path} is not a file"
    return path


class TestParameterValidation(BaseParameterTestCase):
    def test_simple_ExpressionValidator(self):
        p = self._parameter_for(
            xml="""
<param name="blah" type="text" value="">
    <validator type="expression" message="Not gonna happen">value.lower() == "foo"</validator>
</param>"""
        )
        p.validate("Foo")
        p.validate("foo")
        with self.assertRaisesRegex(ValueError, "Not gonna happen"):
            p.validate("Fop")

    def test_negated_ExpressionValidator(self):
        p = self._parameter_for(
            xml="""
<param name="blah" type="text" value="10">
    <validator type="expression" message="Not gonna happen" negate="true">value.lower() == "foo"</validator>
</param>
"""
        )
        with self.assertRaisesRegex(ValueError, "Not gonna happen"):
            p.validate("Foo")
        p.validate("Fop")

    def test_boolean_ExpressionValidator(self):
        p = self._parameter_for(
            xml="""
<param name="blah" type="text" value="">
    <validator type="expression" message="Not gonna happen">value</validator>
</param>"""
        )
        p.validate("Foo")
        with self.assertRaisesRegex(ValueError, "Not gonna happen"):
            p.validate("")

        p = self._parameter_for(
            xml="""
<param name="blah" type="integer" value="">
    <validator type="expression" message="Not gonna happen">value</validator>
</param>"""
        )
        p.validate(3)
        with self.assertRaisesRegex(ValueError, "Not gonna happen"):
            p.validate(0)

    def test_ExpressionValidator_message(self):
        p = self._parameter_for(
            xml="""
<param name="blah" type="text" value="">
    <validator type="expression">value.lower() == "foo"</validator>
</param>"""
        )
        with self.assertRaisesRegex(
            ValueError, r"Value 'Fop' does not evaluate to True for 'value.lower\(\) == \"foo\"'"
        ):
            p.validate("Fop")
        with self.assertRaisesRegex(
            ValueError, r"Validator 'value.lower\(\) == \"foo\"' could not be evaluated on '1'"
        ):
            p.validate(1)

    def test_NoOptionsValidator(self):
        p = self._parameter_for(
            xml="""
<param name="index" type="select" label="Select reference genome">
    <validator type="no_options" message="No options available for selection"/>
</param>"""
        )
        p.validate("foo")
        with self.assertRaisesRegex(ValueError, "Parameter 'index': No options available for selection"):
            p.validate(None)

        p = self._parameter_for(
            xml="""
<param name="index" type="select" label="Select reference genome">
    <options from_data_table="bowtie2_indexes"/>
    <validator type="no_options" negate="true"/>
</param>"""
        )
        with self.assertRaisesRegex(ValueError, "Parameter 'index': Options available for selection"):
            p.validate("foo")
        p.validate(None)

    def test_EmptyTextfieldValidator(self):
        p = self._parameter_for(
            xml="""
<param name="blah" type="text" value="">
    <validator type="empty_field"/>
</param>"""
        )
        p.validate("foo")
        with self.assertRaisesRegex(ValueError, "Parameter 'blah': Field requires a value"):
            p.validate("")

        p = self._parameter_for(
            xml="""
<param name="blah" type="text" value="">
    <validator type="empty_field" negate="true"/>
</param>"""
        )
        with self.assertRaisesRegex(ValueError, "Parameter 'blah': Field must not set a value"):
            p.validate("foo")
        p.validate("")

    def test_RegexValidator(self):
        p = self._parameter_for(
            xml="""
<param name="blah" type="text" value="10">
    <validator type="regex">[Ff]oo</validator>
</param>"""
        )
        p.validate("Foo")
        p.validate("foo")
        with self.assertRaisesRegex(
            ValueError, r"Parameter 'blah': Value 'Fop' does not match regular expression '\[Ff\]oo'"
        ):
            p.validate("Fop")

        # test also valitation of lists (for select parameters)
        p.validate(["Foo", "foo"])
        with self.assertRaisesRegex(
            ValueError, r"Parameter 'blah': Value 'Fop' does not match regular expression '\[Ff\]oo'"
        ):
            p.validate(["Foo", "Fop"])

        p = self._parameter_for(
            xml="""
<param name="blah" type="text" value="10">
    <validator type="regex" negate="true">[Ff]oo</validator>
</param>"""
        )
        with self.assertRaisesRegex(
            ValueError, r"Parameter 'blah': Value 'Foo' does match regular expression '\[Ff\]oo'"
        ):
            p.validate("Foo")
        with self.assertRaisesRegex(
            ValueError, r"Parameter 'blah': Value 'foo' does match regular expression '\[Ff\]oo'"
        ):
            p.validate("foo")
        p.validate("Fop")
        with self.assertRaisesRegex(
            ValueError, r"Parameter 'blah': Value 'foo' does match regular expression '\[Ff\]oo'"
        ):
            p.validate(["Fop", "foo"])
        p.validate(["Fop", "fop"])

    def test_LengthValidator(self):
        p = self._parameter_for(
            xml="""
<param name="blah" type="text" value="foobar">
    <validator type="length" min="2" max="8"/>
</param>"""
        )
        p.validate("foo")
        p.validate("bar")
        with self.assertRaisesRegex(ValueError, "Parameter 'blah': Must have length of at least 2 and at most 8"):
            p.validate("f")
        with self.assertRaisesRegex(ValueError, "Parameter 'blah': Must have length of at least 2 and at most 8"):
            p.validate("foobarbaz")

        p = self._parameter_for(
            xml="""
<param name="blah" type="text" value="foobar">
    <validator type="length" min="2" max="8" negate="true"/>
</param>"""
        )
        with self.assertRaisesRegex(ValueError, "Parameter 'blah': Must not have length of at least 2 and at most 8"):
            p.validate("foo")
        with self.assertRaisesRegex(ValueError, "Parameter 'blah': Must not have length of at least 2 and at most 8"):
            p.validate("bar")
        p.validate("f")
        p.validate("foobarbaz")
        p = self._parameter_for(
            xml="""
<param name="blah" type="text" optional="false">
    <validator type="length" min="2" max="8"/>
</param>"""
        )
        with self.assertRaisesRegex(ValueError, "No value provided"):
            p.validate(None)

    def test_InRangeValidator(self):
        p = self._parameter_for(
            xml="""
<param name="blah" type="integer" value="10">
    <validator type="in_range" message="Doh!! %s not in range" min="10" exclude_min="true" max="20"/>
</param>"""
        )
        with self.assertRaisesRegex(ValueError, "Parameter 'blah': Doh!! 10 not in range"):
            p.validate(10)
        p.validate(15)
        p.validate(20)
        with self.assertRaisesRegex(ValueError, "Parameter 'blah': Doh!! 21 not in range"):
            p.validate(21)

        p = self._parameter_for(
            xml="""
 <param name="blah" type="integer" value="10">
    <validator type="in_range" min="10" exclude_min="true" max="20" negate="true"/>
</param>"""
        )
        p.validate(10)
        with self.assertRaisesRegex(
            ValueError,
            r"Parameter 'blah': Value \('15'\) must not fulfill \(10 < value <= 20\)",
        ):
            p.validate(15)
        with self.assertRaisesRegex(
            ValueError,
            r"Parameter 'blah': Value \('20'\) must not fulfill \(10 < value <= 20\)",
        ):
            p.validate(20)
        p.validate(21)

    def test_DatasetOkValidator(self):
        sa_session = self.app.model.context
        hist = History()
        with sa_session.begin():
            sa_session.add(hist)
        ok_hda = hist.add_dataset(
            HistoryDatasetAssociation(id=1, extension="interval", create_dataset=True, sa_session=sa_session)
        )
        ok_hda.state = Dataset.states.OK
        notok_hda = hist.add_dataset(
            HistoryDatasetAssociation(id=2, extension="interval", create_dataset=True, sa_session=sa_session)
        )
        notok_hda.state = Dataset.states.EMPTY

        p = self._parameter_for(
            xml="""
<param name="blah" type="data" no_validation="true">
    <validator type="dataset_ok_validator"/>
</param>"""
        )
        p.validate(ok_hda)
        with self.assertRaisesRegex(
            ValueError,
            "Parameter 'blah': The selected dataset is still being generated, select another dataset or wait until it is completed",
        ):
            p.validate(notok_hda)
        p = self._parameter_for(
            xml="""
<param name="blah" type="data" no_validation="true">
    <validator type="dataset_ok_validator" negate="true"/>
</param>"""
        )
        with self.assertRaisesRegex(ValueError, "Parameter 'blah': The selected dataset must not be in state OK"):
            p.validate(ok_hda)
        p.validate(notok_hda)

    def test_DatasetEmptyValidator(self):
        sa_session = self.app.model.context
        hist = History()
        with sa_session.begin():
            sa_session.add(hist)
        empty_dataset = Dataset(external_filename=get_test_data_path("empty.txt"))
        empty_hda = hist.add_dataset(
            HistoryDatasetAssociation(id=1, extension="interval", dataset=empty_dataset, sa_session=sa_session)
        )
        full_dataset = Dataset(external_filename=get_test_data_path("1.interval"))
        full_hda = hist.add_dataset(
            HistoryDatasetAssociation(id=2, extension="interval", dataset=full_dataset, sa_session=sa_session)
        )

        p = self._parameter_for(
            xml="""
<param name="blah" type="data">
    <validator type="empty_dataset"/>
</param>"""
        )
        p.validate(full_hda)
        with self.assertRaisesRegex(
            ValueError, "Parameter 'blah': The selected dataset is empty, this tool expects non-empty files."
        ):
            p.validate(empty_hda)

        p = self._parameter_for(
            xml="""
<param name="blah" type="data">
    <validator type="empty_dataset" negate="true"/>
</param>"""
        )
        with self.assertRaisesRegex(
            ValueError, "Parameter 'blah': The selected dataset is non-empty, this tool expects empty files."
        ):
            p.validate(full_hda)
        p.validate(empty_hda)

    def test_DatasetExtraFilesPathEmptyValidator(self):
        sa_session = self.app.model.context
        hist = History()
        with sa_session.begin():
            sa_session.add(hist)
        has_extra_hda = hist.add_dataset(
            HistoryDatasetAssociation(id=1, extension="interval", create_dataset=True, sa_session=sa_session)
        )
        has_extra_hda.dataset.file_size = 10
        has_extra_hda.dataset.total_size = 15
        has_no_extra_hda = hist.add_dataset(
            HistoryDatasetAssociation(id=2, extension="interval", create_dataset=True, sa_session=sa_session)
        )
        has_no_extra_hda.dataset.file_size = 10
        has_no_extra_hda.dataset.total_size = 10

        p = self._parameter_for(
            xml="""
<param name="blah" type="data">
    <validator type="empty_extra_files_path"/>
</param>"""
        )
        p.validate(has_extra_hda)
        with self.assertRaisesRegex(
            ValueError,
            "Parameter 'blah': The selected dataset's extra_files_path directory is empty or does not exist, this tool expects non-empty extra_files_path directories associated with the selected input.",
        ):
            p.validate(has_no_extra_hda)

        p = self._parameter_for(
            xml="""
<param name="blah" type="data">
    <validator type="empty_extra_files_path" negate="true"/>
</param>"""
        )

        with self.assertRaisesRegex(
            ValueError,
            "Parameter 'blah': The selected dataset's extra_files_path directory is non-empty or does exist, this tool expects empty extra_files_path directories associated with the selected input.",
        ):
            p.validate(has_extra_hda)
        p.validate(has_no_extra_hda)

    def test_MetadataValidator(self):
        sa_session = self.app.model.context
        hist = History()
        with sa_session.begin():
            sa_session.add(hist)
        hda = hist.add_dataset(
            HistoryDatasetAssociation(
                id=1,
                extension="bed",
                create_dataset=True,
                sa_session=sa_session,
                dataset=Dataset(external_filename=get_test_data_path("1.bed")),
            )
        )
        hda.state = Dataset.states.OK
        hda.set_meta()
        hda.metadata.strandCol = hda.metadata.spec["strandCol"].no_value

        param_xml = """
<param name="blah" type="data">
    <validator type="metadata" check="{check}" skip="{skip}"/>
</param>"""

        p = self._parameter_for(xml=param_xml.format(check="nameCol", skip=""))
        p.validate(hda)

        p = self._parameter_for(xml=param_xml.format(check="strandCol", skip=""))
        with self.assertRaisesRegex(
            ValueError,
            "Parameter 'blah': Metadata 'strandCol' missing, click the pencil icon in the history item to edit / save the metadata attributes",
        ):
            p.validate(hda)

        p = self._parameter_for(xml=param_xml.format(check="", skip="dbkey,comment_lines,column_names,strandCol"))
        p.validate(hda)
        p = self._parameter_for(xml=param_xml.format(check="", skip="dbkey,comment_lines,column_names,nameCol"))
        with self.assertRaisesRegex(
            ValueError,
            "Parameter 'blah': Metadata 'strandCol' missing, click the pencil icon in the history item to edit / save the metadata attributes",
        ):
            p.validate(hda)

        param_xml_negate = """
<param name="blah" type="data">
    <validator type="metadata" check="{check}" skip="{skip}" negate="true"/>
</param>"""
        p = self._parameter_for(xml=param_xml_negate.format(check="strandCol", skip=""))
        p.validate(hda)
        p = self._parameter_for(xml=param_xml_negate.format(check="nameCol", skip=""))
        with self.assertRaisesRegex(
            ValueError,
            "Parameter 'blah': At least one of the checked metadata 'nameCol' is set, click the pencil icon in the history item to edit / save the metadata attributes",
        ):
            p.validate(hda)

        p = self._parameter_for(xml=param_xml_negate.format(check="", skip="dbkey,comment_lines,column_names,nameCol"))
        p.validate(hda)
        p = self._parameter_for(
            xml=param_xml_negate.format(check="", skip="dbkey,comment_lines,column_names,strandCol")
        )
        with self.assertRaisesRegex(
            ValueError,
            "Parameter 'blah': At least one of the non skipped metadata 'dbkey,comment_lines,column_names,strandCol' is set, click the pencil icon in the history item to edit / save the metadata attributes",
        ):
            p.validate(hda)

    def test_UnspecifiedBuildValidator(self):
        sa_session = self.app.model.context
        hist = History()
        with sa_session.begin():
            sa_session.add(hist)
        has_dbkey_hda = hist.add_dataset(
            HistoryDatasetAssociation(id=1, extension="interval", create_dataset=True, sa_session=sa_session)
        )
        has_dbkey_hda.state = Dataset.states.OK
        has_dbkey_hda.metadata.dbkey = "hg19"
        has_no_dbkey_hda = hist.add_dataset(
            HistoryDatasetAssociation(id=2, extension="interval", create_dataset=True, sa_session=sa_session)
        )
        has_no_dbkey_hda.state = Dataset.states.OK

        p = self._parameter_for(
            xml="""
<param name="blah" type="data" no_validation="true">
    <validator type="unspecified_build"/>
</param>"""
        )
        p.validate(has_dbkey_hda)
        with self.assertRaisesRegex(
            ValueError,
            "Parameter 'blah': Unspecified genome build, click the pencil icon in the history item to set the genome build",
        ):
            p.validate(has_no_dbkey_hda)

        p = self._parameter_for(
            xml="""
<param name="blah" type="data" no_validation="true">
    <validator type="unspecified_build" negate="true"/>
</param>"""
        )
        with self.assertRaisesRegex(
            ValueError,
            "Parameter 'blah': Specified genome build, click the pencil icon in the history item to remove the genome build",
        ):
            p.validate(has_dbkey_hda)
        p.validate(has_no_dbkey_hda)

    def test_RegexValidator_global_flag_inline(self):
        # tests that global inline flags continue to work past python 3.10
        p = self._parameter_for(
            xml=r"""
<param name="blah" type="text" value="">
    <validator type="regex">^(?ims)\s*select\s+.*\s+from\s+.*$</validator>
</param>"""
        )
        p.validate("select id from job where id = 1;")
        with self.assertRaises(ValueError):
            p.validate("not sql")
