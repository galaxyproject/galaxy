#!/usr/bin/env python
# Processes uploads from the user.

# WARNING: Changes in this tool (particularly as related to parsing) may need
# to be reflected in galaxy.web.controllers.tool_runner and galaxy.tools
from __future__ import print_function

import errno
import gzip
import os
import shutil
import sys
import tempfile
import zipfile
from json import dumps, loads

from six.moves.urllib.request import urlopen

from galaxy import util
from galaxy.datatypes import sniff
from galaxy.datatypes.registry import Registry
from galaxy.datatypes.upload_util import (
    handle_sniffable_binary_check,
    handle_unsniffable_binary_check,
    UploadProblemException,
)
from galaxy.util.checkers import (
    check_binary,
    check_bz2,
    check_gzip,
    check_html,
    check_zip
)

if sys.version_info < (3, 3):
    import bz2file as bz2
else:
    import bz2

assert sys.version_info[:2] >= (2, 7)


def file_err(msg, dataset, json_file):
    json_file.write(dumps(dict(type='dataset',
                               ext='data',
                               dataset_id=dataset.dataset_id,
                               stderr=msg,
                               failed=True)) + "\n")
    # never remove a server-side upload
    if dataset.type in ('server_dir', 'path_paste'):
        return
    try:
        os.remove(dataset.path)
    except Exception:
        pass


def safe_dict(d):
    """
    Recursively clone json structure with UTF-8 dictionary keys
    http://mellowmachines.com/blog/2009/06/exploding-dictionary-with-unicode-keys-as-python-arguments/
    """
    if isinstance(d, dict):
        return dict([(k.encode('utf-8'), safe_dict(v)) for k, v in d.items()])
    elif isinstance(d, list):
        return [safe_dict(x) for x in d]
    else:
        return d


def parse_outputs(args):
    rval = {}
    for arg in args:
        id, files_path, path = arg.split(':', 2)
        rval[int(id)] = (path, files_path)
    return rval


