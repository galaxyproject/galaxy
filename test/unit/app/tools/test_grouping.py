from typing import cast

from galaxy.datatypes.registry import Registry
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.tools.parameters.grouping import UploadDataset
from galaxy.util.bunch import Bunch


def test_force_composite_preserves_distinct_member_names(tmp_path):
    registry = Registry()
    registry.load_datatypes()
    trans = cast(ProvidesHistoryContext, Bunch(app=Bunch(datatypes_registry=registry)))
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
