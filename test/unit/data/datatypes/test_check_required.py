from galaxy.datatypes.data import Data
from galaxy.datatypes.metadata import MetadataElement
from galaxy.model import HistoryDatasetAssociation
from galaxy.model.unittest_utils import GalaxyDataTestApp


class CheckRequiredFalse(Data):
    ext = "false"
    MetadataElement(name="columns", desc="Number of columns")


class CheckRequiredTrue(Data):
    ext = "true"
    check_required_metadata = True
    MetadataElement(name="columns", desc="Number of columns")


class CheckRequiredInherited(CheckRequiredTrue):
    ext = "inherited"
    MetadataElement(name="something")


def test_check_required_metadata_false():
    app = GalaxyDataTestApp()
    app.datatypes_registry.datatypes_by_extension["false"] = CheckRequiredFalse()
    hda = HistoryDatasetAssociation(sa_session=app.model.session, extension="false")
    assert not hda.metadata.spec["columns"].check_required_metadata


def test_check_required_metadata_true():
    app = GalaxyDataTestApp()
    app.datatypes_registry.datatypes_by_extension["true"] = CheckRequiredTrue()
    hda = HistoryDatasetAssociation(sa_session=app.model.session, extension="true")
    assert hda.metadata.spec["columns"].check_required_metadata


def test_check_required_metadata_inherited():
    app = GalaxyDataTestApp()
    app.datatypes_registry.datatypes_by_extension["inherited"] = CheckRequiredInherited()
    hda = HistoryDatasetAssociation(sa_session=app.model.session, extension="inherited")
    assert hda.metadata.spec["columns"].check_required_metadata
    assert not hda.metadata.spec["something"].check_required_metadata