def add_file(dataset, registry, json_file, output_path):
    data_type = None
    line_count = None
    converted_path = None
    stdout = None
    link_data_only_str = dataset.get('link_data_only', 'copy_files')
    if link_data_only_str not in ['link_data_only', 'copy_files']:
        raise UploadProblemException("Invalid setting for option link_data_only - upload request misconfigured.")
    link_data_only = link_data_only_str == 'link_data_only'

    # run_as_real_user is estimated from galaxy config (external chmod indicated of inputs executed)
    # If this is True we always purge supplied upload inputs so they are cleaned up and we reuse their
    # paths during data conversions since this user already owns that path.
    # Older in_place check for upload jobs created before 18.01, TODO remove in 19.XX. xref #5206
    run_as_real_user = dataset.get('run_as_real_user', False) or dataset.get("in_place", False)

    # purge_source defaults to True unless this is an FTP import and
    # ftp_upload_purge has been overridden to False in Galaxy's config.
    # We set purge_source to False if:
    # - the job does not have write access to the file, e.g. when running as the
    #   real user
    # - the files are uploaded from external paths.
    purge_source = dataset.get('purge_source', True) and not run_as_real_user and dataset.type not in ('server_dir', 'path_paste')

    # in_place is True unless we are running as a real user or importing external paths (i.e.
    # this is a real upload and not a path paste or ftp import).
    # in_place should always be False if running as real user because the uploaded file will
    # be owned by Galaxy and not the user and it should be False for external paths so Galaxy doesn't
    # modify files not controlled by Galaxy.
    in_place = not run_as_real_user and dataset.type not in ('server_dir', 'path_paste', 'ftp_import')

    # Base on the check_upload_content Galaxy config option and on by default, this enables some
    # security related checks on the uploaded content, but can prevent uploads from working in some cases.
    check_content = dataset.get('check_content' , True)

    # auto_decompress is a request flag that can be swapped off to prevent Galaxy from automatically
    # decompressing archive files before sniffing.
    auto_decompress = dataset.get('auto_decompress', True)
    try:
        ext = dataset.file_type
    except AttributeError:
        raise UploadProblemException('Unable to process uploaded file, missing file_type parameter.')

    if dataset.type == 'url':
        try:
            dataset.path = sniff.stream_url_to_file(dataset.path)
        except Exception as e:
            raise UploadProblemException('Unable to fetch %s\n%s' % (dataset.path, str(e)))

    # See if we have an empty file
    if not os.path.exists(dataset.path):
        raise UploadProblemException('Uploaded temporary file (%s) does not exist.' % dataset.path)

    if not os.path.getsize(dataset.path) > 0:
        raise UploadProblemException('The uploaded file is empty')

    # Is dataset content supported sniffable binary?
    is_binary = check_binary(dataset.path)
    if is_binary:
        data_type, ext = handle_sniffable_binary_check(data_type, ext, dataset.path, registry)
    if not data_type:
        root_datatype = registry.get_datatype_by_extension(dataset.file_type)
        if getattr(root_datatype, 'compressed', False):
            data_type = 'compressed archive'
            ext = dataset.file_type
        else:
            # See if we have a gzipped file, which, if it passes our restrictions, we'll uncompress
            is_gzipped, is_valid = check_gzip(dataset.path, check_content=check_content)
            if is_gzipped and not is_valid:
                raise UploadProblemException('The gzipped uploaded file contains inappropriate content')
            elif is_gzipped and is_valid and auto_decompress:
                if not link_data_only:
                    # We need to uncompress the temp_name file, but BAM files must remain compressed in the BGZF format
                    CHUNK_SIZE = 2 ** 20  # 1Mb
                    fd, uncompressed = tempfile.mkstemp(prefix='data_id_%s_upload_gunzip_' % dataset.dataset_id, dir=os.path.dirname(output_path), text=False)
                    gzipped_file = gzip.GzipFile(dataset.path, 'rb')
                    while 1:
                        try:
                            chunk = gzipped_file.read(CHUNK_SIZE)
                        except IOError:
                            os.close(fd)
                            os.remove(uncompressed)
                            raise UploadProblemException('Problem decompressing gzipped data')
                        if not chunk:
                            break
                        os.write(fd, chunk)
                    os.close(fd)
                    gzipped_file.close()
                    # Replace the gzipped file with the decompressed file if it's safe to do so
                    if not in_place:
                        dataset.path = uncompressed
                    else:
                        shutil.move(uncompressed, dataset.path)
                    os.chmod(dataset.path, 0o644)
                dataset.name = dataset.name.rstrip('.gz')
                data_type = 'gzip'
            if not data_type:
                # See if we have a bz2 file, much like gzip
                is_bzipped, is_valid = check_bz2(dataset.path, check_content)
                if is_bzipped and not is_valid:
                    raise UploadProblemException('The gzipped uploaded file contains inappropriate content')
                elif is_bzipped and is_valid and auto_decompress:
                    if not link_data_only:
                        # We need to uncompress the temp_name file
                        CHUNK_SIZE = 2 ** 20  # 1Mb
                        fd, uncompressed = tempfile.mkstemp(prefix='data_id_%s_upload_bunzip2_' % dataset.dataset_id, dir=os.path.dirname(output_path), text=False)
                        bzipped_file = bz2.BZ2File(dataset.path, 'rb')
                        while 1:
                            try:
                                chunk = bzipped_file.read(CHUNK_SIZE)
                            except IOError:
                                os.close(fd)
                                os.remove(uncompressed)
                                raise UploadProblemException('Problem decompressing bz2 compressed data')
                            if not chunk:
                                break
                            os.write(fd, chunk)
                        os.close(fd)
                        bzipped_file.close()
                        # Replace the bzipped file with the decompressed file if it's safe to do so
                        if not in_place:
                            dataset.path = uncompressed
                        else:
                            shutil.move(uncompressed, dataset.path)
                        os.chmod(dataset.path, 0o644)
                    dataset.name = dataset.name.rstrip('.bz2')
                    data_type = 'bz2'
            if not data_type:
                # See if we have a zip archive
                is_zipped = check_zip(dataset.path)
                if is_zipped and auto_decompress:
                    if not link_data_only:
                        CHUNK_SIZE = 2 ** 20  # 1Mb
                        uncompressed = None
                        uncompressed_name = None
                        unzipped = False
                        z = zipfile.ZipFile(dataset.path)
                        for name in z.namelist():
                            if name.endswith('/'):
                                continue
                            if unzipped:
                                stdout = 'ZIP file contained more than one file, only the first file was added to Galaxy.'
                                break
                            fd, uncompressed = tempfile.mkstemp(prefix='data_id_%s_upload_zip_' % dataset.dataset_id, dir=os.path.dirname(output_path), text=False)
                            if sys.version_info[:2] >= (2, 6):
                                zipped_file = z.open(name)
                                while 1:
                                    try:
                                        chunk = zipped_file.read(CHUNK_SIZE)
                                    except IOError:
                                        os.close(fd)
                                        os.remove(uncompressed)
                                        raise UploadProblemException('Problem decompressing zipped data')
                                    if not chunk:
                                        break
                                    os.write(fd, chunk)
                                os.close(fd)
                                zipped_file.close()
                                uncompressed_name = name
                                unzipped = True
                            else:
                                # python < 2.5 doesn't have a way to read members in chunks(!)
                                try:
                                    with open(uncompressed, 'wb') as outfile:
                                        outfile.write(z.read(name))
                                    uncompressed_name = name
                                    unzipped = True
                                except IOError:
                                    os.close(fd)
                                    os.remove(uncompressed)
                                    raise UploadProblemException('Problem decompressing zipped data')
                        z.close()
                        # Replace the zipped file with the decompressed file if it's safe to do so
                        if uncompressed is not None:
                            if not in_place:
                                dataset.path = uncompressed
                            else:
                                shutil.move(uncompressed, dataset.path)
                            os.chmod(dataset.path, 0o644)
                            dataset.name = uncompressed_name
                    data_type = 'zip'
            if not data_type:
                data_type, ext = handle_unsniffable_binary_check(
                    data_type, ext, dataset.path, dataset.name, is_binary, dataset.file_type, check_content, registry
                )
            if not data_type:
                # We must have a text file
                if check_content and check_html(dataset.path):
                    raise UploadProblemException('The uploaded file contains inappropriate HTML content')
            if data_type != 'binary':
                if not link_data_only and data_type not in ('gzip', 'bz2', 'zip'):
                    # Convert universal line endings to Posix line endings if to_posix_lines is True
                    # and the data is not binary or gzip-, bz2- or zip-compressed.
                    if dataset.to_posix_lines:
                        tmpdir = output_adjacent_tmpdir(output_path)
                        tmp_prefix = 'data_id_%s_convert_' % dataset.dataset_id
                        if dataset.space_to_tab:
                            line_count, converted_path = sniff.convert_newlines_sep2tabs(dataset.path, in_place=in_place, tmp_dir=tmpdir, tmp_prefix=tmp_prefix)
                        else:
                            line_count, converted_path = sniff.convert_newlines(dataset.path, in_place=in_place, tmp_dir=tmpdir, tmp_prefix=tmp_prefix)
                if dataset.file_type == 'auto':
                    ext = sniff.guess_ext(converted_path or dataset.path, registry.sniff_order)
                else:
                    ext = dataset.file_type
                data_type = ext
    # Save job info for the framework
    if ext == 'auto' and data_type == 'binary':
        ext = 'data'
    if ext == 'auto' and dataset.ext:
        ext = dataset.ext
    if ext == 'auto':
        ext = 'data'
    datatype = registry.get_datatype_by_extension(ext)
    if link_data_only:
        # Never alter a file that will not be copied to Galaxy's local file store.
        if datatype.dataset_content_needs_grooming(dataset.path):
            err_msg = 'The uploaded files need grooming, so change your <b>Copy data into Galaxy?</b> selection to be ' + \
                '<b>Copy files into Galaxy</b> instead of <b>Link to files without copying into Galaxy</b> so grooming can be performed.'
            raise UploadProblemException(err_msg)
    if not link_data_only and converted_path:
        # Move the dataset to its "real" path
        try:
            shutil.move(converted_path, output_path)
        except OSError as e:
            # We may not have permission to remove converted_path
            if e.errno != errno.EACCES:
                raise
    elif not link_data_only:
        if purge_source:
            shutil.move(dataset.path, output_path)
        else:
            shutil.copy(dataset.path, output_path)
    # Write the job info
    stdout = stdout or 'uploaded %s file' % data_type
    info = dict(type='dataset',
                dataset_id=dataset.dataset_id,
                ext=ext,
                stdout=stdout,
                name=dataset.name,
                line_count=line_count)
    if dataset.get('uuid', None) is not None:
        info['uuid'] = dataset.get('uuid')
    json_file.write(dumps(info) + "\n")
    if not link_data_only and datatype and datatype.dataset_content_needs_grooming(output_path):
        # Groom the dataset content if necessary
        datatype.groom_dataset_content(output_path)


