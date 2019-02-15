"""Module of utilities for verifying test results."""

import difflib
import filecmp
import hashlib
import io
import logging
import os
import re
import shutil
import tempfile

try:
    import pysam
except ImportError:
    pysam = None

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
    keep_outputs_dir=None,
    verify_extra_files=None,
    mode='file',
):
    """Verify the content of a test output using test definitions described by attributes.

    Throw an informative assertion error if any of these tests fail.
    """
    if get_filecontent is None:
        get_filecontent = DEFAULT_TEST_DATA_RESOLVER.get_filecontent

    # Check assertions...
    assertions = attributes.get("assert_list", None)
    if attributes is not None and assertions is not None:
        try:
            verify_assertions(output_content, attributes["assert_list"])
        except AssertionError as err:
            errmsg = '%s different than expected\n' % (item_label)
            errmsg += str(err)
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
            errmsg = '%s different than expected\n' % (item_label)
            errmsg += str(err)
            raise AssertionError(errmsg)

    if attributes is None:
        attributes = {}

    if filename is not None:
        if mode == 'directory':
            # if verifying a file inside a extra_files_path directory
            # filename already point to a file that exists on disk
            local_name = filename
        else:
            file_content = get_filecontent(filename)
            local_name = make_temp_fname(fname=filename)
            with open(local_name, 'wb') as f:
                f.write(file_content)
        temp_name = make_temp_fname(fname=filename)
        with open(temp_name, 'wb') as f:
            f.write(output_content)

        # if the server's env has GALAXY_TEST_SAVE, save the output file to that dir
        if keep_outputs_dir:
            ofn = os.path.join(keep_outputs_dir, filename)
            log.debug('keep_outputs_dir: %s, ofn: %s', keep_outputs_dir, ofn)
            try:
                shutil.copy(temp_name, ofn)
            except Exception as exc:
                error_log_msg = 'Could not save output file %s to %s: ' % (temp_name, ofn)
                error_log_msg += str(exc)
                log.error(error_log_msg, exc_info=True)
            else:
                log.debug('## GALAXY_TEST_SAVE=%s. saved %s' % (keep_outputs_dir, ofn))
        try:
            compare = attributes.get('compare', 'diff')
            if attributes.get('ftype', None) in ['bam', 'qname_sorted.bam', 'qname_input_sorted.bam', 'unsorted.bam']:
                local_fh, temp_name = _bam_to_sam(local_name, temp_name)
                local_name = local_fh.name
            if compare == 'diff':
                files_diff(local_name, temp_name, attributes=attributes)
            elif compare == 're_match':
                files_re_match(local_name, temp_name, attributes=attributes)
            elif compare == 're_match_multiline':
                files_re_match_multiline(local_name, temp_name, attributes=attributes)
            elif compare == 'sim_size':
                delta = attributes.get('delta', '100')
                s1 = len(output_content)
                s2 = os.path.getsize(local_name)
                if abs(s1 - s2) > int(delta):
                    raise AssertionError('Files %s=%db but %s=%db - compare by size (delta=%s) failed' % (temp_name, s1, local_name, s2, delta))
            elif compare == "contains":
                files_contains(local_name, temp_name, attributes=attributes)
            else:
                raise Exception('Unimplemented Compare type: %s' % compare)
        except AssertionError as err:
            errmsg = '%s different than expected, difference (using %s):\n' % (item_label, compare)
            errmsg += "( %s v. %s )\n" % (local_name, temp_name)
            errmsg += str(err)
            raise AssertionError(errmsg)
        finally:
            if 'GALAXY_TEST_NO_CLEANUP' not in os.environ:
                os.remove(temp_name)

    if verify_extra_files:
        extra_files = attributes.get('extra_files', None)
        if extra_files:
            verify_extra_files(extra_files)


def make_temp_fname(fname=None):
    """Safe temp name - preserve the file extension for tools that interpret it."""
    suffix = os.path.split(fname)[-1]  # ignore full path
    fd, temp_prefix = tempfile.mkstemp(prefix='tmp', suffix=suffix)
    return temp_prefix


def _bam_to_sam(local_name, temp_name):
    temp_local = tempfile.NamedTemporaryFile(suffix='.sam', prefix='local_bam_converted_to_sam_')
    fd, temp_temp = tempfile.mkstemp(suffix='.sam', prefix='history_bam_converted_to_sam_')
    os.close(fd)
    try:
        pysam.view('-h', '-o%s' % temp_local.name, local_name)
    except Exception as e:
        raise Exception("Converting local (test-data) BAM to SAM failed: %s" % e)
    try:
        pysam.view('-h', '-o%s' % temp_temp, temp_name)
    except Exception as e:
        raise Exception("Converting history BAM to SAM failed: %s" % e)
    os.remove(temp_name)
    return temp_local, temp_temp


def _verify_checksum(data, checksum_type, expected_checksum_value):
    if checksum_type not in ["md5", "sha1", "sha256", "sha512"]:
        raise Exception("Unimplemented hash algorithm [%s] encountered." % checksum_type)

    h = hashlib.new(checksum_type)
    h.update(data)
    actual_checksum_value = h.hexdigest()
    if expected_checksum_value != actual_checksum_value:
        template = "Output checksum [%s] does not match expected [%s] (using hash algorithm %s)."
        message = template % (actual_checksum_value, expected_checksum_value, checksum_type)
        raise AssertionError(message)


