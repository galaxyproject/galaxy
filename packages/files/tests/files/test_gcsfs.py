import os

import pytest

from galaxy.exceptions import MessageException
from galaxy.files.sources import googlecloudstorage
from ._util import (
    configured_file_sources,
    list_root,
    user_context_fixture,
)

try:
    from gcsfs import GCSFileSystem
except ImportError:
    GCSFileSystem = None

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "gcsfs_file_sources_conf.yml")


skip_if_no_gcsfs_libs = pytest.mark.skipif(
    not GCSFileSystem, reason="Required lib to run gcs file source test: gcsfs is not available"
)


@skip_if_no_gcsfs_libs
def test_file_source():
    """Test that we can list files from a public GCS bucket with anonymous access."""
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    res = list_root(file_sources, "gxfiles://test1", recursive=False, user_context=user_context)
    # Verify we got some results from the public bucket
    assert len(res) > 0, "Expected to find files/directories in the public GCS bucket"


class _OpenedFileSystem(Exception):
    pass


def _gcs_conf(**overrides):
    conf = {
        "type": "googlecloudstorage",
        "id": "rp",
        "bucket_name": "some-requester-pays-bucket",
        "project": "billing-project",
        "anonymous": False,
    }
    conf.update(overrides)
    return conf


def _open_fs_kwargs(monkeypatch, conf):
    """List the source against a stub GCSFileSystem and return the kwargs it was built with."""
    captured = {}

    def stub_gcs_file_system(**kwargs):
        captured.update(kwargs)
        raise _OpenedFileSystem()

    monkeypatch.setattr(googlecloudstorage, "GCSFileSystem", stub_gcs_file_system)
    file_sources = configured_file_sources([conf])
    with pytest.raises(MessageException):
        list_root(file_sources, "gxfiles://rp", recursive=False, user_context=user_context_fixture())
    return captured


@skip_if_no_gcsfs_libs
def test_requester_pays_defaults_off(monkeypatch):
    assert _open_fs_kwargs(monkeypatch, _gcs_conf())["requester_pays"] is False


@skip_if_no_gcsfs_libs
def test_requester_pays_true_bills_project(monkeypatch):
    assert _open_fs_kwargs(monkeypatch, _gcs_conf(requester_pays=True))["requester_pays"] is True


@skip_if_no_gcsfs_libs
def test_requester_pays_project_id(monkeypatch):
    kwargs = _open_fs_kwargs(monkeypatch, _gcs_conf(requester_pays="other-project"))
    assert kwargs["requester_pays"] == "other-project"


@skip_if_no_gcsfs_libs
def test_requester_pays_rejects_anonymous():
    file_sources = configured_file_sources([_gcs_conf(requester_pays=True, anonymous=True)])
    with pytest.raises(MessageException, match="anonymous"):
        list_root(file_sources, "gxfiles://rp", recursive=False, user_context=user_context_fixture())


@skip_if_no_gcsfs_libs
def test_requester_pays_true_requires_project():
    file_sources = configured_file_sources([_gcs_conf(requester_pays=True, project=None)])
    with pytest.raises(MessageException, match="needs a project"):
        list_root(file_sources, "gxfiles://rp", recursive=False, user_context=user_context_fixture())