def add_composite_file(dataset, json_file, output_path, files_path):
    if dataset.composite_files:
        os.mkdir(files_path)
        for name, value in dataset.composite_files.items():
            value = util.bunch.Bunch(**value)
            if dataset.composite_file_paths[value.name] is None and not value.optional:
                raise UploadProblemException('A required composite data file was not provided (%s)' % name)
            elif dataset.composite_file_paths[value.name] is not None:
                dp = dataset.composite_file_paths[value.name]['path']
                isurl = dp.find('://') != -1  # todo fixme
                if isurl:
                    try:
                        temp_name = sniff.stream_to_file(urlopen(dp), prefix='url_paste')
                    except Exception as e:
                        raise UploadProblemException('Unable to fetch %s\n%s' % (dp, str(e)))
                    dataset.path = temp_name
                    dp = temp_name
                if not value.is_binary:
                    tmpdir = output_adjacent_tmpdir(output_path)
                    tmp_prefix = 'data_id_%s_convert_' % dataset.dataset_id
                    if dataset.composite_file_paths[value.name].get('space_to_tab', value.space_to_tab):
                        sniff.convert_newlines_sep2tabs(dp, tmp_dir=tmpdir, tmp_prefix=tmp_prefix)
                    else:
                        sniff.convert_newlines(dp, tmp_dir=tmpdir, tmp_prefix=tmp_prefix)
                shutil.move(dp, os.path.join(files_path, name))
    # Move the dataset to its "real" path
    shutil.move(dataset.primary_file, output_path)
    # Write the job info
    info = dict(type='dataset',
                dataset_id=dataset.dataset_id,
                stdout='uploaded %s file' % dataset.file_type)
    json_file.write(dumps(info) + "\n")


