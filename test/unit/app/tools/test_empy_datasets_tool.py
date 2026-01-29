import gzip
import tempfile
from contextlib import contextmanager
from typing import Union

from galaxy.model import (
    Dataset,
    DatasetCollectionElement,
    HistoryDatasetAssociation,
)
from galaxy.tools import FilterEmptyDatasetsTool


@contextmanager
def get_dce(empty, compressed):
    dataset = Dataset()
    with tempfile.NamedTemporaryFile(mode="wb") as out:
        fh: Union[gzip.GzipFile, tempfile._TemporaryFileWrapper]
        if compressed:
            fh = gzip.open(out.name, "wb")
        else:
            fh = out
        if not empty:
            fh.write(b"content")
        fh.flush()
        if compressed:
            fh.close()
        dataset.external_filename = out.name
        hda = HistoryDatasetAssociation(dataset=dataset)
        dce = DatasetCollectionElement(element=hda)
        yield dce


def test_valid_element_empty_dataset():
    with get_dce(empty=True, compressed=False) as dce:
        assert not FilterEmptyDatasetsTool.element_is_valid(dce)


def test_valid_element_empty_dataset_compressed():
    with get_dce(empty=True, compressed=True) as dce:
        assert not FilterEmptyDatasetsTool.element_is_valid(dce)


def test_valid_element_dataset_not_compressed():
    with get_dce(empty=False, compressed=False) as dce:
        assert FilterEmptyDatasetsTool.element_is_valid(dce)


def test_valid_element_dataset_compressed():
    with get_dce(empty=False, compressed=True) as dce:
        assert FilterEmptyDatasetsTool.element_is_valid(dce)
