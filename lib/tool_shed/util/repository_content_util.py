import os
import shutil
import tempfile
from typing import (
    Optional,
    TYPE_CHECKING,
)

import tool_shed.repository_types.util as rt_util
from galaxy.tool_shed.util.hg_util import clone_repository
from galaxy.util.compression_utils import CompressedFile
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
    from tool_shed.context import ProvidesRepositoriesContext
    from tool_shed.webapp.model import Repository


def upload_tar(
    trans: "ProvidesRepositoriesContext",
    username: str,
    repository: "Repository",
    uploaded_file,
    commit_message: str,
    dry_run: bool = False,
    remove_repo_files_not_in_tar: bool = True,
    new_repo_alert: bool = False,
    rdah: Optional[RepositoryDependencyAttributeHandler] = None,
    tdah: Optional[ToolDependencyAttributeHandler] = None,
) -> ChangeResponseT:
    host = trans.repositories_hostname
    app = trans.app
    tar = CompressedFile.open_tar(uploaded_file)
    rdah = rdah or RepositoryDependencyAttributeHandler(trans, unpopulate=False)
    tdah = tdah or ToolDependencyAttributeHandler(trans, unpopulate=False)
    # Upload a tar archive of files.
    undesirable_dirs_removed = 0
    undesirable_files_removed = 0
    check_results = check_archive(repository, tar)
    if check_results.invalid:
        tar.close()
        try:
            uploaded_file.close()
        except AttributeError:
            pass
        message = "{} Invalid paths were: {}".format(
            " ".join(check_results.errors), ", ".join([i.name for i in check_results.invalid])
        )
        return False, message, [], "", undesirable_dirs_removed, undesirable_files_removed
    else:
        repo_dir = repository.repo_path(app)
        if dry_run:
            full_path = tempfile.mkdtemp()
            clone_repository(repo_dir, full_path)
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
            repo_path=full_path,
        )
