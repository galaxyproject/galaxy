"""
lwr_client
==========

This module contains logic for interfacing with an external LWR server.

------------------
Configuring Galaxy
------------------

Galaxy job runners are configured in Galaxy's ``job_conf.xml`` file. See ``job_conf.xml.sample_advanced``
in your Galaxy code base or on
`Bitbucket <https://bitbucket.org/galaxy/galaxy-dist/src/tip/job_conf.xml.sample_advanced?at=default>`_
for information on how to configure Galaxy to interact with the LWR.

Galaxy also supports an older, less rich configuration of job runners directly
in its main ``galaxy.ini`` file. The following section describes how to
configure Galaxy to communicate with the LWR in this legacy mode.

Legacy
------

A Galaxy tool can be configured to be executed remotely via LWR by
adding a line to the ``galaxy.ini`` file under the ``galaxy:tool_runners``
section with the format::

    <tool_id> = lwr://http://<lwr_host>:<lwr_port>

As an example, if a host named remotehost is running the LWR server
application on port ``8913``, then the tool with id ``test_tool`` can
be configured to run remotely on remotehost by adding the following
line to ``galaxy.ini``::

    test_tool = lwr://http://remotehost:8913

Remember this must be added after the ``[galaxy:tool_runners]`` header
in the ``universe.ini`` file.


"""

from .staging.down import finish_job
from .staging.up import submit_job
from .staging import ClientJobDescription
from .staging import LwrOutputs
from .staging import ClientOutputs
from .client import OutputNotFoundException
from .manager import build_client_manager
from .destination import url_to_destination_params
from .path_mapper import PathMapper

__all__ = [
    build_client_manager,
    OutputNotFoundException,
    url_to_destination_params,
    finish_job,
    submit_job,
    ClientJobDescription,
    LwrOutputs,
    ClientOutputs,
    PathMapper,
]
