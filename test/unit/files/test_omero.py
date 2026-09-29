from datetime import (
    datetime,
    timezone,
)
from typing import Optional

from galaxy.files.plugins import FileSourcePluginsConfig
from galaxy.files.sources.omero import (
    OmeroFileSource,
    OmeroFileSourceTemplateConfiguration,
)

ACQUISITION_TIMESTAMP = 1790169452


class _PixelsType:
    def getValue(self):
        return "uint8"


class _Pixels:
    def getSizeX(self):
        return 1

    getSizeY = getSizeZ = getSizeC = getSizeT = getSizeX

    def getPixelsType(self):
        return _PixelsType()


class _Image:
    def __init__(self, date: Optional[datetime]):
        self._date = date

    def getDate(self):
        return self._date

    def getName(self):
        return "image"

    def getId(self):
        return 1

    def getPrimaryPixels(self):
        return _Pixels()


def _omero_file_source() -> OmeroFileSource:
    return OmeroFileSource(
        OmeroFileSourceTemplateConfiguration(
            id="omero",
            type="omero",
            username="user",
            password="pass",
            host="omero.example.org",
            port=4064,
            file_sources_config=FileSourcePluginsConfig(),
        )
    )


def test_omero_image_ctime_converts_gateway_local_time_to_utc(non_utc_local_time):
    image = _Image(datetime.fromtimestamp(ACQUISITION_TIMESTAMP))
    remote_file = _omero_file_source()._create_remote_file_for_image(image, "/image/1")
    assert remote_file.ctime == datetime.fromtimestamp(ACQUISITION_TIMESTAMP, tz=timezone.utc)


def test_omero_image_without_date_has_no_ctime():
    remote_file = _omero_file_source()._create_remote_file_for_image(_Image(None), "/image/1")
    assert remote_file.ctime is None
