from galaxy.datatypes.triples import Sbol
from .util import (
    get_dataset,
    get_input_files,
)


def test_sbol_sniff():
    sbol_datatype = Sbol()
    with get_input_files("sbol.v2.crispr_example.xml") as input_files:
        assert sbol_datatype.sniff(input_files[0]) is True


def test_sbol_set_meta():
    sbol_datatype = Sbol()
    with get_input_files("sbol.v2.crispr_example.xml") as input_files, get_dataset(input_files[0]) as dataset:
        sbol_datatype.set_meta(dataset)
        assert dataset.metadata.version == "2"

    with get_input_files("sbol.v3.circuit.nt") as input_files, get_dataset(input_files[0]) as dataset:
        sbol_datatype.set_meta(dataset)
        assert dataset.metadata.version == "3"
