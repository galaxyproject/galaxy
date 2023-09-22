import logging
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from time import gmtime

from galaxy.tool_shed.util import basic_util
from galaxy.tool_shed.util.hg_util import (
    clone_repository,
    copy_file_from_manifest,
    get_changectx_for_changeset,
    get_config_from_disk,
    get_ctx_file_path_from_manifest,
    get_file_context_from_ctx,
    pull_repository,
    reversed_lower_upper_bounded_changelog,
    reversed_upper_bounded_changelog,
    update_repository,
)
from galaxy.util import unicodify

log = logging.getLogger(__name__)

INITIAL_CHANGELOG_HASH = "000000000000"


def add_changeset(repo_path, path_to_filename_in_archive):
    try:
        subprocess.check_output(["hg", "add", path_to_filename_in_archive], stderr=subprocess.STDOUT, cwd=repo_path)
    except Exception as e:
        error_message = f"Error adding '{path_to_filename_in_archive}' to repository: {unicodify(e)}"
        if isinstance(e, subprocess.CalledProcessError):
            error_message += f"\nOutput was:\n{unicodify(e.output)}"
        raise Exception(error_message)


def archive_repository_revision(app, repository, archive_dir, changeset_revision):
    """Create an un-versioned archive of a repository."""
    repo_path = repository.repo_path(app)
    try:
        subprocess.check_output(
            ["hg", "archive", "-r", changeset_revision, archive_dir], stderr=subprocess.STDOUT, cwd=repo_path
        )
    except Exception as e:
        error_message = f"Error attempting to archive revision '{changeset_revision}' of repository '{repository.name}': {unicodify(e)}"
        if isinstance(e, subprocess.CalledProcessError):
            error_message += f"\nOutput was:\n{unicodify(e.output)}"
        log.exception(error_message)
        raise Exception(error_message)


def commit_changeset(repo_path: str, full_path_to_changeset: str, username: str, message: str) -> None:
    try:
        subprocess.check_output(
            ["hg", "commit", "-u", username, "-m", message, full_path_to_changeset],
            stderr=subprocess.STDOUT,
            cwd=repo_path,
        )
    except Exception as e:
        error_message = f"Error committing '{full_path_to_changeset}' to repository: {unicodify(e)}"
        if isinstance(e, subprocess.CalledProcessError):
            if e.returncode == 1 and "nothing changed" in unicodify(e.output):
                return
            error_message += f"\nOutput was:\n{unicodify(e.output)}"
        raise Exception(error_message)


def get_hgrc_path(repo_path):
    return os.path.join(repo_path, ".hg", "hgrc")


def create_hgrc_file(app, repository):
    # Since we support both http and https, we set `push_ssl` to False to
    # override the default (which is True) in the Mercurial API.
    # The hg purge extension purges all files and directories not being tracked
    # by Mercurial in the current repository. It will remove unknown files and
    # empty directories. This is not currently used because it is not supported
    # in the Mercurial API.
    repo_path = repository.repo_path(app)
    hgrc_path = get_hgrc_path(repo_path)
    with open(hgrc_path, "w") as fp:
        fp.write("[paths]\n")
        fp.write("default = .\n")
        fp.write("default-push = .\n")
        fp.write("[web]\n")
        fp.write(f"allow_push = {repository.user.username}\n")
        fp.write(f"name = {repository.name}\n")
        fp.write("push_ssl = false\n")
        fp.write("[extensions]\n")
        fp.write("hgext.purge=")


