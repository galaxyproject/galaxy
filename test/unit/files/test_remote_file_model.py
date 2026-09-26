from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from galaxy.files.models import RemoteFile
from galaxy.schema.remote_files import ListUriResponse

UTC_TIME = datetime(2024, 1, 15, 10, 20, 30, tzinfo=timezone.utc)


def _remote_file(ctime) -> RemoteFile:
    return RemoteFile(name="a", uri="gxfiles://test1/a", path="/a", size=1, ctime=ctime)


@pytest.mark.parametrize(
    "ctime, expected",
    [
        (UTC_TIME.timestamp(), UTC_TIME),
        (datetime(2024, 1, 15, 10, 20, 30), UTC_TIME),
        (datetime(2024, 1, 15, 12, 20, 30, tzinfo=timezone(timedelta(hours=2))), UTC_TIME),
        ("2024-01-15T10:20:30Z", UTC_TIME),
        ("2024-01-15T12:20:30+02:00", UTC_TIME),
        ("2024-01-15T10:20:30.000000+00:00", UTC_TIME),
        ("2024-01-15T10:20:30", UTC_TIME),
        ("2024-01-15 10:20:30", UTC_TIME),
        ("2024-01-15", datetime(2024, 1, 15, tzinfo=timezone.utc)),
        (None, None),
        ("", None),
        ("not a timestamp", None),
    ],
)
def test_remote_file_ctime_is_utc(non_utc_local_time, ctime, expected):
    assert _remote_file(ctime).ctime == expected


def test_remote_files_api_serializes_ctime_as_utc():
    remote_file = _remote_file("2024-01-15T12:20:30+02:00")
    response = ListUriResponse.model_validate([remote_file.model_dump(by_alias=True)])
    assert '"ctime":"2024-01-15T10:20:30Z"' in response.model_dump_json()


def test_remote_file_ctime_assignment_is_utc(non_utc_local_time):
    remote_file = _remote_file(None)
    remote_file.ctime = datetime(2024, 1, 15, 10, 20, 30)
    assert remote_file.ctime == UTC_TIME
    assert remote_file.ctime.utcoffset() == timedelta(0)
