from galaxy.datatypes.qiime2 import (
    _strip_properties,
    QIIME2Artifact,
    QIIME2Metadata,
    QIIME2Visualization,
)
from .util import (
    get_input_files,
    MockDataset,
)

# Tests for QIIME2Artifact:


def test_qza_sniff():
    qza = QIIME2Artifact()
    with get_input_files("qiime2.qza") as input_files:
        assert qza.sniff(input_files[0]) is True


def test_qza_set_meta():
    qza = QIIME2Artifact()
    with get_input_files("qiime2.qza") as input_files:
        dataset = MockDataset(1)
        dataset.set_file_name(input_files[0])

        qza.set_meta(dataset)

        assert dataset.metadata.uuid == "ba8c55e1-a2bc-47ea-beb2-b37b0b3b4032"
        assert dataset.metadata.version == "2022.2.1"
        assert dataset.metadata.format == "SingleIntDirectoryFormat"
        assert dataset.metadata.semantic_type == "SingleInt1"
        assert dataset.metadata.semantic_type_simple == "SingleInt1"


def test_qza_set_peek():
    qza = QIIME2Artifact()
    with get_input_files("qiime2.qza") as input_files:
        dataset = MockDataset(1)
        dataset.set_file_name(input_files[0])
        dataset.metadata.semantic_type = None
        dataset.metadata.uuid = None
        assert qza.display_peek(dataset) == "Peek unavailable"

        qza.set_meta(dataset)
        qza.set_peek(dataset)

        assert (
            dataset.peek
            == """Type: SingleInt1
UUID: ba8c55e1-a2bc-47ea-beb2-b37b0b3b4032
Format: SingleIntDirectoryFormat
Version: 2022.2.1"""
        )


# Tests for QIIME2Visualization:


def test_qzv_sniff():
    qzv = QIIME2Visualization()
    with get_input_files("qiime2.qzv") as input_files:
        assert qzv.sniff(input_files[0]) is True


def test_qzv_set_meta():
    qzv = QIIME2Visualization()
    with get_input_files("qiime2.qzv") as input_files:
        dataset = MockDataset(1)
        dataset.set_file_name(input_files[0])

        qzv.set_meta(dataset)

        assert dataset.metadata.uuid == "368ba1e7-3a7c-4dbc-98da-79f41aeece63"
        assert dataset.metadata.version == "2022.2.1"
        assert dataset.metadata.semantic_type == "Visualization"
        assert dataset.metadata.semantic_type_simple == "Visualization"


def test_qzv_set_peek():
    qzv = QIIME2Visualization()
    with get_input_files("qiime2.qzv") as input_files:
        dataset = MockDataset(1)
        dataset.set_file_name(input_files[0])

        qzv.set_meta(dataset)
        qzv.set_peek(dataset)

        assert (
            dataset.peek
            == """Type: Visualization
UUID: 368ba1e7-3a7c-4dbc-98da-79f41aeece63
Version: 2022.2.1"""
        )


# Tets for QIIME2Metadata:


def test_qiime2tabular_sniff():
    q2md = QIIME2Metadata()
    with get_input_files("qiime2.qiime2.tabular") as input_files:
        assert q2md.sniff(input_files[0]) is True


def test_qiime2tabular_sniff_false():
    q2md = QIIME2Metadata()
    with get_input_files("test_tab1.tabular") as input_files:
        assert q2md.sniff(input_files[0]) is False


def test_qiime2tabular_set_meta():
    q2md = QIIME2Metadata()
    with get_input_files("qiime2.qiime2.tabular") as input_files:
        dataset = MockDataset(1)
        dataset.set_file_name(input_files[0])

        q2md.set_meta(dataset)

        # Show override of type inferrence on the second to last column:
        assert dataset.metadata.column_types == ["str", "str", "str", "int"]


# Tests for _strip_properties, which is rather complicated so worth testing
# on it's own.

# Note: Not all the expressions here are completely valid types they are just
# representative examples


def test_strip_properties_simple():
    simple_expression = 'Taxonomy % Properties("SILVIA")'
    stripped_expression = "Taxonomy"

    reconstructed_expression = _strip_properties(simple_expression)

    assert reconstructed_expression == stripped_expression


def test_strip_properties_single():
    single_expression = 'FeatureData[Taxonomy % Properties("SILVIA")]'
    stripped_expression = "FeatureData[Taxonomy]"

    reconstructed_expression = _strip_properties(single_expression)

    assert reconstructed_expression == stripped_expression


def test_strip_properties_double():
    double_expression = 'FeatureData[Taxonomy % Properties("SILVIA"), DistanceMatrix % Axes("ASV", "ASV")]'
    stripped_expression = "FeatureData[Taxonomy, DistanceMatrix]"

    reconstructed_expression = _strip_properties(double_expression)

    assert reconstructed_expression == stripped_expression


def test_strip_properties_nested():
    nested_expression = 'Tuple[FeatureData[Taxonomy % Properties("SILVIA")] % Axes("ASV", "ASV")]'
    stripped_expression = "Tuple[FeatureData[Taxonomy]]"

    reconstructed_expression = _strip_properties(nested_expression)

    assert reconstructed_expression == stripped_expression


def test_strip_properties_complex():
    complex_expression = (
        'Tuple[FeatureData[Taxonomy % Properties("SILVA")] % Axis("ASV")'
        ', DistanceMatrix % Axes("ASV", "ASV")] % Unique'
    )
    stripped_expression = "Tuple[FeatureData[Taxonomy], DistanceMatrix]"

    reconstructed_expression = _strip_properties(complex_expression)

    assert reconstructed_expression == stripped_expression


def test_strip_properties_keeps_different_binop():
    expression_with_different_binop = 'FeatureData[Taxonomy % Properties("SILVIA"), Taxonomy & Properties]'
    stripped_expression = "FeatureData[Taxonomy, Taxonomy & Properties]"

    reconstructed_expression = _strip_properties(expression_with_different_binop)

    assert reconstructed_expression == stripped_expression


def test_strip_properties_multiple_strings():
    simple_expression = 'Taxonomy % Properties("SILVIA")'
    stripped_simple_expression = "Taxonomy"

    reconstructed_simple_expression = _strip_properties(simple_expression)

    single_expression = 'FeatureData[Taxonomy % Properties("SILVIA")]'
    stripped_single_expression = "FeatureData[Taxonomy]"

    reconstructed_single_expression = _strip_properties(single_expression)

    assert reconstructed_simple_expression == stripped_simple_expression
    assert reconstructed_single_expression == stripped_single_expression
