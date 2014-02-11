from os.path import join
from os.path import relpath
from re import compile
from contextlib import contextmanager

from ..staging import COMMAND_VERSION_FILENAME
from ..action_mapper import FileActionMapper


from logging import getLogger
log = getLogger(__name__)

# All output files marked with from_work_dir attributes will copied or downloaded
# this pattern picks up attiditional files to copy back - such as those
# associated with multiple outputs and metadata configuration. Set to .* to just
# copy everything
COPY_FROM_WORKING_DIRECTORY_PATTERN = compile(r"primary_.*|galaxy.json|metadata_.*|dataset_\d+\.dat|dataset_\d+_files.+")


def finish_job(client, cleanup_job, job_completed_normally, galaxy_outputs, lwr_outputs):
    """ Responsible for downloading results from remote server and cleaning up
    LWR staging directory (if needed.)
    """
    download_failure_exceptions = []
    if job_completed_normally:
        downloader = ResultsDownloader(client, galaxy_outputs, lwr_outputs)
        download_failure_exceptions = downloader.download()
    return __clean(download_failure_exceptions, cleanup_job, client)


class ResultsDownloader(object):

    def __init__(self, client, galaxy_outputs, lwr_outputs):
        self.client = client
        self.galaxy_outputs = galaxy_outputs
        self.lwr_outputs = lwr_outputs
        self.action_mapper = FileActionMapper(client)
        self.downloaded_working_directory_files = []
        self.exception_tracker = DownloadExceptionTracker()
        self.output_files = galaxy_outputs.output_files
        self.working_directory_contents = lwr_outputs.working_directory_contents or []

    def download(self):
        self.__download_working_directory_outputs()
        self.__download_outputs()
        self.__download_version_file()
        self.__download_other_working_directory_files()
        return self.exception_tracker.download_failure_exceptions

    def __download_working_directory_outputs(self):
        working_directory = self.galaxy_outputs.working_directory
        # Fetch explicit working directory outputs.
        for source_file, output_file in self.galaxy_outputs.work_dir_outputs:
            name = relpath(source_file, working_directory)
            remote_name = self.lwr_outputs.path_helper.remote_name(name)
            with self.exception_tracker():
                action = self.action_mapper.action(output_file, 'output_workdir')
                self.client.fetch_work_dir_output(remote_name, working_directory, output_file, action_type=action.action_type)
                self.downloaded_working_directory_files.append(remote_name)
            # Remove from full output_files list so don't try to download directly.
            self.output_files.remove(output_file)

    def __download_outputs(self):
        # Legacy LWR not returning list of files, iterate over the list of
        # expected outputs for tool.
        for output_file in self.output_files:
            # Fetch ouptut directly...
            with self.exception_tracker():
                action = self.action_mapper.action(output_file, 'output')
                output_generated = self.lwr_outputs.has_output_file(output_file)
                working_directory = self.galaxy_outputs.working_directory
                if output_generated is None:
                    self.client.fetch_output_legacy(output_file, working_directory, action_type=action.action_type)
                elif output_generated:
                    self.client.fetch_output(output_file, action_type=action.action_type)

            for local_path, remote_name in self.lwr_outputs.output_extras(output_file).iteritems():
                with self.exception_tracker():
                    action = self.action_mapper.action(local_path, 'output')
                    self.client.fetch_output(path=local_path, name=remote_name, action_type=action.action_type)
            # else not output generated, do not attempt download.

    def __download_version_file(self):
        version_file = self.galaxy_outputs.version_file
        # output_directory_contents may be none for legacy LWR servers.
        lwr_output_directory_contents = (self.lwr_outputs.output_directory_contents or [])
        if version_file and COMMAND_VERSION_FILENAME in lwr_output_directory_contents:
            action = self.action_mapper.action(version_file, 'output')
            self.client.fetch_output(path=version_file, name=COMMAND_VERSION_FILENAME, action_type=action.action_type)

    def __download_other_working_directory_files(self):
        working_directory = self.galaxy_outputs.working_directory
        # Fetch remaining working directory outputs of interest.
        for name in self.working_directory_contents:
            if name in self.downloaded_working_directory_files:
                continue
            if COPY_FROM_WORKING_DIRECTORY_PATTERN.match(name):
                with self.exception_tracker():
                    output_file = join(working_directory, self.lwr_outputs.path_helper.local_name(name))
                    action = self.action_mapper.action(output_file, 'output_workdir')
                    self.client.fetch_work_dir_output(name, working_directory, output_file, action_type=action.action_type)
                    self.downloaded_working_directory_files.append(name)


class DownloadExceptionTracker(object):

    def __init__(self):
        self.download_failure_exceptions = []

    @contextmanager
    def __call__(self):
        try:
            yield
        except Exception as e:
            self.download_failure_exceptions.append(e)


def __clean(download_failure_exceptions, cleanup_job, client):
    failed = (len(download_failure_exceptions) > 0)
    if (not failed and cleanup_job != "never") or cleanup_job == "always":
        try:
            client.clean()
        except:
            log.warn("Failed to cleanup remote LWR job")
    return failed

__all__ = [finish_job]