def files_diff(file1, file2, attributes=None):
    """Check the contents of 2 files for differences."""
    def get_lines_diff(diff):
        count = 0
        for line in diff:
            if (line.startswith('+') and not line.startswith('+++')) or (line.startswith('-') and not line.startswith('---')):
                count += 1
        return count

    if not filecmp.cmp(file1, file2):
        if attributes is None:
            attributes = {}
        decompress = attributes.get("decompress", None)
        if decompress:
            # None means all compressed formats are allowed
            compressed_formats = None
        else:
            compressed_formats = []
        is_pdf = False
        try:
            local_file = get_fileobj(file1, compressed_formats=compressed_formats).readlines()
            history_data = get_fileobj(file2, compressed_formats=compressed_formats).readlines()
        except UnicodeDecodeError:
            if file1.endswith('.pdf') or file2.endswith('.pdf'):
                is_pdf = True
                local_file = open(file1, 'rb').readlines()
                history_data = open(file2, 'rb').readlines()
            else:
                raise AssertionError("Binary data detected, not displaying diff")
        if attributes.get('sort', False):
            local_file.sort()
            history_data.sort()
        allowed_diff_count = int(attributes.get('lines_diff', 0))
        diff = list(difflib.unified_diff(local_file, history_data, "local_file", "history_data"))
        diff_lines = get_lines_diff(diff)
        if diff_lines > allowed_diff_count:
            if 'GALAXY_TEST_RAW_DIFF' in os.environ:
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
                valid_diff_strs = ['description', 'createdate', 'creationdate', 'moddate', 'id', 'producer', 'creator']
                valid_diff = False
                invalid_diff_lines = 0
                for line in diff_slice:
                    # Make sure to lower case strings before checking.
                    line = line.lower()
                    # Diff lines will always start with a + or - character, but handle special cases: '--- local_file \n', '+++ history_data \n'
                    if (line.startswith('+') or line.startswith('-')) and line.find('local_file') < 0 and line.find('history_data') < 0:
                        for vdf in valid_diff_strs:
                            if line.find(vdf) < 0:
                                valid_diff = False
                            else:
                                valid_diff = True
                                # Stop checking as soon as we know we have a valid difference
                                break
                        if not valid_diff:
                            invalid_diff_lines += 1
                log.info("## files diff on '%s' and '%s': lines_diff = %d, found diff = %d, found pdf invalid diff = %d" % (file1, file2, allowed_diff_count, diff_lines, invalid_diff_lines))
                if invalid_diff_lines > allowed_diff_count:
                    # Print out diff_slice so we can see what failed
                    log.info("###### diff_slice ######")
                    raise AssertionError("".join(diff_slice))
            else:
                log.info("## files diff on '%s' and '%s': lines_diff = %d, found diff = %d" % (file1, file2, allowed_diff_count, diff_lines))
                raise AssertionError("".join(diff_slice))


def files_re_match(file1, file2, attributes=None):
    """Check the contents of 2 files for differences using re.match."""
    local_file = io.open(file1, encoding='utf-8').readlines()  # regex file
    history_data = io.open(file2, encoding='utf-8').readlines()
    assert len(local_file) == len(history_data), 'Data File and Regular Expression File contain a different number of lines (%d != %d)\nHistory Data (first 40 lines):\n%s' % (len(local_file), len(history_data), ''.join(history_data[:40]))
    if attributes is None:
        attributes = {}
    if attributes.get('sort', False):
        history_data.sort()
    lines_diff = int(attributes.get('lines_diff', 0))
    line_diff_count = 0
    diffs = []
    for i in range(len(history_data)):
        if not re.match(local_file[i].rstrip('\r\n'), history_data[i].rstrip('\r\n')):
            line_diff_count += 1
            diffs.append('Regular Expression: %s\nData file         : %s' % (local_file[i].rstrip('\r\n'), history_data[i].rstrip('\r\n')))
        if line_diff_count > lines_diff:
            raise AssertionError("Regular expression did not match data file (allowed variants=%i):\n%s" % (lines_diff, "".join(diffs)))


def files_re_match_multiline(file1, file2, attributes=None):
    """Check the contents of 2 files for differences using re.match in multiline mode."""
    local_file = io.open(file1, encoding='utf-8').read()  # regex file
    if attributes is None:
        attributes = {}
    if attributes.get('sort', False):
        history_data = io.open(file2, encoding='utf-8').readlines()
        history_data.sort()
        history_data = ''.join(history_data)
    else:
        history_data = io.open(file2, encoding='utf-8').read()
    # lines_diff not applicable to multiline matching
    assert re.match(local_file, history_data, re.MULTILINE), "Multiline Regular expression did not match data file"


def files_contains(file1, file2, attributes=None):
    """Check the contents of file2 for substrings found in file1, on a per-line basis."""
    local_file = io.open(file1, encoding='utf-8').readlines()  # regex file
    # TODO: allow forcing ordering of contains
    history_data = io.open(file2, encoding='utf-8').read()
    lines_diff = int(attributes.get('lines_diff', 0))
    line_diff_count = 0
    while local_file:
        contains = local_file.pop(0).rstrip('\n\r')
        if contains not in history_data:
            line_diff_count += 1
        if line_diff_count > lines_diff:
            raise AssertionError("Failed to find '%s' in history data. (lines_diff=%i):\n" % (contains, lines_diff))
