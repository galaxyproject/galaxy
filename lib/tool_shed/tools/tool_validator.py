import filecmp
import logging
import os
import tempfile

from galaxy.tool_shed.tools.tool_validator import ToolValidator as GalaxyToolValidator
from galaxy.tools import Tool
from galaxy.util import unicodify
from galaxy.util.tool_shed.xml_util import parse_xml
from tool_shed.util import (
    basic_util,
    hg_util,
    repository_util,
    tool_util,
)

log = logging.getLogger(__name__)


class ToolValidator(GalaxyToolValidator):
    def can_use_tool_config_disk_file(self, repository, repo, file_path, changeset_revision):
        """
        Determine if repository's tool config file on disk can be used.  This method
        is restricted to tool config files since, with the exception of tool config
        files, multiple files with the same name will likely be in various directories
        in the repository and we're comparing file names only (not relative paths).
        """
        if not file_path or not os.path.exists(file_path):
            # The file no longer exists on disk, so it must have been deleted at some previous
            # point in the change log.
            return False
        if changeset_revision == repository.tip():
            return True
        file_name = basic_util.strip_path(file_path)
        latest_version_of_file = self.get_latest_tool_config_revision_from_repository_manifest(
            repo, file_name, changeset_revision
        )
        can_use_disk_file = filecmp.cmp(file_path, latest_version_of_file)
        try:
            os.unlink(latest_version_of_file)
        except Exception:
            pass
        return can_use_disk_file

    def concat_messages(self, msg1, msg2):
        if msg1:
            if msg2:
                message = f"{msg1}  {msg2}"
            else:
                message = msg1
        elif msg2:
            message = msg2
        else:
            message = ""
        return message

    def copy_disk_sample_files_to_dir(self, repo_files_dir, dest_path):
        """
        Copy all files currently on disk that end with the .sample extension to the
        directory to which dest_path refers.
        """
        sample_files = []
        for root, _dirs, files in os.walk(repo_files_dir):
            if root.find(".hg") < 0:
                for name in files:
                    if name.endswith(".sample"):
                        relative_path = os.path.join(root, name)
                        tool_util.copy_sample_file(self.app, relative_path, dest_path=dest_path)
                        sample_files.append(name)
        return sample_files

    def get_latest_tool_config_revision_from_repository_manifest(self, repo, filename, changeset_revision):
        """
        Get the latest revision of a tool config file named filename from the repository
        manifest up to the value of changeset_revision.  This method is restricted to tool_config
        files rather than any file since it is likely that, with the exception of tool config
        files, multiple files will have the same name in various directories within the repository.
        """
        stripped_filename = basic_util.strip_path(filename)
        for changeset in hg_util.reversed_upper_bounded_changelog(repo, changeset_revision):
            manifest_ctx = repo[changeset]
            for ctx_file in manifest_ctx.files():
                ctx_file_name = basic_util.strip_path(unicodify(ctx_file))
                if ctx_file_name == stripped_filename:
                    try:
                        fctx = manifest_ctx[ctx_file]
                    except LookupError:
                        # The ctx_file may have been moved in the change set.  For example,
                        # 'ncbi_blastp_wrapper.xml' was moved to 'tools/ncbi_blast_plus/ncbi_blastp_wrapper.xml',
                        # so keep looking for the file until we find the new location.
                        continue
                    with tempfile.NamedTemporaryFile("wb", prefix="tmp-toolshed-gltcrfrm", delete=False) as fh:
                        tmp_filename = fh.name
                        fh.write(fctx.data())
                    return tmp_filename
        return None

    def get_list_of_copied_sample_files(self, repo, changeset_revision, dir):
        """
        Find all sample files (files in the repository with the special .sample extension)
        in the reversed repository manifest up to changeset_revision. Copy each discovered file to dir and
        return the list of filenames.  If a .sample file was added in a changeset and then
        deleted in a later changeset, it will be returned in the deleted_sample_files list.
        The caller will set the value of app.config.tool_data_path to dir in order to load
        the tools and generate metadata for them.
        """
        deleted_sample_files = []
        sample_files = []
        for changeset in hg_util.reversed_upper_bounded_changelog(repo, changeset_revision):
            changeset_ctx = repo[changeset]
            for ctx_file in changeset_ctx.files():
                ctx_file = unicodify(ctx_file)
                ctx_file_name = basic_util.strip_path(ctx_file)
                # If we decide in the future that files deleted later in the changelog should
                # not be used, we can use the following if statement. if ctx_file_name.endswith( '.sample' )
                # and ctx_file_name not in sample_files and ctx_file_name not in deleted_sample_files:
                if ctx_file_name.endswith(".sample") and ctx_file_name not in sample_files:
                    fctx = hg_util.get_file_context_from_ctx(changeset_ctx, ctx_file)
                    if fctx in ["DELETED"]:
                        # Since the possibly future used if statement above is commented out, the
                        # same file that was initially added will be discovered in an earlier changeset
                        # in the change log and fall through to the else block below.  In other words,
                        # if a file named blast2go.loc.sample was added in change set 0 and then deleted
                        # in changeset 3, the deleted file in changeset 3 will be handled here, but the
                        # later discovered file in changeset 0 will be handled in the else block below.
                        # In this way, the file contents will always be found for future tools even though
                        # the file was deleted.
                        if ctx_file_name not in deleted_sample_files:
                            deleted_sample_files.append(ctx_file_name)
                    else:
                        sample_files.append(ctx_file_name)
                        tmp_ctx_file_name = os.path.join(dir, ctx_file_name.replace(".sample", ""))
                        with open(tmp_ctx_file_name, "wb") as fh:
                            fh.write(fctx.data())
        return sample_files, deleted_sample_files

    def handle_sample_files_and_load_tool_from_disk(
        self, repo_files_dir, repository_id, tool_config_filepath, work_dir
    ):
        """
        Copy all sample files from disk to a temporary directory since the sample files may
        be in multiple directories.
        """
        message = ""
        sample_files = self.copy_disk_sample_files_to_dir(repo_files_dir, work_dir)
        if sample_files:
            if "tool_data_table_conf.xml.sample" in sample_files:
                # Load entries into the tool_data_tables if the tool requires them.
                tool_data_table_config = os.path.join(work_dir, "tool_data_table_conf.xml")
                error, message = self.stdtm.handle_sample_tool_data_table_conf_file(
                    tool_data_table_config, persist=False
                )
        tool, valid, message2 = self.load_tool_from_config(repository_id, tool_config_filepath)
        message = self.concat_messages(message, message2)
        return tool, valid, message, sample_files

    def handle_sample_files_and_load_tool_from_tmp_config(
        self, repo, repository_id, changeset_revision, tool_config_filename, work_dir
    ):
        tool = None
        valid = False
        message = ""
        # We're not currently doing anything with the returned list of deleted_sample_files here.  It is
        # intended to help handle sample files that are in the manifest, but have been deleted from disk.
        sample_files, deleted_sample_files = self.get_list_of_copied_sample_files(
            repo, changeset_revision, dir=work_dir
        )
        if sample_files:
            if "tool_data_table_conf.xml.sample" in sample_files:
                # Load entries into the tool_data_tables if the tool requires them.
                tool_data_table_config = os.path.join(work_dir, "tool_data_table_conf.xml")
                error, message = self.stdtm.handle_sample_tool_data_table_conf_file(
                    tool_data_table_config, persist=False
                )
        manifest_ctx, ctx_file = hg_util.get_ctx_file_path_from_manifest(tool_config_filename, repo, changeset_revision)
        if manifest_ctx and ctx_file:
            tool, valid, message2 = self.load_tool_from_tmp_config(
                repo, repository_id, manifest_ctx, ctx_file, work_dir
            )
            message = self.concat_messages(message, message2)
        return tool, valid, message, sample_files

    def load_tool_from_changeset_revision(self, repository_id, changeset_revision, tool_config_filename):
        """
        Return a loaded tool whose tool config file name (e.g., filtering.xml) is the value
        of tool_config_filename.  The value of changeset_revision is a valid (downloadable)
        changeset revision.  The tool config will be located in the repository manifest between
        the received valid changeset revision and the first changeset revision in the repository,
        searching backwards.
        """
        repository = repository_util.get_repository_in_tool_shed(self.app, repository_id)
        repo_files_dir = repository.repo_path(self.app)
        repo = repository.hg_repo
        tool_config_filepath = repository_util.get_absolute_path_to_file_in_repository(
            repo_files_dir, tool_config_filename
        )
        work_dir = tempfile.mkdtemp(prefix="tmp-toolshed-ltfcr")
        can_use_disk_file = self.can_use_tool_config_disk_file(
            repository, repo, tool_config_filepath, changeset_revision
        )
        if can_use_disk_file:
            tool, valid, message, sample_files = self.handle_sample_files_and_load_tool_from_disk(
                repo_files_dir, repository_id, tool_config_filepath, work_dir
            )
            if tool is not None:
                invalid_files_and_errors_tups = self.check_tool_input_params(
                    repo_files_dir, tool_config_filename, tool, sample_files
                )
                if invalid_files_and_errors_tups:
                    message2 = tool_util.generate_message_for_invalid_tools(
                        self.app,
                        invalid_files_and_errors_tups,
                        repository,
                        metadata_dict=None,
                        as_html=True,
                        displaying_invalid_tool=True,
                    )
                    message = self.concat_messages(message, message2)
        else:
            tool, valid, message, sample_files = self.handle_sample_files_and_load_tool_from_tmp_config(
                repo, repository_id, changeset_revision, tool_config_filename, work_dir
            )
        basic_util.remove_dir(work_dir)
        # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
        self.stdtm.reset_tool_data_tables()
        return repository, tool, valid, message

    def load_tool_from_tmp_config(self, repo, repository_id, ctx, ctx_file, work_dir):
        tool = None
        valid = False
        message = ""
        tmp_tool_config = hg_util.get_named_tmpfile_from_ctx(ctx, ctx_file, work_dir)
        if tmp_tool_config:
            tool_element, error_message = parse_xml(tmp_tool_config)
            if tool_element is None:
                return tool, message
            # Look for external files required by the tool config.
            tmp_code_files = []
            external_paths = Tool.get_externally_referenced_paths(tmp_tool_config)
            changeset_revision = str(ctx)
            for path in external_paths:
                tmp_code_file_name = hg_util.copy_file_from_manifest(repo, changeset_revision, path, work_dir)
                if tmp_code_file_name:
                    tmp_code_files.append(tmp_code_file_name)
            tool, valid, message = self.load_tool_from_config(repository_id, tmp_tool_config)
            for tmp_code_file in tmp_code_files:
                try:
                    os.unlink(tmp_code_file)
                except Exception:
                    pass
            try:
                os.unlink(tmp_tool_config)
            except Exception:
                pass
        return tool, valid, message
