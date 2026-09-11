from pathlib import Path
from unittest.mock import MagicMock

import pytest

from galaxy.objectstore.examples import get_example
from galaxy.objectstore.s3 import S3ObjectStore
from galaxy.objectstore.s3_boto3 import S3ObjectStore as Boto3ObjectStore
from galaxy.objectstore.unittest_utils import Config as StoreConfig

REMOTE_CONTENT = b"remote object content"
BOTO3_CONFIG = """
type: boto3
auth:
  access_key: access_moo
  secret_key: secret_cow
bucket:
  name: unique_bucket_name_all_lowercase
"""


class UninitializedS3ObjectStore(S3ObjectStore):
    def _initialize(self):
        pass


class UninitializedBoto3ObjectStore(Boto3ObjectStore):
    def _initialize(self):
        pass


class FailedDownloadBoto3ObjectStore(UninitializedBoto3ObjectStore):
    def _download(self, rel_path: str) -> bool:
        return False


@pytest.fixture
def legacy_store():
    pytest.importorskip("boto")
    with StoreConfig(get_example("s3_global_cache.yml"), clazz=UninitializedS3ObjectStore) as (_, store):
        store._ensure_staging_path_writable()
        store.use_axel = False
        store._bucket = MagicMock()
        yield store


@pytest.fixture
def boto3_store():
    with StoreConfig(BOTO3_CONFIG, clazz=UninitializedBoto3ObjectStore) as (_, store):
        store._ensure_staging_path_writable()
        store._client = MagicMock()
        yield store


def _serve_legacy_object(store, downloaded_content):
    key = store._bucket.get_key.return_value
    key.size = len(REMOTE_CONTENT)
    key.get_contents_to_filename.side_effect = lambda filename, **_: Path(filename).write_bytes(downloaded_content)


def _serve_boto3_object(store, downloaded_content, remote_size=len(REMOTE_CONTENT)):
    store._client.head_object.return_value = {"ContentLength": remote_size}
    store._client.download_file.side_effect = lambda _bucket, _key, filename, **_: Path(filename).write_bytes(
        downloaded_content
    )


def _cache(store) -> Path:
    return Path(store.staging_path)


def _assert_nothing_published(store, rel_path="object"):
    assert not (_cache(store) / rel_path).exists()
    assert not list(_cache(store).rglob("*.tmp"))


def test_legacy_s3_does_not_publish_truncated_download(legacy_store):
    _serve_legacy_object(legacy_store, REMOTE_CONTENT[:5])

    with pytest.raises(OSError, match="downloaded object size"):
        legacy_store._download("object")

    _assert_nothing_published(legacy_store)


def test_boto3_does_not_publish_empty_download_for_nonempty_object(boto3_store):
    _serve_boto3_object(boto3_store, b"")

    with pytest.raises(OSError, match="downloaded object size"):
        boto3_store._download("object")

    _assert_nothing_published(boto3_store)


def test_boto3_preserves_legitimate_empty_remote_object(boto3_store):
    _serve_boto3_object(boto3_store, b"", remote_size=0)

    assert boto3_store._download("object")
    assert (_cache(boto3_store) / "object").read_bytes() == b""


def test_legacy_s3_axel_download_is_size_checked(legacy_store, monkeypatch):
    legacy_store.use_axel = True
    legacy_store._bucket.get_key.return_value.size = len(REMOTE_CONTENT)
    legacy_store._bucket.get_key.return_value.generate_url.return_value = "https://example.org/object"

    def axel_download_that_writes_nothing(_url, path):
        Path(path).write_bytes(b"")
        return True

    monkeypatch.setattr(legacy_store, "_axel_download", axel_download_that_writes_nothing)

    with pytest.raises(OSError, match="downloaded object size"):
        legacy_store._download("object")

    _assert_nothing_published(legacy_store)


def test_interrupted_download_cleans_temporary_file(boto3_store):
    cache_path = str(_cache(boto3_store) / "object")

    with pytest.raises(KeyboardInterrupt):
        with boto3_store._atomic_download(cache_path, len(REMOTE_CONTENT)) as tmp:
            Path(tmp).write_bytes(REMOTE_CONTENT[:5])
            raise KeyboardInterrupt()

    _assert_nothing_published(boto3_store)


def test_failed_download_does_not_remove_concurrently_published_file():
    with StoreConfig(BOTO3_CONFIG, clazz=FailedDownloadBoto3ObjectStore) as (_, store):
        store._ensure_staging_path_writable()
        (_cache(store) / "object").write_bytes(REMOTE_CONTENT)

        assert not store._pull_into_cache("object")
        assert (_cache(store) / "object").read_bytes() == REMOTE_CONTENT


def test_concurrent_downloads_use_distinct_temp_files_and_failure_cannot_replace_success(boto3_store):
    cache_path = str(_cache(boto3_store) / "object")

    with boto3_store._atomic_download(cache_path, len(REMOTE_CONTENT)) as first_tmp:
        with pytest.raises(OSError, match="downloaded object size"):
            with boto3_store._atomic_download(cache_path, len(REMOTE_CONTENT)) as second_tmp:
                assert second_tmp != first_tmp
                Path(second_tmp).write_bytes(REMOTE_CONTENT[:5])
        Path(first_tmp).write_bytes(REMOTE_CONTENT)

    assert (_cache(boto3_store) / "object").read_bytes() == REMOTE_CONTENT
    assert not list(_cache(boto3_store).rglob("*.tmp"))


def test_boto3_directory_download_uses_listed_sizes_without_head_requests(boto3_store):
    contents = {"dataset_1_files/a.txt": REMOTE_CONTENT, "dataset_1_files/sub/b.txt": b""}
    boto3_store._client.get_paginator.return_value.paginate.return_value = [
        {"Contents": [{"Key": key, "Size": len(content)} for key, content in contents.items()]}
    ]
    boto3_store._client.download_file.side_effect = lambda _bucket, key, filename, **_: Path(filename).write_bytes(
        contents[key]
    )
    cache_dir = _cache(boto3_store) / "dataset_1_files"

    boto3_store._download_directory_into_cache("dataset_1_files", str(cache_dir))

    boto3_store._client.head_object.assert_not_called()
    assert (cache_dir / "a.txt").read_bytes() == REMOTE_CONTENT
    assert (cache_dir / "sub" / "b.txt").read_bytes() == b""
    assert not list(_cache(boto3_store).rglob("*.tmp"))
