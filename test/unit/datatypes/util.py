import os
import shutil
import tempfile
from contextlib import contextmanager

from galaxy.datatypes.sniff import get_test_fname
from galaxy.util.bunch import Bunch


@contextmanager
def get_dataset(file, index_attr='bam_index', dataset_id=1, has_data=True):
    dataset = Bunch()
    dataset.has_data = lambda: True
    dataset.id = dataset_id
    dataset.metadata = Bunch()
    with get_input_files(file) as input_files, get_tmp_path() as index_path:
        dataset.file_name = input_files[0]
        index = Bunch()
        index.file_name = index_path
        setattr(dataset.metadata, index_attr, index)
        yield dataset


@contextmanager
def get_tmp_path():
    _, path = tempfile.mkstemp()
    os.remove(path)
    yield path
    try:
        os.remove(path)
    except Exception:
        pass


@contextmanager
def get_input_files(*args):
    # need to import here, otherwise get_test_fname is treated as a test
    temp_dir = tempfile.mkdtemp()
    test_files = []
    for file in args:
        shutil.copy(get_test_fname(file), temp_dir)
        test_files.append(os.path.join(temp_dir, file))
    yield test_files
    shutil.rmtree(temp_dir, ignore_errors=True)
