import gzip
import json
import logging
import os
import shutil
import sys
import tempfile
from collections import namedtuple

from sqlalchemy.sql.expression import null

from galaxy.util import checkers
from galaxy.util.path import safe_relpath
from tool_shed import repository_types as rt_util
from tool_shed.tools.data_table_manager import ShedToolDataTableManager
from tool_shed.util import basic_util, hg_util

if sys.version_info < (3, 3):
    import bz2file as bz2
else:
    import bz2

log = logging.getLogger(__name__)

UNDESIRABLE_DIRS = ['.hg', '.svn', '.git', '.cvs']
UNDESIRABLE_FILES = ['.hg_archival.txt', 'hgrc', '.DS_Store', 'tool_test_output.html', 'tool_test_output.json']


def check_archive(repository, archive):
    valid = []
    invalid = []
    errors = []
    undesirable_files = []
    undesirable_dirs = []
    for member in archive.getmembers():
        # Allow regular files and directories only
        if not (member.isdir() or member.isfile() or member.islnk()):
            errors.append("Uploaded archives can only include regular directories and files (no symbolic links, devices, etc).")
            invalid.append(member)
            continue
        if not safe_relpath(member.name):
            errors.append("Uploaded archives cannot contain files that would extract outside of the archive.")
            invalid.append(member)
            continue
        if os.path.basename(member.name) in UNDESIRABLE_FILES:
            undesirable_files.append(member)
            continue
        head = tail = member.name
        try:
            while tail:
                head, tail = os.path.split(head)
                if tail in UNDESIRABLE_DIRS:
                    undesirable_dirs.append(member)
                    assert False
        except AssertionError:
            continue
        if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION and member.name != rt_util.REPOSITORY_DEPENDENCY_DEFINITION_FILENAME:
            errors.append('Repositories of type <b>Repository suite definition</b> can contain only a single file named <b>repository_dependencies.xml</b>.')
            invalid.append(member)
            continue
        if repository.type == rt_util.TOOL_DEPENDENCY_DEFINITION and member.name != rt_util.TOOL_DEPENDENCY_DEFINITION_FILENAME:
            errors.append('Repositories of type <b>Tool dependency definition</b> can contain only a single file named <b>tool_dependencies.xml</b>.')
            invalid.append(member)
            continue
        valid.append(member)
    ArchiveCheckResults = namedtuple('ArchiveCheckResults', ['valid', 'invalid', 'undesirable_files', 'undesirable_dirs', 'errors'])
    return ArchiveCheckResults(valid, invalid, undesirable_files, undesirable_dirs, errors)


def check_file_contents_for_email_alerts(app):
    """
    See if any admin users have chosen to receive email alerts when a repository is updated.
    If so, the file contents of the update must be checked for inappropriate content.
    """
    sa_session = app.model.context.current
    admin_users = app.config.get("admin_users", "").split(",")
    for repository in sa_session.query(app.model.Repository) \
                                .filter(app.model.Repository.table.c.email_alerts != null()):
        email_alerts = json.loads(repository.email_alerts)
        for user_email in email_alerts:
            if user_email in admin_users:
                return True
    return False


def check_file_content_for_html_and_images(file_path):
    message = ''
    if checkers.check_html(file_path):
        message = 'The file "%s" contains HTML content.\n' % str(file_path)
    elif checkers.check_image(file_path):
        message = 'The file "%s" contains image content.\n' % str(file_path)
    return message


def get_change_lines_in_file_for_tag(tag, change_dict):
    """
    The received change_dict is the jsonified version of the changes to a file in a
    changeset being pushed to the Tool Shed from the command line. This method cleans
    and returns appropriate lines for inspection.
    """
    cleaned_lines = []
    data_list = change_dict.get('data', [])
    for data_dict in data_list:
        block = data_dict.get('block', '')
        lines = block.split('\\n')
        for line in lines:
            index = line.find(tag)
            if index > -1:
                line = line[index:]
                cleaned_lines.append(line)
    return cleaned_lines


def get_upload_point(repository, **kwd):
    upload_point = kwd.get('upload_point', None)
    if upload_point is not None:
        # The value of upload_point will be something like: database/community_files/000/repo_12/1.bed
        if os.path.exists(upload_point):
            if os.path.isfile(upload_point):
                # Get the parent directory
                upload_point, not_needed = os.path.split(upload_point)
                # Now the value of uplaod_point will be something like: database/community_files/000/repo_12/
            upload_point = upload_point.split('repo_%d' % repository.id)[1]
            if upload_point:
                upload_point = upload_point.lstrip('/')
                upload_point = upload_point.rstrip('/')
            # Now the value of uplaod_point will be something like: /
            if upload_point == '/':
                upload_point = None
        else:
            # Must have been an error selecting something that didn't exist, so default to repository root
            upload_point = None
    return upload_point


def handle_bz2(repository, uploaded_file_name):
    fd, uncompressed = tempfile.mkstemp(prefix='repo_%d_upload_bunzip2_' % repository.id,
                                        dir=os.path.dirname(uploaded_file_name),
                                        text=False)
    bzipped_file = bz2.BZ2File(uploaded_file_name, 'rb')
    while 1:
        try:
            chunk = bzipped_file.read(basic_util.CHUNK_SIZE)
        except IOError:
            os.close(fd)
            os.remove(uncompressed)
            log.exception('Problem uncompressing bz2 data "%s"', uploaded_file_name)
            return
        if not chunk:
            break
        os.write(fd, chunk)
    os.close(fd)
    bzipped_file.close()
    shutil.move(uncompressed, uploaded_file_name)


def handle_gzip(repository, uploaded_file_name):
    fd, uncompressed = tempfile.mkstemp(prefix='repo_%d_upload_gunzip_' % repository.id,
                                        dir=os.path.dirname(uploaded_file_name),
                                        text=False)
    gzipped_file = gzip.GzipFile(uploaded_file_name, 'rb')
    while 1:
        try:
            chunk = gzipped_file.read(basic_util.CHUNK_SIZE)
        except IOError:
            os.close(fd)
            os.remove(uncompressed)
            log.exception('Problem uncompressing gz data "%s"', uploaded_file_name)
            return
        if not chunk:
            break
        os.write(fd, chunk)
    os.close(fd)
    gzipped_file.close()
    shutil.move(uncompressed, uploaded_file_name)


def uncompress(repository, uploaded_file_name, uploaded_file_filename, isgzip=False, isbz2=False):
    if isgzip:
        handle_gzip(repository, uploaded_file_name)
        return uploaded_file_filename.rstrip('.gz')
    if isbz2:
        handle_bz2(repository, uploaded_file_name)
        return uploaded_file_filename.rstrip('.bz2')
