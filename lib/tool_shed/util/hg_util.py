import logging
import os
import subprocess
import tempfile
from datetime import datetime
from time import gmtime

from tool_shed.util import basic_util

log = logging.getLogger(__name__)

INITIAL_CHANGELOG_HASH = '000000000000'


def add_changeset(repo_path, path_to_filename_in_archive):
    try:
        subprocess.check_output(['hg', 'add', path_to_filename_in_archive], stderr=subprocess.STDOUT, cwd=repo_path)
    except Exception as e:
        error_message = "Error adding '%s' to repository: %s" % (path_to_filename_in_archive, e)
        if isinstance(e, subprocess.CalledProcessError):
            error_message += "\nOutput was:\n%s" % e.output
        raise Exception(error_message)


def archive_repository_revision(app, repository, archive_dir, changeset_revision):
    '''Create an un-versioned archive of a repository.'''
    repo_path = repository.repo_path(app)
    try:
        subprocess.check_output(['hg', 'archive', '-r', changeset_revision, archive_dir], stderr=subprocess.STDOUT, cwd=repo_path)
    except Exception as e:
        error_message = "Error attempting to archive revision '%s' of repository '%s': %s" % (changeset_revision, repository.name, e)
        if isinstance(e, subprocess.CalledProcessError):
            error_message += "\nOutput was:\n%s" % e.output
        log.exception(error_message)
        raise Exception(error_message)


def clone_repository(repository_clone_url, repository_file_dir, ctx_rev=None):
    """
    Clone the repository up to the specified changeset_revision.  No subsequent revisions will be
    present in the cloned repository.
    """
    cmd = ['hg', 'clone']
    if ctx_rev:
        cmd.extend(['-r', ctx_rev])
    cmd.extend([repository_clone_url, repository_file_dir])
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return True, None
    except Exception as e:
        error_message = 'Error cloning repository: %s' % e
        if isinstance(e, subprocess.CalledProcessError):
            error_message += "\nOutput was:\n%s" % e.output
        log.error(error_message)
        return False, error_message


def commit_changeset(repo_path, full_path_to_changeset, username, message):
    try:
        subprocess.check_output(['hg', 'commit', '-u', username, '-m', message, full_path_to_changeset], stderr=subprocess.STDOUT, cwd=repo_path)
    except Exception as e:
        error_message = "Error committing '%s' to repository: %s" % (full_path_to_changeset, e)
        if isinstance(e, subprocess.CalledProcessError):
            if e.returncode == 1 and 'nothing changed' in e.output:
                return
            error_message += "\nOutput was:\n%s" % e.output
        raise Exception(error_message)


def copy_file_from_manifest(repo, changeset_revision, filename, dir):
    """
    Copy the latest version of the file named filename from the repository manifest to the directory
    to which dir refers.
    """
    for changeset in reversed_upper_bounded_changelog(repo, changeset_revision):
        changeset_ctx = repo.changectx(changeset)
        fctx = get_file_context_from_ctx(changeset_ctx, filename)
        if fctx and fctx not in ['DELETED']:
            file_path = os.path.join(dir, filename)
            fh = open(file_path, 'wb')
            fh.write(fctx.data())
            fh.close()
            return file_path
    return None


def create_hgrc_file(app, repository):
    # Since we support both http and https, we set `push_ssl` to False to
    # override the default (which is True) in the Mercurial API.
    # The hg purge extension purges all files and directories not being tracked
    # by Mercurial in the current repository. It will remove unknown files and
    # empty directories. This is not currently used because it is not supported
    # in the Mercurial API.
    repo_path = repository.repo_path(app)
    hgrc_path = os.path.join(repo_path, '.hg', 'hgrc')
    with open(hgrc_path, 'wb') as fp:
        fp.write('[paths]\n')
        fp.write('default = .\n')
        fp.write('default-push = .\n')
        fp.write('[web]\n')
        fp.write('allow_push = %s\n' % repository.user.username)
        fp.write('name = %s\n' % repository.name)
        fp.write('push_ssl = false\n')
        fp.write('[extensions]\n')
        fp.write('hgext.purge=')


