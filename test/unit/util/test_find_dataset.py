import os
import tempfile

from galaxy.util import find_dataset


def test_find_dataset_no_dir():
    assert find_dataset('no-such-path') is None


def test_find_dataset_no_dat_file():
    with tempfile.TemporaryDirectory() as td_name:
        td1 = tempfile.TemporaryDirectory(dir=td_name)
        tempfile.mkstemp(suffix='.not-dat', dir=td1.name)
        assert find_dataset(td_name) is None


def test_find_dataset_exists():
    with tempfile.TemporaryDirectory() as td_name:
        td1 = tempfile.TemporaryDirectory(dir=td_name)
        f = tempfile.NamedTemporaryFile(suffix='.dat', dir=td1.name)

        direntry = find_dataset(td_name)
        assert direntry.name == os.path.basename(f.name)