def get_named_tmpfile_from_ctx(ctx, filename, dir):
    """
    Return a named temporary file created from a specified file with a given name included in a repository
    changeset revision.
    """
    filename = basic_util.strip_path(filename)
    for ctx_file in ctx.files():
        ctx_file_name = basic_util.strip_path(unicodify(ctx_file))
        if filename == ctx_file_name:
            try:
                # If the file was moved, its destination file contents will be returned here.
                fctx = ctx[ctx_file]
            except LookupError:
                # Continue looking in case the file was moved.
                fctx = None
                continue
            if fctx:
                fh = tempfile.NamedTemporaryFile("wb", prefix="tmp-toolshed-gntfc", dir=dir)
                tmp_filename = fh.name
                fh.close()
                fh = open(tmp_filename, "wb")
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
    Return a string consisting of the human readable changeset rev and the changeset revision string
    which includes the revision date if the receive include_date is True.
    """
    repo = repository.hg_repo
    ctx = get_changectx_for_changeset(repo, changeset_revision)
    if ctx:
        return get_revision_label_from_ctx(ctx, include_date=include_date, include_hash=include_hash)
    else:
        if include_hash:
            return f"-1:{changeset_revision}"
        else:
            return "-1"


def get_rev_label_changeset_revision_from_repository_metadata(
    app, repository_metadata, repository=None, include_date=True, include_hash=True
):
    if repository is None:
        repository = repository_metadata.repository
    repo = repository.hg_repo
    changeset_revision = repository_metadata.changeset_revision
    ctx = get_changectx_for_changeset(repo, changeset_revision)
    if ctx:
        rev = "%04d" % ctx.rev()
        if include_date:
            changeset_revision_date = get_readable_ctx_date(ctx)
            if include_hash:
                label = f"{ctx.rev()}:{changeset_revision} ({changeset_revision_date})"
            else:
                label = f"{ctx.rev()} ({changeset_revision_date})"
        else:
            if include_hash:
                label = f"{ctx.rev()}:{changeset_revision}"
            else:
                label = f"{ctx.rev()}"
    else:
        rev = "-1"
        if include_hash:
            label = f"-1:{changeset_revision}"
        else:
            label = "-1"
    return rev, label, changeset_revision


def get_revision_label_from_ctx(ctx, include_date=True, include_hash=True):
    if include_date:
        if include_hash:
            return f'{ctx.rev()}:{ctx} <i><font color="#666666">({get_readable_ctx_date(ctx)})</font></i>'
        else:
            return f'{ctx.rev()} <i><font color="#666666">({get_readable_ctx_date(ctx)})</font></i>'
    else:
        if include_hash:
            return f"{ctx.rev()}:{ctx}"
        else:
            return str(ctx.rev())


def get_rev_label_from_changeset_revision(repo, changeset_revision, include_date=True, include_hash=True):
    """
    Given a changeset revision hash, return two strings, the changeset rev and the changeset revision hash
    which includes the revision date if the receive include_date is True.
    """
    ctx = get_changectx_for_changeset(repo, changeset_revision)
    if ctx:
        rev = "%04d" % ctx.rev()
        label = get_revision_label_from_ctx(ctx, include_date=include_date)
    else:
        rev = "-1"
        label = f"-1:{changeset_revision}"
    return rev, label


def remove_path(repo_path, selected_file):
    cmd = ["hg", "remove", "--force", selected_file]
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT, cwd=repo_path)
    except Exception as e:
        error_message = f"Error removing path '{selected_file}': {unicodify(e)}"
        if isinstance(e, subprocess.CalledProcessError):
            output = unicodify(e.output)
            if "is untracked" in output:
                # That's ok, happens if we add a new file or directory via tarball upload,
                # just delete the file or dir on disk
                selected_file_path = os.path.join(repo_path, selected_file)
                if os.path.isdir(selected_file_path):
                    shutil.rmtree(selected_file_path)
                else:
                    os.remove(selected_file_path)
                return
            error_message += f"\nOutput was:\n{output}"
        raise Exception(error_message)


def init_repository(repo_path):
    """
    Create a new Mercurial repository in the given directory.
    """
    try:
        subprocess.check_output(["hg", "init"], stderr=subprocess.STDOUT, cwd=repo_path)
    except Exception as e:
        error_message = f"Error initializing repository: {unicodify(e)}"
        if isinstance(e, subprocess.CalledProcessError):
            error_message += f"\nOutput was:\n{unicodify(e.output)}"
        raise Exception(error_message)


def changeset2rev(repo_path, changeset_revision):
    """
    Return the revision number (as an int) corresponding to a specified changeset revision.
    """
    try:
        rev = subprocess.check_output(
            ["hg", "id", "-r", changeset_revision, "-n"], stderr=subprocess.STDOUT, cwd=repo_path
        )
    except Exception as e:
        error_message = f"Error looking for changeset '{changeset_revision}': {unicodify(e)}"
        if isinstance(e, subprocess.CalledProcessError):
            error_message += f"\nOutput was:\n{unicodify(e.output)}"
        raise Exception(error_message)
    return int(rev.strip())


__all__ = (
    "add_changeset",
    "archive_repository_revision",
    "clone_repository",
    "commit_changeset",
    "copy_file_from_manifest",
    "create_hgrc_file",
    "get_changectx_for_changeset",
    "get_config_from_disk",
    "get_ctx_file_path_from_manifest",
    "get_file_context_from_ctx",
    "get_named_tmpfile_from_ctx",
    "get_readable_ctx_date",
    "get_repository_heads",
    "get_reversed_changelog_changesets",
    "get_revision_label",
    "get_rev_label_changeset_revision_from_repository_metadata",
    "get_revision_label_from_ctx",
    "get_rev_label_from_changeset_revision",
    "pull_repository",
    "remove_path",
    "reversed_lower_upper_bounded_changelog",
    "reversed_upper_bounded_changelog",
    "update_repository",
    "init_repository",
    "changeset2rev",
)