def get_changectx_for_changeset(repo, changeset_revision, **kwd):
    """Retrieve a specified changectx from a repository."""
    for changeset in repo.changelog:
        ctx = repo.changectx(changeset)
        if str(ctx) == changeset_revision:
            return ctx
    return None


def get_config_from_disk(config_file, relative_install_dir):
    for root, dirs, files in os.walk(relative_install_dir):
        if root.find('.hg') < 0:
            for name in files:
                if name == config_file:
                    return os.path.abspath(os.path.join(root, name))
    return None


def get_ctx_file_path_from_manifest(filename, repo, changeset_revision):
    """
    Get the ctx file path for the latest revision of filename from the repository manifest up
    to the value of changeset_revision.
    """
    stripped_filename = basic_util.strip_path(filename)
    for changeset in reversed_upper_bounded_changelog(repo, changeset_revision):
        manifest_ctx = repo.changectx(changeset)
        for ctx_file in manifest_ctx.files():
            ctx_file_name = basic_util.strip_path(ctx_file)
            if ctx_file_name == stripped_filename:
                return manifest_ctx, ctx_file
    return None, None


def get_file_context_from_ctx(ctx, filename):
    """Return the mercurial file context for a specified file."""
    # We have to be careful in determining if we found the correct file because multiple files with
    # the same name may be in different directories within ctx if the files were moved within the change
    # set.  For example, in the following ctx.files() list, the former may have been moved to the latter:
    # ['tmap_wrapper_0.0.19/tool_data_table_conf.xml.sample', 'tmap_wrapper_0.3.3/tool_data_table_conf.xml.sample'].
    # Another scenario is that the file has been deleted.
    deleted = False
    filename = basic_util.strip_path(filename)
    for ctx_file in ctx.files():
        ctx_file_name = basic_util.strip_path(ctx_file)
        if filename == ctx_file_name:
            try:
                # If the file was moved, its destination will be returned here.
                fctx = ctx[ctx_file]
                return fctx
            except LookupError:
                # Set deleted for now, and continue looking in case the file was moved instead of deleted.
                deleted = True
    if deleted:
        return 'DELETED'
    return None


def get_named_tmpfile_from_ctx(ctx, filename, dir):
    """
    Return a named temporary file created from a specified file with a given name included in a repository
    changeset revision.
    """
    filename = basic_util.strip_path(filename)
    for ctx_file in ctx.files():
        ctx_file_name = basic_util.strip_path(ctx_file)
        if filename == ctx_file_name:
            try:
                # If the file was moved, its destination file contents will be returned here.
                fctx = ctx[ctx_file]
            except LookupError:
                # Continue looking in case the file was moved.
                fctx = None
                continue
            if fctx:
                fh = tempfile.NamedTemporaryFile('wb', prefix="tmp-toolshed-gntfc", dir=dir)
                tmp_filename = fh.name
                fh.close()
                fh = open(tmp_filename, 'wb')
                fh.write(fctx.data())
                fh.close()
                return tmp_filename
    return None


def get_readable_ctx_date(ctx):
    """Convert the date of the changeset (the received ctx) to a human-readable date."""
    t, tz = ctx.date()
    date = datetime(*gmtime(float(t) - tz)[:6])
    ctx_date = date.strftime("%Y-%m-%d")
    return ctx_date


def get_repo_for_repository(app, repository=None, repo_path=None):
    # Import from mercurial here to let Galaxy start under Python 3
    from mercurial import (
        hg,
        ui
    )
    if repository is not None:
        return hg.repository(ui.ui(), repository.repo_path(app))
    if repo_path is not None:
        return hg.repository(ui.ui(), repo_path)


def get_repository_heads(repo):
    """Return current repository heads, which are changesets with no child changesets."""
    heads = [repo[h] for h in repo.heads(None)]
    return heads


