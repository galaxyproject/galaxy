import os
import shutil
import tarfile
from typing import (
    Optional,
    TYPE_CHECKING,
)

import tool_shed.repository_types.util as rt_util
from galaxy.util import checkers
from tool_shed.dependencies.attribute_handlers import (
    RepositoryDependencyAttributeHandler,
    ToolDependencyAttributeHandler,
)
from tool_shed.util import xml_util
from tool_shed.util.commit_util import (
    ChangeResponseT,
    check_archive,
    handle_directory_changes,
)

if TYPE_CHECKING:
    from tool_shed.structured_app import ToolShedApp
    from tool_shed.webapp.model import Repository


def upload_tar(
    app: "ToolShedApp",
    host: str,
    username: str,
    repository: "Repository",
    uploaded_file,
    upload_point,
    commit_message: str,
    remove_repo_files_not_in_tar: bool = True,
    new_repo_alert: bool = False,
    tar=None,
    rdah: Optional[RepositoryDependencyAttributeHandler] = None,
    tdah: Optional[ToolDependencyAttributeHandler] = None,
) -> ChangeResponseT:
    if tar is None:
        isgzip = False
        isbz2 = False
        isgzip = checkers.is_gzip(uploaded_file)
        if not isgzip:
            isbz2 = checkers.is_bz2(uploaded_file)
        if isgzip or isbz2:
            # Open for reading with transparent compression.
            tar = tarfile.open(uploaded_file, "r:*")
        else:
            tar = tarfile.open(uploaded_file)

    rdah = rdah or RepositoryDependencyAttributeHandler(app, unpopulate=False)
    tdah = tdah or ToolDependencyAttributeHandler(app, unpopulate=False)
    # Upload a tar archive of files.
    undesirable_dirs_removed = 0
    undesirable_files_removed = 0
    check_results = check_archive(repository, tar)
    if check_results.invalid:
        tar.close()
        uploaded_file.close()
        message = "{} Invalid paths were: {}".format(" ".join(check_results.errors), ", ".join(check_results.invalid))
        return False, message, [], "", undesirable_dirs_removed, undesirable_files_removed
    else:
        repo_dir = repository.repo_path(app)
        if upload_point is not None:
            full_path = os.path.abspath(os.path.join(repo_dir, upload_point))
        else:
            full_path = os.path.abspath(repo_dir)
        undesirable_files_removed = len(check_results.undesirable_files)
        undesirable_dirs_removed = len(check_results.undesirable_dirs)
        filenames_in_archive = [ti.name for ti in check_results.valid]
        # Extract the uploaded tar to the load_point within the repository hierarchy.
        tar.extractall(path=full_path, members=check_results.valid)
        tar.close()
        try:
            uploaded_file.close()
        except AttributeError:
            pass
        for filename in filenames_in_archive:
            uploaded_file_name = os.path.join(full_path, filename)
            if os.path.split(uploaded_file_name)[-1] == rt_util.REPOSITORY_DEPENDENCY_DEFINITION_FILENAME:
                # Inspect the contents of the file to see if toolshed or changeset_revision attributes
                # are missing and if so, set them appropriately.
                altered, root_elem, error_message = rdah.handle_tag_attributes(uploaded_file_name)
                if error_message:
                    return False, error_message, [], "", 0, 0
                elif altered:
                    tmp_filename = xml_util.create_and_write_tmp_file(root_elem)
                    shutil.move(tmp_filename, uploaded_file_name)
            elif os.path.split(uploaded_file_name)[-1] == rt_util.TOOL_DEPENDENCY_DEFINITION_FILENAME:
                # Inspect the contents of the file to see if toolshed or changeset_revision
                # attributes are missing and if so, set them appropriately.
                altered, root_elem, error_message = tdah.handle_tag_attributes(uploaded_file_name)
                if error_message:
                    return False, error_message, [], "", 0, 0
                if altered:
                    tmp_filename = xml_util.create_and_write_tmp_file(root_elem)
                    shutil.move(tmp_filename, uploaded_file_name)
        return handle_directory_changes(
            app,
            host,
            username,
            repository,
            full_path,
            filenames_in_archive,
            remove_repo_files_not_in_tar,
            new_repo_alert,
            commit_message,
            undesirable_dirs_removed,
            undesirable_files_removed,
        )
