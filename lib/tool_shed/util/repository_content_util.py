import os
import shutil

import tool_shed.repository_types.util as rt_util
from tool_shed.util import (
    commit_util,
    xml_util,
)


def upload_tar(
    trans,
    rdah,
    tdah,
    repository,
    tar,
    uploaded_file,
    upload_point,
    remove_repo_files_not_in_tar,
    commit_message,
    new_repo_alert,
):
    # Upload a tar archive of files.
    undesirable_dirs_removed = 0
    undesirable_files_removed = 0
    check_results = commit_util.check_archive(repository, tar)
    if check_results.invalid:
        tar.close()
        uploaded_file.close()
        message = "{} Invalid paths were: {}".format(" ".join(check_results.errors), ", ".join(check_results.invalid))
        return False, message, [], "", undesirable_dirs_removed, undesirable_files_removed
    else:
        repository.hg_repo
        repo_dir = repository.repo_path(trans.app)
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
        uploaded_file.close()
        for filename in filenames_in_archive:
            uploaded_file_name = os.path.join(full_path, filename)
            if os.path.split(uploaded_file_name)[-1] == rt_util.REPOSITORY_DEPENDENCY_DEFINITION_FILENAME:
                # Inspect the contents of the file to see if toolshed or changeset_revision attributes
                # are missing and if so, set them appropriately.
                altered, root_elem, error_message = rdah.handle_tag_attributes(uploaded_file_name)
                if error_message:
                    return False, error_message, [], "", [], []
                elif altered:
                    tmp_filename = xml_util.create_and_write_tmp_file(root_elem)
                    shutil.move(tmp_filename, uploaded_file_name)
            elif os.path.split(uploaded_file_name)[-1] == rt_util.TOOL_DEPENDENCY_DEFINITION_FILENAME:
                # Inspect the contents of the file to see if toolshed or changeset_revision
                # attributes are missing and if so, set them appropriately.
                altered, root_elem, error_message = tdah.handle_tag_attributes(uploaded_file_name)
                if error_message:
                    return False, error_message, [], "", [], []
                if altered:
                    tmp_filename = xml_util.create_and_write_tmp_file(root_elem)
                    shutil.move(tmp_filename, uploaded_file_name)
        return commit_util.handle_directory_changes(
            trans.app,
            trans.request.host,
            trans.user.username,
            repository,
            full_path,
            filenames_in_archive,
            remove_repo_files_not_in_tar,
            new_repo_alert,
            commit_message,
            undesirable_dirs_removed,
            undesirable_files_removed,
        )