def get_reversed_changelog_changesets(repo):
    """Return a list of changesets in reverse order from that provided by the repository manifest."""
    reversed_changelog = []
    for changeset in repo.changelog:
        reversed_changelog.insert(0, changeset)
    return reversed_changelog


def get_revision_label(app, repository, changeset_revision, include_date=True, include_hash=True):
    """
    Return a string consisting of the human read-able changeset rev and the changeset revision string
    which includes the revision date if the receive include_date is True.
    """
    repo = get_repo_for_repository(app, repository=repository)
    ctx = get_changectx_for_changeset(repo, changeset_revision)
    if ctx:
        return get_revision_label_from_ctx(ctx, include_date=include_date, include_hash=include_hash)
    else:
        if include_hash:
            return "-1:%s" % changeset_revision
        else:
            return "-1"


def get_rev_label_changeset_revision_from_repository_metadata(app, repository_metadata, repository=None,
                                                              include_date=True, include_hash=True):
    if repository is None:
        repository = repository_metadata.repository
    repo = get_repo_for_repository(app, repository=repository)
    changeset_revision = repository_metadata.changeset_revision
    ctx = get_changectx_for_changeset(repo, changeset_revision)
    if ctx:
        rev = '%04d' % ctx.rev()
        if include_date:
            changeset_revision_date = get_readable_ctx_date(ctx)
            if include_hash:
                label = "%s:%s (%s)" % (str(ctx.rev()), changeset_revision, changeset_revision_date)
            else:
                label = "%s (%s)" % (str(ctx.rev()), changeset_revision_date)
        else:
            if include_hash:
                label = "%s:%s" % (str(ctx.rev()), changeset_revision)
            else:
                label = "%s" % str(ctx.rev())
    else:
        rev = '-1'
        if include_hash:
            label = "-1:%s" % changeset_revision
        else:
            label = "-1"
    return rev, label, changeset_revision


def get_revision_label_from_ctx(ctx, include_date=True, include_hash=True):
    if include_date:
        if include_hash:
            return '%s:%s <i><font color="#666666">(%s)</font></i>' % \
                (str(ctx.rev()), str(ctx), str(get_readable_ctx_date(ctx)))
        else:
            return '%s <i><font color="#666666">(%s)</font></i>' % \
                (str(ctx.rev()), str(get_readable_ctx_date(ctx)))
    else:
        if include_hash:
            return '%s:%s' % (str(ctx.rev()), str(ctx))
        else:
            return '%s' % str(ctx.rev())


def get_rev_label_from_changeset_revision(repo, changeset_revision, include_date=True, include_hash=True):
    """
    Given a changeset revision hash, return two strings, the changeset rev and the changeset revision hash
    which includes the revision date if the receive include_date is True.
    """
    ctx = get_changectx_for_changeset(repo, changeset_revision)
    if ctx:
        rev = '%04d' % ctx.rev()
        label = get_revision_label_from_ctx(ctx, include_date=include_date)
    else:
        rev = '-1'
        label = "-1:%s" % changeset_revision
    return rev, label


def pull_repository(repo_path, repository_clone_url, ctx_rev):
    """Pull changes from a remote repository to a local one."""
    try:
        subprocess.check_output(['hg', 'pull', '-r', ctx_rev, repository_clone_url], stderr=subprocess.STDOUT, cwd=repo_path)
    except Exception as e:
        error_message = "Error pulling revision '%s': %s" % (ctx_rev, e)
        if isinstance(e, subprocess.CalledProcessError):
            error_message += "\nOutput was:\n%s" % e.output
        raise Exception(error_message)


def remove_file(repo_path, selected_file, force=True):
    cmd = ['hg', 'remove']
    if force:
        cmd.append('--force')
    cmd.append(selected_file)
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT, cwd=repo_path)
    except Exception as e:
        error_message = "Error removing file '%s': %s" % (selected_file, e)
        if isinstance(e, subprocess.CalledProcessError):
            error_message += "\nOutput was:\n%s" % e.output
        raise Exception(error_message)


