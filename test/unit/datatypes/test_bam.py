import os
import shutil
import tempfile
from contextlib import contextmanager

import pysam

from galaxy.datatypes.binary import Bam
from galaxy.util.bunch import Bunch


def test_merge_bam():
    with get_input_files('1.bam', '1.bam') as input_files, get_tmp_path() as outpath:
        Bam.merge(input_files, outpath)
        alignment_count_output = int(pysam.view('-c', outpath).strip())
        alignment_count_input = int(pysam.view('-c', input_files[0]).strip()) * 2
        assert alignment_count_input == alignment_count_output


def test_dataset_content_needs_grooming():
    b = Bam()
    with get_input_files('1.bam') as input_files:
        assert b.dataset_content_needs_grooming(input_files[0]) is False
        with get_tmp_path() as qname_sorted:
            pysam.sort('-n', input_files[0], '-o', qname_sorted)
            assert b.dataset_content_needs_grooming(qname_sorted) is True
    with get_input_files('1.unsorted.bam') as input_files:
        assert b.dataset_content_needs_grooming(input_files[0]) is True


def test_groom_dataset_content():
    b = Bam()
    with get_input_files('1.unsorted.bam') as input_files:
        b.groom_dataset_content(input_files[0])
        assert b.dataset_content_needs_grooming(input_files[0]) is False


def test_set_meta():
    b = Bam()
    dataset = Bunch()
    with get_input_files('1.bam') as input_files, get_tmp_path() as index_path:
        dataset.file_name = input_files[0]
        dataset.metadata = Bunch()
        dataset.metadata.bam_index = Bunch()
        dataset.metadata.bam_index.file_name = index_path
        b.set_meta(dataset=dataset)
        assert dataset.metadata.sort_order == 'coordinate'
        bam_file = pysam.AlignmentFile(dataset.file_name, mode='rb',
                                       index_filename=dataset.metadata.bam_index.file_name)
        assert bam_file.has_index() is True


@contextmanager
def get_tmp_path():
    _, path = tempfile.mkstemp()
    os.remove(path)
    yield path
    os.remove(path)


@contextmanager
def get_input_files(*args):
    # need to import here, otherwise get_test_fname is treated as a test
    from galaxy.datatypes.sniff import get_test_fname
    temp_dir = tempfile.mkdtemp()
    test_files = []
    for file in args:
        shutil.copy(get_test_fname(file), temp_dir)
        test_files.append(os.path.join(temp_dir, file))
    yield test_files
    shutil.rmtree(temp_dir, ignore_errors=True)
