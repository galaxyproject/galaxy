"""Module of utilities for verifying test results."""

import difflib
import filecmp
import hashlib
import json
import logging
import os
import os.path
import re
import shutil
import tempfile

try:
    import pysam
except ImportError:
    pysam = None  # type: ignore[assignment]

from galaxy.tool_util.parser.util import (
    DEFAULT_DELTA,
    DEFAULT_DELTA_FRAC,
)
from galaxy.util import unicodify
from galaxy.util.compression_utils import get_fileobj
from .asserts import verify_assertions
from .test_data import TestDataResolver

log = logging.getLogger(__name__)

DEFAULT_TEST_DATA_RESOLVER = TestDataResolver()


def verify(
    item_label,
    output_content,
    attributes,
    filename=None,
    get_filecontent=None,
    get_filename=None,
    keep_outputs_dir=None,
    verify_extra_files=None,
    mode="file",
):
    """Verify the content of a test output using test definitions described by attributes.

    Throw an informative assertion error if any of these tests fail.
    """
    if get_filename is None:
        if get_filecontent is None:
            get_filecontent = DEFAULT_TEST_DATA_RESOLVER.get_filecontent

        def get_filename(filename):
            file_content = get_filecontent(filename)
            local_name = make_temp_fname(fname=filename)
            with open(local_name, "wb") as f:
                f.write(file_content)
            return local_name

    # Check assertions...
    assertions = attributes.get("assert_list", None)
    if attributes is not None and assertions is not None:
        try:
            verify_assertions(output_content, attributes["assert_list"])
        except AssertionError as err:
            errmsg = f"{item_label} different than expected\n"
            errmsg += unicodify(err)
            raise AssertionError(errmsg)

    # Verify checksum attributes...
    # works with older Galaxy style md5=<expected_sum> or cwltest
    # style checksum=<hash_type>$<hash>.
    expected_checksum_type = None
    expected_checksum = None
    if attributes is not None and attributes.get("md5", None) is not None:
        expected_checksum_type = "md5"
        expected_checksum = attributes.get("md5")
    elif attributes is not None and attributes.get("checksum", None) is not None:
        checksum_value = attributes.get("checksum", None)
        expected_checksum_type, expected_checksum = checksum_value.split("$", 1)

    if expected_checksum_type:
        try:
            _verify_checksum(output_content, expected_checksum_type, expected_checksum)
        except AssertionError as err:
            errmsg = f"{item_label} different than expected\n"
            errmsg += unicodify(err)
            raise AssertionError(errmsg)

    if attributes is None:
        attributes = {}

    # expected object might be None, so don't pull unless available
    has_expected_object = "object" in attributes
    if has_expected_object:
        assert filename is None
        expected_object = attributes.get("object")
        actual_object = json.loads(output_content)

        expected_object_type = type(expected_object)
        actual_object_type = type(actual_object)

        if expected_object_type != actual_object_type:
            message = f"Type mismatch between expected object ({expected_object_type}) and actual object ({actual_object_type})"
            raise AssertionError(message)

        if expected_object != actual_object:
            message = f"Expected object ({expected_object}) does not match actual object ({actual_object})"
            raise AssertionError(message)

    elif filename is not None:
        temp_name = make_temp_fname(fname=filename)
        with open(temp_name, "wb") as f:
            f.write(output_content)

        # If the server's env has GALAXY_TEST_SAVE, save the output file to that
        # directory.
        # This needs to be done before the call to `get_filename()` because that
        # may raise an exception if `filename` does not exist (e.g. when
        # generating a tool output file from scratch with
        # `planemo test --update_test_data`).
        if keep_outputs_dir:
            ofn = os.path.join(keep_outputs_dir, filename)
            out_dir = os.path.dirname(ofn)
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            log.debug("keep_outputs_dir: %s, ofn: %s", keep_outputs_dir, ofn)
            try:
                shutil.copy(temp_name, ofn)
            except Exception:
                log.exception("Could not save output file %s to %s", temp_name, ofn)
            else:
                log.debug("## GALAXY_TEST_SAVE=%s. saved %s", keep_outputs_dir, ofn)

        if mode == "directory":
            # if verifying a file inside a extra_files_path directory
            # filename already point to a file that exists on disk
            local_name = filename
        else:
            local_name = get_filename(filename)

        compare = attributes.get("compare", "diff")
        try:
            if attributes.get("ftype", None) in [
                "bam",
                "qname_sorted.bam",
                "qname_input_sorted.bam",
                "unsorted.bam",
                "cram",
            ]:
                try:
                    local_fh, temp_name = _bam_to_sam(local_name, temp_name)
                    local_name = local_fh.name
                except Exception as e:
                    log.warning("%s. Will compare BAM files", unicodify(e))
            if compare == "diff":
                files_diff(local_name, temp_name, attributes=attributes)
            elif compare == "re_match":
                files_re_match(local_name, temp_name, attributes=attributes)
            elif compare == "re_match_multiline":
                files_re_match_multiline(local_name, temp_name, attributes=attributes)
            elif compare == "sim_size":
                files_delta(local_name, temp_name, attributes=attributes)
            elif compare == "contains":
                files_contains(local_name, temp_name, attributes=attributes)
            else:
                raise Exception(f"Unimplemented Compare type: {compare}")
        except AssertionError as err:
            errmsg = f"{item_label} different than expected, difference (using {compare}):\n"
            errmsg += f"( {local_name} v. {temp_name} )\n"
            errmsg += unicodify(err)
            raise AssertionError(errmsg)
        finally:
            if "GALAXY_TEST_NO_CLEANUP" not in os.environ:
                os.remove(temp_name)

    if verify_extra_files:
        extra_files = attributes.get("extra_files", None)
        if extra_files:
            verify_extra_files(extra_files)


