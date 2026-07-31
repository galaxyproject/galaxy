"""Tests for the global max_optional_metadata_filesize config option.

Setting optional metadata means reading a dataset from end to end. The size cut
off that suppresses it existed only as a per-datatype attribute in
datatypes_conf.xml; these tests cover the global default, its precedence rules,
and the fact that it reaches the separate processes that set metadata.
"""

import os

import pytest

from galaxy.datatypes.data import (
    Data,
    Text,
)
from galaxy.datatypes.registry import Registry
from galaxy.datatypes.sequence import FastqSanger
from galaxy.util import galaxy_directory
from galaxy.util.bunch import Bunch

DATATYPES_CONF = os.path.join(galaxy_directory(), "lib", "galaxy", "config", "sample", "datatypes_conf.xml.sample")


@pytest.fixture(autouse=True)
def restore_class_level_cut_off():
    """Undo the class-level mutation these tests cause.

    The cut off is stored on the datatype class, not the instance, so both
    load_datatypes() and a direct assignment leak into every later test in the
    same process. Without this, these tests silently broke test_sequence.py.
    """
    touched = [FastqSanger, Text, Data]
    sentinel = object()
    saved = [(cls, cls.__dict__.get("_max_optional_metadata_filesize", sentinel)) for cls in touched]
    yield
    for cls, previous in saved:
        if previous is sentinel:
            if "_max_optional_metadata_filesize" in cls.__dict__:
                delattr(cls, "_max_optional_metadata_filesize")
        else:
            cls._max_optional_metadata_filesize = previous


def _registry(config=None):
    registry = Registry(config=config)
    registry.load_datatypes(
        root_dir=galaxy_directory(),
        config=DATATYPES_CONF,
        use_build_sites=False,
        use_converters=False,
        use_display_applications=False,
    )
    return registry


def _cut_off_for(registry, extension):
    return registry.datatypes_by_extension[extension].max_optional_metadata_filesize


def test_without_the_option_behaviour_is_unchanged():
    """No config value means the cut off comes from datatypes_conf.xml as before.

    Note what that actually yields: the sample config sets the attribute only on
    the ``data`` datatype, but the cut off is stored on the datatype *class*, so
    every datatype deriving from Data inherits it through the MRO. fastqsanger
    never mentions the attribute yet ends up with Data's 1MB. That implicit
    inheritance is why a global option is worth having, and this test pins the
    pre-existing behaviour so the option does not change it.
    """
    registry = _registry()
    assert _cut_off_for(registry, "fastqsanger") == 1048576


def test_global_option_applies_to_datatypes():
    registry = _registry(config=Bunch(max_optional_metadata_filesize=1024))
    assert _cut_off_for(registry, "fastqsanger") == 1024


def test_zero_means_never_read():
    """0 is the 'do not read datasets for optional metadata' setting."""
    registry = _registry(config=Bunch(max_optional_metadata_filesize=0))
    assert _cut_off_for(registry, "fastqsanger") == 0


def test_reaches_processes_that_have_no_config(tmp_path):
    """The value must survive the round trip through the job's registry XML.

    set_metadata and the fetch tool build a Registry from that XML in a separate
    process and never see a config object, so the option is only effective if it
    is written into the datatype elements.
    """
    registry = _registry(config=Bunch(max_optional_metadata_filesize=4096))
    registry_xml = tmp_path / "registry.xml"
    registry.to_xml_file(str(registry_xml))

    reloaded = Registry()  # no config, exactly as the metadata process builds it
    reloaded.load_datatypes(
        root_dir=galaxy_directory(),
        config=str(registry_xml),
        use_build_sites=False,
        use_converters=False,
        use_display_applications=False,
    )
    assert _cut_off_for(reloaded, "fastqsanger") == 4096


def test_datatype_attribute_wins_over_global_option():
    """An explicit attribute in datatypes_conf.xml takes precedence."""
    import xml.etree.ElementTree as ET

    tree = ET.parse(DATATYPES_CONF)
    root = tree.getroot()
    for elem in root.find("registration").findall("datatype"):
        if elem.get("extension") == "fastqsanger":
            elem.set("max_optional_metadata_filesize", "777")

    registry = Registry(config=Bunch(max_optional_metadata_filesize=4096))
    registry.load_datatypes(
        root_dir=galaxy_directory(),
        config=root,
        use_build_sites=False,
        use_converters=False,
        use_display_applications=False,
    )
    assert _cut_off_for(registry, "fastqsanger") == 777


def test_large_fastq_is_not_read(tmp_path):
    """The point of the option: no bytes are read for an oversized dataset."""
    fastq = tmp_path / "reads.fastqsanger"
    fastq.write_text("@r1\nACGT\n+\nIIII\n" * 500)
    size = fastq.stat().st_size

    class FakeDataset:
        metadata = Bunch(data_lines=0, sequences=0)

        def get_file_name(self, sync_cache=True):
            return str(fastq)

        def get_size(self, nice_size=False, calculate_size=True):
            return size

        def has_data(self):
            return True

    datatype = FastqSanger()

    datatype.max_optional_metadata_filesize = -1
    dataset = FakeDataset()
    datatype.set_meta(dataset)
    assert dataset.metadata.sequences == 500

    datatype.max_optional_metadata_filesize = 0
    dataset = FakeDataset()
    datatype.set_meta(dataset)
    assert dataset.metadata.sequences is None
    assert dataset.metadata.data_lines is None