def output_adjacent_tmpdir(output_path):
    """ For temp files that will ultimately be moved to output_path anyway
    just create the file directly in output_path's directory so shutil.move
    will work optimially.
    """
    return os.path.dirname(output_path)


def __main__():

    if len(sys.argv) < 4:
        print('usage: upload.py <root> <datatypes_conf> <json paramfile> <output spec> ...', file=sys.stderr)
        sys.exit(1)

    output_paths = parse_outputs(sys.argv[4:])
    json_file = open('galaxy.json', 'w')

    registry = Registry()
    registry.load_datatypes(root_dir=sys.argv[1], config=sys.argv[2])

    for line in open(sys.argv[3], 'r'):
        dataset = loads(line)
        dataset = util.bunch.Bunch(**safe_dict(dataset))
        try:
            output_path = output_paths[int(dataset.dataset_id)][0]
        except Exception:
            print('Output path for dataset %s not found on command line' % dataset.dataset_id, file=sys.stderr)
            sys.exit(1)
        try:
            if dataset.type == 'composite':
                files_path = output_paths[int(dataset.dataset_id)][1]
                add_composite_file(dataset, json_file, output_path, files_path)
            else:
                add_file(dataset, registry, json_file, output_path)
        except UploadProblemException as e:
            file_err(e.message, dataset, json_file)
    # clean up paramfile
    # TODO: this will not work when running as the actual user unless the
    # parent directory is writable by the user.
    try:
        os.remove(sys.argv[3])
    except Exception:
        pass


if __name__ == '__main__':
    __main__()