def make_temp_fname(fname=None):
    """Safe temp name - preserve the file extension for tools that interpret it."""
    suffix = os.path.split(fname)[-1]  # ignore full path
    with tempfile.NamedTemporaryFile(prefix="tmp", suffix=suffix, delete=False) as temp:
        return temp.name


def _bam_to_sam(local_name, temp_name):
    temp_local = tempfile.NamedTemporaryFile(suffix=".sam", prefix="local_bam_converted_to_sam_")
    with tempfile.NamedTemporaryFile(suffix=".sam", prefix="history_bam_converted_to_sam_", delete=False) as temp:
        try:
            pysam.view("-h", "--no-PG", "-o", temp_local.name, local_name, catch_stdout=False)
        except Exception as e:
            msg = f"Converting local (test-data) BAM to SAM failed: {unicodify(e)}"
            raise Exception(msg)
        try:
            pysam.view("-h", "--no-PG", "-o", temp.name, temp_name, catch_stdout=False)
        except Exception as e:
            msg = f"Converting history BAM to SAM failed: {unicodify(e)}"
            raise Exception(msg)
    os.remove(temp_name)
    return temp_local, temp.name


def _verify_checksum(data, checksum_type, expected_checksum_value):
    if checksum_type not in ["md5", "sha1", "sha256", "sha512"]:
        raise Exception(f"Unimplemented hash algorithm [{checksum_type}] encountered.")

    h = hashlib.new(checksum_type)
    h.update(data)
    actual_checksum_value = h.hexdigest()
    if expected_checksum_value != actual_checksum_value:
        template = "Output checksum [%s] does not match expected [%s] (using hash algorithm %s)."
        message = template % (actual_checksum_value, expected_checksum_value, checksum_type)
        raise AssertionError(message)


def files_delta(file1, file2, attributes=None):
    """Check the contents of 2 files for size differences."""
    if attributes is None:
        attributes = {}
    delta = attributes.get("delta", DEFAULT_DELTA)
    delta_frac = attributes.get("delta_frac", DEFAULT_DELTA_FRAC)
    s1 = os.path.getsize(file1)
    s2 = os.path.getsize(file2)
    if abs(s1 - s2) > delta:
        raise AssertionError(
            "Files %s=%db but %s=%db - compare by size (delta=%s) failed" % (file1, s1, file2, s2, delta)
        )
    if delta_frac is not None and not (s1 - (s1 * delta_frac) <= s2 <= s1 + (s1 * delta_frac)):
        raise AssertionError(
            "Files %s=%db but %s=%db - compare by size (delta_frac=%s) failed" % (file1, s1, file2, s2, delta_frac)
        )


