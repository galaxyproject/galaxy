import os
from .util import filter_destination_params

REMOTE_SYSTEM_PROPERTY_PREFIX = "remote_property_"


def build(client, destination_args):
    """ Build a SetupHandler object for client from destination parameters.
    """
    # Have defined a remote job directory, lets do the setup locally.
    if client.job_directory:
        handler = LocalSetupHandler(client, destination_args)
    else:
        handler = RemoteSetupHandler(client)
    return handler


class LocalSetupHandler(object):
    """ Parse destination params to infer job setup parameters (input/output
    directories, etc...). Default is to get this configuration data from the
    remote Pulsar server.

    Downside of this approach is that it requires more and more dependent
    configuraiton of Galaxy. Upside is that it is asynchronous and thus makes
    message queue driven configurations possible.

    Remote system properties (such as galaxy_home) can be specified in
    destination args by prefixing property with remote_property_ (e.g.
    remote_property_galaxy_home).
    """

    def __init__(self, client, destination_args):
        self.client = client
        system_properties = self.__build_system_properties(destination_args)
        system_properties["separator"] = client.job_directory.separator
        self.system_properties = system_properties
        self.jobs_directory = destination_args["jobs_directory"]

    def setup(self, job_id, tool_id=None, tool_version=None):
        return build_job_config(
            job_id=job_id,
            job_directory=self.client.job_directory,
            system_properties=self.system_properties,
            tool_id=tool_id,
            tool_version=tool_version,
        )

    @property
    def local(self):
        """
        """
        return True

    def __build_system_properties(self, destination_params):
        return filter_destination_params(destination_params, REMOTE_SYSTEM_PROPERTY_PREFIX)


class RemoteSetupHandler(object):
    """ Default behavior. Fetch setup information from remote Pulsar server.
    """
    def __init__(self, client):
        self.client = client

    def setup(self, **setup_args):
        return self.client.remote_setup(**setup_args)

    @property
    def local(self):
        """
        """
        return False


def build_job_config(job_id, job_directory, system_properties={}, tool_id=None, tool_version=None):
    """
    """
    inputs_directory = job_directory.inputs_directory()
    working_directory = job_directory.working_directory()
    outputs_directory = job_directory.outputs_directory()
    configs_directory = job_directory.configs_directory()
    tools_directory = job_directory.tool_files_directory()
    unstructured_files_directory = job_directory.unstructured_files_directory()
    sep = system_properties.get("sep", os.sep)
    job_config = {
        "working_directory": working_directory,
        "outputs_directory": outputs_directory,
        "configs_directory": configs_directory,
        "tools_directory": tools_directory,
        "inputs_directory": inputs_directory,
        "unstructured_files_directory": unstructured_files_directory,
        # Poorly named legacy attribute. Drop at some point.
        "path_separator": sep,
        "job_id": job_id,
        "system_properties": system_properties,
    }
    if tool_id:
        job_config["tool_id"] = tool_id
    if tool_version:
        job_config["tool_version"] = tool_version
    return job_config


__all__ = [build_job_config, build]
