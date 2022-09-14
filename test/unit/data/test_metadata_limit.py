import pytest

import galaxy.datatypes.registry as registry
import galaxy.model.mapping as mapping
from galaxy.model import (
    custom_types,
    HistoryDatasetAssociation,
    set_datatypes_registry,
)

METADATA_LIMIT = 500


@pytest.fixture(scope="module")
def datatypes_registry():
    r = registry.Registry()
    r.load_datatypes()
    set_datatypes_registry(r)


@pytest.fixture
def sa_session(datatypes_registry):
    custom_types.MAX_METADATA_VALUE_SIZE = METADATA_LIMIT
    return mapping.init("/tmp", "sqlite:///:memory:", create_tables=True).session


def create_bed_data(sa_session, string_size):
    hda = HistoryDatasetAssociation(extension="bed")
    big_string = "0" * string_size
    sa_session.add(hda)
    hda.metadata.column_names = [big_string]
    assert hda.metadata.column_names
    sa_session.flush()
    return hda


def test_hda_below_limit(sa_session):
    hda = create_bed_data(sa_session=sa_session, string_size=1)
    assert len(hda.metadata.column_names[0]) == 1


def test_hda_above_limit(sa_session):
    hda = create_bed_data(sa_session=sa_session, string_size=1000)
    assert not hda.metadata.column_names