def get_compressed_formats(attributes):
    attributes = attributes or {}
    decompress = attributes.get("decompress")
    # None means all compressed formats are allowed
    return None if decompress else []


def files_diff(file1, file2, attributes=None):
    """Check the contents of 2 files for differences."""
    attributes = attributes or {}

    def get_lines_diff(diff):
        count = 0
        for line in diff:
            if (line.startswith("+") and not line.startswith("+++")) or (
                line.startswith("-") and not line.startswith("---")
            ):
                count += 1
        return count

    if not filecmp.cmp(file1, file2, shallow=False):
        compressed_formats = get_compressed_formats(attributes)
        is_pdf = False
        try:
            with get_fileobj(file2, compressed_formats=compressed_formats) as fh:
                history_data = fh.readlines()
            with get_fileobj(file1, compressed_formats=compressed_formats) as fh:
                local_file = fh.readlines()
        except UnicodeDecodeError:
            if file1.endswith(".pdf") or file2.endswith(".pdf"):
                is_pdf = True
                # Replace non-Unicode characters using unicodify(),
                # difflib.unified_diff doesn't work on list of bytes
                history_data = [
                    unicodify(line) for line in get_fileobj(file2, mode="rb", compressed_formats=compressed_formats)
                ]
                local_file = [
                    unicodify(line) for line in get_fileobj(file1, mode="rb", compressed_formats=compressed_formats)
                ]
            else:
                raise AssertionError("Binary data detected, not displaying diff")
        if attributes.get("sort", False):
            local_file.sort()
            history_data.sort()
        allowed_diff_count = int(attributes.get("lines_diff", 0))
        diff = list(difflib.unified_diff(local_file, history_data, "local_file", "history_data"))
        diff_lines = get_lines_diff(diff)
        if diff_lines > allowed_diff_count:
            if "GALAXY_TEST_RAW_DIFF" in os.environ:
                diff_slice = diff
            else:
                if len(diff) < 60:
                    diff_slice = diff[0:40]
                else:
                    diff_slice = diff[:25] + ["********\n", "*SNIP *\n", "********\n"] + diff[-25:]
            # FIXME: This pdf stuff is rather special cased and has not been updated to consider lines_diff
            # due to unknown desired behavior when used in conjunction with a non-zero lines_diff
            # PDF forgiveness can probably be handled better by not special casing by __extension__ here
            # and instead using lines_diff or a regular expression matching
            # or by creating and using a specialized pdf comparison function
            if is_pdf:
                # PDF files contain creation dates, modification dates, ids and descriptions that change with each
                # new file, so we need to handle these differences.  As long as the rest of the PDF file does
                # not differ we're ok.
                valid_diff_strs = ["description", "createdate", "creationdate", "moddate", "id", "producer", "creator"]
                valid_diff = False
                invalid_diff_lines = 0
                for line in diff_slice:
                    # Make sure to lower case strings before checking.
                    line = line.lower()
                    # Diff lines will always start with a + or - character, but handle special cases: '--- local_file \n', '+++ history_data \n'
                    if (
                        (line.startswith("+") or line.startswith("-"))
                        and line.find("local_file") < 0
                        and line.find("history_data") < 0
                    ):
                        for vdf in valid_diff_strs:
                            if line.find(vdf) < 0:
                                valid_diff = False
                            else:
                                valid_diff = True
                                # Stop checking as soon as we know we have a valid difference
                                break
                        if not valid_diff:
                            invalid_diff_lines += 1
                log.info(
                    "## files diff on '%s' and '%s': lines_diff = %d, found diff = %d, found pdf invalid diff = %d"
                    % (file1, file2, allowed_diff_count, diff_lines, invalid_diff_lines)
                )
                if invalid_diff_lines > allowed_diff_count:
                    # Print out diff_slice so we can see what failed
                    log.info("###### diff_slice ######")
                    raise AssertionError("".join(diff_slice))
            else:
                log.info(
                    "## files diff on '%s' and '%s': lines_diff = %d, found diff = %d"
                    % (file1, file2, allowed_diff_count, diff_lines)
                )
                raise AssertionError("".join(diff_slice))


