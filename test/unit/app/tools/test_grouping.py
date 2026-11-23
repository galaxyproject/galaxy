from typing import Any

import pytest

from galaxy.datatypes.registry import Registry
from galaxy.tools.parameters.grouping import UploadDataset
from galaxy.util.bunch import Bunch


def test_force_composite_preserves_distinct_member_names(tmp_path):
    registry = Registry()
    registry.load_datatypes()
    trans = Bunch(app=Bunch(datatypes_registry=registry))
    upload = UploadDataset(name="files")
    names = ["sample-1.txt", "sample_1.txt", "sample 1.txt"]
    files = []
    for name in ["primary.txt", *names]:
        path = tmp_path / name
        path.write_text(f"Content for {name}\n")
        files.append(
            {
                "NAME": name,
                "file_data": {"local_filename": str(path), "filename": name},
                "file_type": "txt",
                "dbkey": "?",
                "url_paste": None,
                "ftp_files": None,
            }
        )
    context = {"files": files, "file_type": "txt", "file_count": len(files), "force_composite": True}

    (dataset,) = upload.get_uploaded_datasets(trans, context)

    assert set(dataset.composite_files) == set(names)
    for name in names:
        assert dataset.composite_files[name]["path"] == str(tmp_path / name)


_URLS_WITH_USERINFO = [
    ("https://fetchuser:s3cret@example.org/a.bed", "https://example.org/a.bed"),
    (
        "https://example.org/a.bed?next=ftp://fetchuser:s3cret@inner.example.org/b",
        "https://example.org/a.bed?next=ftp://inner.example.org/b",
    ),
    (
        "https://example.org/a.bed?next=//fetchuser:s3cret@inner.example.org/b",
        "https://example.org/a.bed?next=//inner.example.org/b",
    ),
]


def _url_paste_context(tmp_path, urls, **kwds):
    file_contexts: list[dict[str, Any]] = []
    for index, url in enumerate(urls):
        url_paste = tmp_path / f"url_paste_{index}"
        url_paste.write_text(f"{url}\n")
        file_contexts.append(
            {"file_data": {}, "url_paste": str(url_paste), "ftp_files": None, "dbkey": "?", "file_type": "txt"}
        )
    return {"files": file_contexts, "file_type": "txt", "file_count": len(urls), **kwds}


def _registry_trans():
    registry = Registry()
    registry.load_datatypes()
    return Bunch(app=Bunch(datatypes_registry=registry))


@pytest.mark.parametrize(("url", "expected_name"), _URLS_WITH_USERINFO)
def test_url_paste_dataset_name_hides_userinfo(tmp_path, url, expected_name):
    (dataset,) = UploadDataset(name="files").get_uploaded_datasets(
        _registry_trans(), _url_paste_context(tmp_path, [url])
    )

    assert dataset.path == url
    assert dataset.name == expected_name


@pytest.mark.parametrize(("url", "expected_name"), _URLS_WITH_USERINFO)
def test_composite_url_paste_file_name_hides_userinfo(tmp_path, url, expected_name):
    # The first file is the primary one, the second a composite member.
    context = _url_paste_context(tmp_path, [url, url], force_composite=True)

    (dataset,) = UploadDataset(name="files").get_uploaded_datasets(_registry_trans(), context)

    assert dataset.primary_file == url
    (composite_file,) = dataset.composite_files.values()
    assert composite_file["path"] == url
    assert composite_file["name"] == expected_name
