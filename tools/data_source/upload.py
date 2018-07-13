#!/usr/bin/env python
# Processes uploads from the user.

# WARNING: Changes in this tool (particularly as related to parsing) may need
# to be reflected in galaxy.web.controllers.tool_runner and galaxy.tools
from __future__ import print_function

import errno
import os
import shutil
import sys
from json import dump, load, loads

from six.moves.urllib.request import urlopen

from galaxy import util
from galaxy.datatypes import sniff
from galaxy.datatypes.registry import Registry
from galaxy.datatypes.upload_util import handle_upload, UploadProblemException

assert sys.version_info[:2] >= (2, 7)


def file_err(msg, dataset):
    # never remove a server-side upload
    if dataset.type not in ('server_dir', 'path_paste'):
        try:
            os.remove(dataset.path)
        except Exception:
            pass
    return dict(type='dataset',
                ext='data',
                dataset_id=dataset.dataset_id,
                stderr=msg,
                failed=True)


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


def add_file(dataset, registry, output_path):
    ext = None
    compression_type = None
    line_count = None
    link_data_only_str = dataset.get('link_data_only', 'copy_files')
    if link_data_only_str not in ['link_to_files', 'copy_files']:
        raise UploadProblemException("Invalid setting '%s' for option link_data_only - upload request misconfigured" % link_data_only_str)
    link_data_only = link_data_only_str == 'link_to_files'

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
        dataset.file_type
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

    stdout, ext, datatype, is_binary, converted_path = handle_upload(
        registry=registry,
        path=dataset.path,
        requested_ext=dataset.file_type,
        name=dataset.name,
        tmp_prefix='data_id_%s_upload_' % dataset.dataset_id,
        tmp_dir=output_adjacent_tmpdir(output_path),
        check_content=check_content,
        link_data_only=link_data_only,
        in_place=in_place,
        auto_decompress=auto_decompress,
        convert_to_posix_lines=dataset.to_posix_lines,
        convert_spaces_to_tabs=dataset.space_to_tab,
    )

    # Strip compression extension from name
    if compression_type and not getattr(datatype, 'compressed', False) and dataset.name.endswith('.' + compression_type):
        dataset.name = dataset.name[:-len('.' + compression_type)]

    # Move dataset
    if link_data_only:
        # Never alter a file that will not be copied to Galaxy's local file store.
        if datatype.dataset_content_needs_grooming(dataset.path):
            err_msg = 'The uploaded files need grooming, so change your <b>Copy data into Galaxy?</b> selection to be ' + \
                '<b>Copy files into Galaxy</b> instead of <b>Link to files without copying into Galaxy</b> so grooming can be performed.'
            raise UploadProblemException(err_msg)
    if not link_data_only:
        # Move the dataset to its "real" path. converted_path is a tempfile so we move it even if purge_source is False.
        if purge_source or converted_path:
            try:
                # If user has indicated that the original file to be purged and have converted_path tempfile
                if purge_source and converted_path:
                    shutil.move(converted_path, output_path)
                    os.remove(dataset.path)
                else:
                    shutil.move(converted_path or dataset.path, output_path)
            except OSError as e:
                # We may not have permission to remove the input
                if e.errno != errno.EACCES:
                    raise
        else:
            shutil.copy(dataset.path, output_path)

    # Write the job info
    stdout = stdout or 'uploaded %s file' % ext
    info = dict(type='dataset',
                dataset_id=dataset.dataset_id,
                ext=ext,
                stdout=stdout,
                name=dataset.name,
                line_count=line_count)
    if dataset.get('uuid', None) is not None:
        info['uuid'] = dataset.get('uuid')
    # FIXME: does this belong here? also not output-adjacent-tmpdir aware =/
    if not link_data_only and datatype and datatype.dataset_content_needs_grooming(output_path):
        # Groom the dataset content if necessary
        datatype.groom_dataset_content(output_path)
    return info


def add_composite_file(dataset, output_path, files_path):
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
    return dict(type='dataset',
                dataset_id=dataset.dataset_id,
                stdout='uploaded %s file' % dataset.file_type)


def __read_paramfile(path):
    with open(path) as fh:
        obj = load(fh)
    # If there's a single dataset in an old-style paramfile it'll still parse, but it'll be a dict
    assert type(obj) == list
    return obj


def __read_old_paramfile(path):
    datasets = []
    with open(path) as fh:
        for line in fh:
            datasets.append(loads(line))
    return datasets


def __write_job_metadata(metadata):
    # TODO: make upload/set_metadata compatible with https://github.com/galaxyproject/galaxy/pull/4437
    with open('galaxy.json', 'w') as fh:
        for meta in metadata:
            dump(meta, fh)
            fh.write('\n')


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

    registry = Registry()
    registry.load_datatypes(root_dir=sys.argv[1], config=sys.argv[2])

    try:
        datasets = __read_paramfile(sys.argv[3])
    except (ValueError, AssertionError):
        datasets = __read_old_paramfile(sys.argv[3])

    metadata = []
    for dataset in datasets:
        dataset = util.bunch.Bunch(**safe_dict(dataset))
        try:
            output_path = output_paths[int(dataset.dataset_id)][0]
        except Exception:
            print('Output path for dataset %s not found on command line' % dataset.dataset_id, file=sys.stderr)
            sys.exit(1)
        try:
            if dataset.type == 'composite':
                files_path = output_paths[int(dataset.dataset_id)][1]
                metadata.append(add_composite_file(dataset, output_path, files_path))
            else:
                metadata.append(add_file(dataset, registry, output_path))
        except UploadProblemException as e:
            metadata.append(file_err(e.message, dataset))
    __write_job_metadata(metadata)


if __name__ == '__main__':
    __main__()