def files_re_match(file1, file2, attributes=None):
    """Check the contents of 2 files for differences using re.match."""
    attributes = attributes or {}
    join_char = ""
    to_strip = os.linesep
    compressed_formats = get_compressed_formats(attributes)
    try:
        with get_fileobj(file2, compressed_formats=compressed_formats) as fh:
            history_data = fh.readlines()
        with get_fileobj(file1, compressed_formats=compressed_formats) as fh:
            local_file = fh.readlines()
    except UnicodeDecodeError:
        join_char = b""
        to_strip = os.linesep.encode("utf-8")
        with open(file2, "rb") as fh:
            history_data = fh.readlines()
        with open(file1, "rb") as fh:
            local_file = fh.readlines()
    assert len(local_file) == len(history_data), (
        "Data File and Regular Expression File contain a different number of lines (%d != %d)\nHistory Data (first 40 lines):\n%s"
        % (len(local_file), len(history_data), join_char.join(history_data[:40]))
    )
    if attributes.get("sort", False):
        history_data.sort()
    lines_diff = int(attributes.get("lines_diff", 0))
    line_diff_count = 0
    diffs = []
    for regex_line, data_line in zip(local_file, history_data):
        regex_line = regex_line.rstrip(to_strip)
        data_line = data_line.rstrip(to_strip)
        if not re.match(regex_line, data_line):
            line_diff_count += 1
            diffs.append(f"Regular Expression: {regex_line}, Data file: {data_line}\n")
    if line_diff_count > lines_diff:
        raise AssertionError(
            "Regular expression did not match data file (allowed variants=%i):\n%s" % (lines_diff, "".join(diffs))
        )


def files_re_match_multiline(file1, file2, attributes=None):
    """Check the contents of 2 files for differences using re.match in multiline mode."""
    attributes = attributes or {}
    join_char = ""
    compressed_formats = get_compressed_formats(attributes)
    try:
        with get_fileobj(file2, compressed_formats=compressed_formats) as fh:
            history_data = fh.readlines()
        with get_fileobj(file1, compressed_formats=compressed_formats) as fh:
            local_file = fh.read()
    except UnicodeDecodeError:
        join_char = b""
        with open(file2, "rb") as fh:
            history_data = fh.readlines()
        with open(file1, "rb") as fh:
            local_file = fh.read()
    if attributes.get("sort", False):
        history_data.sort()
    history_data = join_char.join(history_data)
    # lines_diff not applicable to multiline matching
    assert re.match(local_file, history_data, re.MULTILINE), "Multiline Regular expression did not match data file"


def files_contains(file1, file2, attributes=None):
    """Check the contents of file2 for substrings found in file1, on a per-line basis."""
    # TODO: allow forcing ordering of contains
    attributes = attributes or {}
    to_strip = os.linesep
    compressed_formats = get_compressed_formats(attributes)
    try:
        with get_fileobj(file2, compressed_formats=compressed_formats) as fh:
            history_data = fh.read()
        with get_fileobj(file1, compressed_formats=compressed_formats) as fh:
            local_file = fh.readlines()
    except UnicodeDecodeError:
        to_strip = os.linesep.encode("utf-8")
        with open(file2, "rb") as fh:
            history_data = fh.read()
        with open(file1, "rb") as fh:
            local_file = fh.readlines()
    lines_diff = int(attributes.get("lines_diff", 0))
    line_diff_count = 0
    for contains in local_file:
        contains = contains.rstrip(to_strip)
        if contains not in history_data:
            line_diff_count += 1
        if line_diff_count > lines_diff:
            raise AssertionError(f"Failed to find '{contains}' in history data. (lines_diff={lines_diff}).")