def reversed_lower_upper_bounded_changelog(repo, excluded_lower_bounds_changeset_revision, included_upper_bounds_changeset_revision):
    """
    Return a reversed list of changesets in the repository changelog after the excluded_lower_bounds_changeset_revision,
    but up to and including the included_upper_bounds_changeset_revision.  The value of excluded_lower_bounds_changeset_revision
    will be the value of INITIAL_CHANGELOG_HASH if no valid changesets exist before included_upper_bounds_changeset_revision.
    """
    # To set excluded_lower_bounds_changeset_revision, calling methods should do the following, where the value
    # of changeset_revision is a downloadable changeset_revision.
    # excluded_lower_bounds_changeset_revision = \
    #     metadata_util.get_previous_metadata_changeset_revision(app, repository, changeset_revision, downloadable=?)
    if excluded_lower_bounds_changeset_revision == INITIAL_CHANGELOG_HASH:
        appending_started = True
    else:
        appending_started = False
    reversed_changelog = []
    for changeset in repo.changelog:
        changeset_hash = str(repo.changectx(changeset))
        if appending_started:
            reversed_changelog.insert(0, changeset)
        if changeset_hash == excluded_lower_bounds_changeset_revision and not appending_started:
            appending_started = True
        if changeset_hash == included_upper_bounds_changeset_revision:
            break
    return reversed_changelog


def reversed_upper_bounded_changelog(repo, included_upper_bounds_changeset_revision):
    """
    Return a reversed list of changesets in the repository changelog up to and including the
    included_upper_bounds_changeset_revision.
    """
    return reversed_lower_upper_bounded_changelog(repo, INITIAL_CHANGELOG_HASH, included_upper_bounds_changeset_revision)


def update_repository(repo_path, ctx_rev=None):
    """
    Update the cloned repository to changeset_revision.  It is critical that the installed repository is updated to the desired
    changeset_revision before metadata is set because the process for setting metadata uses the repository files on disk.
    """
    # TODO: We may have files on disk in the repo directory that aren't being tracked, so they must be removed.
    # The codes used to show the status of files are as follows.
    # M = modified
    # A = added
    # R = removed
    # C = clean
    # ! = deleted, but still tracked
    # ? = not tracked
    # I = ignored
    # It would be nice if we could use mercurial's purge extension to remove untracked files.  The problem is that
    # purging is not supported by the mercurial API.
    cmd = ['hg', 'update']
    if ctx_rev:
        cmd.extend(['-r', ctx_rev])
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT, cwd=repo_path)
    except Exception as e:
        error_message = 'Error updating repository: %s' % e
        if isinstance(e, subprocess.CalledProcessError):
            error_message += "\nOutput was:\n%s" % e.output
        raise Exception(error_message)


def init_repository(repo_path):
    """
    Create a new Mercurial repository in the given directory.
    """
    try:
        subprocess.check_output(['hg', 'init'], stderr=subprocess.STDOUT, cwd=repo_path)
    except Exception as e:
        error_message = 'Error initializing repository: %s' % e
        if isinstance(e, subprocess.CalledProcessError):
            error_message += "\nOutput was:\n%s" % e.output
        raise Exception(error_message)


def changeset2rev(repo_path, changeset_revision):
    """
    Return the revision number corresponding to a specified changeset revision.
    """
    try:
        rev = subprocess.check_output(['hg', 'id', '-r', changeset_revision, '-n'], stderr=subprocess.STDOUT, cwd=repo_path)
    except Exception as e:
        error_message = "Error looking for changeset '%s': %s" % (changeset_revision, e)
        if isinstance(e, subprocess.CalledProcessError):
            error_message += "\nOutput was:\n%s" % e.output
        raise Exception(error_message)
    return int(rev.strip())
