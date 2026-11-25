import logging
import os

import pytest

from galaxy.datatypes.mothur import (
    AlignCheck,
    CountTable,
    GroupAbund,
    LowerTriangleDistanceMatrix,
    Otu,
    PairwiseDistanceMatrix,
    Sabund,
    SffFlow,
    SquareDistanceMatrix,
)
from galaxy.datatypes.sniff import FilePrefix
from .util import MockDataset


class SizedMockDataset(MockDataset):
    def has_data(self):
        return os.path.getsize(self.get_file_name()) > 0


def _dataset(tmp_path, content):
    path = tmp_path / "input"
    path.write_text(content)
    dataset = SizedMockDataset(id=1)
    dataset.set_file_name(str(path))
    return dataset


@pytest.mark.parametrize("content", ["", "\n"], ids=["empty", "blank_line"])
def test_count_table_set_meta_empty(tmp_path, content):
    """Empty count tables (e.g. from chimera.uchime) have no header line."""
    dataset = _dataset(tmp_path, content)
    CountTable().set_meta(dataset)
    assert dataset.metadata.columns == 0
    assert dataset.metadata.column_types == []


def test_group_abund_set_meta_skips_short_and_blank_lines(tmp_path):
    dataset = _dataset(tmp_path, "label\tGroup\tnumOtus\tOtu1\n\n0.03\tA\t1\t5\nshort\n0.03\tB\t1\t2\n")
    GroupAbund().set_meta(dataset)
    assert dataset.metadata.data_lines == 2
    assert dataset.metadata.groups == ["A", "B"]
    assert dataset.metadata.skip == 1


def test_align_check_set_meta_empty(tmp_path):
    dataset = _dataset(tmp_path, "")
    AlignCheck().set_meta(dataset)
    assert dataset.metadata.data_lines == 0


def test_distance_matrix_set_meta_skips_leading_blank_line(tmp_path, caplog):
    dataset = _dataset(tmp_path, "\n2\nseqA\nseqB\t0.1\n")
    with caplog.at_level(logging.WARNING, logger="galaxy.datatypes.mothur"):
        LowerTriangleDistanceMatrix().set_meta(dataset)
    assert dataset.metadata.sequence_count == 2
    assert not caplog.records


def test_sff_flow_set_meta_empty_no_warning(tmp_path, caplog):
    dataset = _dataset(tmp_path, "")
    with caplog.at_level(logging.WARNING, logger="galaxy.datatypes.mothur"):
        SffFlow().set_meta(dataset)
    assert not caplog.records


def test_pairwise_distance_matrix_sniff_integer_distances(tmp_path):
    path = tmp_path / "input"
    path.write_text("seqA\tseqB\t1\nseqA\tseqC\t2\nseqB\tseqC\t3\n")
    assert PairwiseDistanceMatrix().sniff_prefix(FilePrefix(str(path))) is False


@pytest.mark.parametrize("datatype", [LowerTriangleDistanceMatrix(), SquareDistanceMatrix()])
def test_distance_matrix_sniff_empty(tmp_path, datatype):
    path = tmp_path / "input"
    path.write_text("")
    assert datatype.sniff_prefix(FilePrefix(str(path))) is False


PHYLOTYPE_SABUND = "1\t3\t0\t1\t2\n2\t3\t1\t0\t2\n3\t4\t2\t1\t0\t1\n"
PHYLOTYPE_LIST = "label\tnumOtus\tOtu1\tOtu2\n1\t2\tseqA,seqB\tseqC\n2\t2\tseqA\tseqB,seqC\n3\t2\tseqA\tseqB,seqC\n"


@pytest.mark.parametrize(
    "datatype, content",
    [(Sabund(), PHYLOTYPE_SABUND), (Otu(), PHYLOTYPE_SABUND), (Otu(), PHYLOTYPE_LIST)],
    ids=["sabund", "otu_no_heading", "list"],
)
def test_sniff_phylotype_integer_labels(tmp_path, datatype, content):
    path = tmp_path / "input"
    path.write_text(content)
    assert datatype.sniff_prefix(FilePrefix(str(path))) is True


@pytest.mark.parametrize("datatype", [LowerTriangleDistanceMatrix(), SquareDistanceMatrix()])
def test_distance_matrix_sniff_zero_count(tmp_path, datatype):
    path = tmp_path / "input"
    path.write_text("0\n")
    assert datatype.sniff_prefix(FilePrefix(str(path))) is False


def test_sabund_sniff_with_heading_line(tmp_path):
    path = tmp_path / "input"
    path.write_text("label\tnumOtus\tOtu1\tOtu2\nunique\t2\t94\t2\n0.03\t2\t75\t6\n")
    assert Sabund().sniff_prefix(FilePrefix(str(path))) is True
