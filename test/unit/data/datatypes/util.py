import os
import shutil
import tempfile
from contextlib import contextmanager

from galaxy.datatypes.sniff import get_test_fname
from galaxy.util.bunch import Bunch
from galaxy.util.hash_util import md5_hash_file


@contextmanager
def get_dataset(filename, index_attr='bam_index', dataset_id=1, has_data=True):
    dataset = Bunch()
    dataset.has_data = lambda: True
    dataset.id = dataset_id
    dataset.metadata = Bunch()
    with get_input_files(filename) as input_files, get_tmp_path() as index_path:
        dataset.file_name = input_files[0]
        index = Bunch()
        index.file_name = index_path
        setattr(dataset.metadata, index_attr, index)
        yield dataset


@contextmanager
def get_tmp_path(should_exist=False, suffix=''):
    _, path = tempfile.mkstemp(suffix=suffix)
    if not should_exist:
        os.remove(path)
    yield path
    try:
        os.remove(path)
    except Exception:
        pass


@contextmanager
def get_input_files(*args):
    temp_dir = tempfile.mkdtemp()
    test_files = []
    try:
        for filename in args:
            shutil.copy(get_test_fname(filename), temp_dir)
            test_files.append(os.path.join(temp_dir, filename))
        md5_sums = [md5_hash_file(f) for f in test_files]
        yield test_files
        new_md5_sums = [md5_hash_file(f) for f in test_files]
        for old_hash, new_hash, f in zip(md5_sums, new_md5_sums, test_files):
            assert old_hash == new_hash, 'Unexpected change of content for file %s' % f
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
