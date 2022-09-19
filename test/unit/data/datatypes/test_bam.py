from pysam import (  # type: ignore[attr-defined]
    AlignmentFile,
    view,
)

from galaxy.datatypes.binary import Bam
from .util import (
    get_dataset,
    get_input_files,
    get_tmp_path,
)


def test_merge_bam():
    with get_input_files("1.bam", "1.bam") as input_files, get_tmp_path() as outpath:
        Bam.merge(input_files, outpath)
        alignment_count_output = int(view("-c", outpath).strip())
        alignment_count_input = int(view("-c", input_files[0]).strip()) * 2
        assert alignment_count_input == alignment_count_output


def test_dataset_content_needs_grooming():
    b = Bam()
    with get_input_files("1.bam", "2.shuffled.unsorted.bam") as input_files:
        sorted_bam, shuffled_bam = input_files
        assert b.dataset_content_needs_grooming(sorted_bam) is False
        assert b.dataset_content_needs_grooming(shuffled_bam) is True


def test_groom_dataset_content():
    b = Bam()
    try:
        with get_input_files("2.shuffled.unsorted.bam") as input_files:
            b.groom_dataset_content(input_files[0])
            assert b.dataset_content_needs_grooming(input_files[0]) is False
    except AssertionError as e:
        # Grooming modifies files in-place, so the md5 hash comparison has to fail
        assert "Unexpected change" in str(e)
        return
    # should not reach this part of the test
    raise Exception("Bam grooming did not occur in-place")


def test_set_meta_presorted():
    b = Bam()
    with get_dataset("1.bam") as dataset:
        b.set_meta(dataset=dataset)
        assert dataset.metadata.sort_order == "coordinate"
        bam_file = AlignmentFile(dataset.file_name, mode="rb", index_filename=dataset.metadata.bam_index.file_name)
        assert bam_file.has_index() is True


def test_set_meta_header_info():
    """
    check if information from the bam header is set
    as metadata
    """
    b = Bam()
    with get_dataset("bam_from_sam.bam") as dataset:
        b.set_meta(dataset=dataset)
        assert dataset.metadata.bam_header == {
            "HD": {"VN": "1.3", "SO": "coordinate"},
            "SQ": [{"SN": "ref", "LN": 45}, {"SN": "ref2", "LN": 40}],
        }
        assert dataset.metadata.reference_names == ["ref", "ref2"]
