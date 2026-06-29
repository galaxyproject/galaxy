import os

import pytest

from galaxy.util.unittest_utils import skip_unless_environ
from ._util import (
    assert_can_write_and_read_to_conf,
    assert_realizes_contains,
    assert_simple_file_realize,
    configured_file_sources,
    user_context_fixture,
)

pytest.importorskip("s3fs")

from galaxy.files.sources.s3fs import (  # noqa: E402  (after importorskip)
    S3FSFileSourceConfiguration,
    S3FsFilesSource,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "s3_file_sources_conf.yml")


def _s3fs_config(**kwargs) -> S3FSFileSourceConfiguration:
    return S3FSFileSourceConfiguration(type="s3fs", id="test", file_sources_config={}, **kwargs)


def test_config_kwargs_defaults_when_required_for_non_aws_endpoint():
    config = _s3fs_config(endpoint_url="https://storage.googleapis.com/")
    assert S3FsFilesSource._config_kwargs(config) == {"request_checksum_calculation": "when_required"}


def test_config_kwargs_none_for_aws_endpoint():
    # No endpoint -> AWS -> no botocore override (None means "don't pass config_kwargs").
    assert S3FsFilesSource._config_kwargs(_s3fs_config()) is None


def test_config_kwargs_explicit_value_wins():
    config = _s3fs_config(endpoint_url="https://storage.googleapis.com/", request_checksum_calculation="when_supported")
    assert S3FsFilesSource._config_kwargs(config) == {"request_checksum_calculation": "when_supported"}


def test_file_source():
    assert_simple_file_realize(
        FILE_SOURCES_CONF,
        recursive=False,
        filename="data_use_policies.txt",
        contents="DATA USE POLICIES",
        contains=True,
    )


def test_file_source_generic():
    file_url = "s3://ga4gh-demo-data/phenopackets/Cao-2018-TGFBR2-Patient_4.json"
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path(file_url)

    assert file_source_pair.path == file_url
    assert file_source_pair.file_source.id == "test2"

    assert_realizes_contains(
        file_sources, file_url, "PMID:30101859-Cao-2018-TGFBR2-Patient_4", user_context=user_context
    )


def test_file_source_specific():
    file_url = "s3://genomeark/data_use_policies.txt"
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path(file_url)

    assert file_source_pair.path == file_url
    assert file_source_pair.file_source.id == "test1"

    assert_realizes_contains(file_sources, file_url, "DATA USE POLICIES", user_context=user_context)


@skip_unless_environ("GALAXY_TEST_AWS_ACCESS_KEY")
@skip_unless_environ("GALAXY_TEST_AWS_SECRET_KEY")
@skip_unless_environ("GALAXY_TEST_AWS_BUCKET")
def test_read_write_against_aws():
    conf = {
        "type": "s3fs",
        "id": "playtest",
        "doc": "Test against Play development server.",
        "secret": os.environ["GALAXY_TEST_AWS_SECRET_KEY"],
        "key": os.environ["GALAXY_TEST_AWS_ACCESS_KEY"],
        "bucket": os.environ["GALAXY_TEST_AWS_BUCKET"],
        "writable": True,
    }
    assert_can_write_and_read_to_conf(conf)
