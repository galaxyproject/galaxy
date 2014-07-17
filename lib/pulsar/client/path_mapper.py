import os.path
from .action_mapper import FileActionMapper
from .action_mapper import path_type
from .util import PathHelper

from galaxy.util import in_directory


class PathMapper(object):
    """ Ties together a FileActionMapper and remote job configuration returned
    by the Pulsar setup method to pre-determine the location of files for staging
    on the remote Pulsar server.

    This is not useful when rewrite_paths (as has traditionally been done with
    the Pulsar) because when doing that the Pulsar determines the paths as files are
    uploaded. When rewrite_paths is disabled however, the destination of files
    needs to be determined prior to transfer so an object of this class can be
    used.
    """

    def __init__(
        self,
        client,
        remote_job_config,
        local_working_directory,
        action_mapper=None,
    ):
        self.local_working_directory = local_working_directory
        if not action_mapper:
            action_mapper = FileActionMapper(client)
        self.action_mapper = action_mapper
        self.input_directory = remote_job_config["inputs_directory"]
        self.output_directory = remote_job_config["outputs_directory"]
        self.working_directory = remote_job_config["working_directory"]
        self.unstructured_files_directory = remote_job_config["unstructured_files_directory"]
        self.config_directory = remote_job_config["configs_directory"]
        separator = remote_job_config["system_properties"]["separator"]
        self.path_helper = PathHelper(separator)

    def remote_output_path_rewrite(self, local_path):
        output_type = path_type.OUTPUT
        if in_directory(local_path, self.local_working_directory):
            output_type = path_type.OUTPUT_WORKDIR
        remote_path = self.__remote_path_rewrite(local_path, output_type)
        return remote_path

    def remote_input_path_rewrite(self, local_path):
        remote_path = self.__remote_path_rewrite(local_path, path_type.INPUT)
        return remote_path

    def remote_version_path_rewrite(self, local_path):
        remote_path = self.__remote_path_rewrite(local_path, path_type.OUTPUT, name="COMMAND_VERSION")
        return remote_path

    def check_for_arbitrary_rewrite(self, local_path):
        path = str(local_path)  # Use false_path if needed.
        action = self.action_mapper.action(path, path_type.UNSTRUCTURED)
        if not action.staging_needed:
            return action.path_rewrite(self.path_helper), []
        unique_names = action.unstructured_map()
        name = unique_names[path]
        remote_path = self.path_helper.remote_join(self.unstructured_files_directory, name)
        return remote_path, unique_names

    def __remote_path_rewrite(self, dataset_path, dataset_path_type, name=None):
        """ Return remote path of this file (if staging is required) else None.
        """
        path = str(dataset_path)  # Use false_path if needed.
        action = self.action_mapper.action(path, dataset_path_type)
        if action.staging_needed:
            if name is None:
                name = os.path.basename(path)
            remote_directory = self.__remote_directory(dataset_path_type)
            remote_path_rewrite = self.path_helper.remote_join(remote_directory, name)
        else:
            # Actions which don't require staging MUST define a path_rewrite
            # method.
            remote_path_rewrite = action.path_rewrite(self.path_helper)

        return remote_path_rewrite

    def __action(self, dataset_path, dataset_path_type):
        path = str(dataset_path)  # Use false_path if needed.
        action = self.action_mapper.action(path, dataset_path_type)
        return action

    def __remote_directory(self, dataset_path_type):
        if dataset_path_type in [path_type.OUTPUT]:
            return self.output_directory
        elif dataset_path_type in [path_type.WORKDIR, path_type.OUTPUT_WORKDIR]:
            return self.working_directory
        elif dataset_path_type in [path_type.INPUT]:
            return self.input_directory
        else:
            message = "PathMapper cannot handle path type %s" % dataset_path_type
            raise Exception(message)

__all__ = [PathMapper]
