# Security considerations

## Protect Galaxy against data loss due to misbehaving tools

Tools have access to the paths of input and output data sets which are stored in
``file_path``. If tools use reference data stored in data tables, they have access also to data in
``tool_data_path`` and ``shed_tool_data_path`` (plus data referred in hand
crafted loc files and refgenie configuration). 

By default the credentials used for running tools are the same as for running
Galaxy. Thus it is possible that a tool modifies data in Galaxy's ``file_path``.
Examples of such potential changes are:

- Creation of additional files, e.g. indices, which is a problem for cleaning up data, because Galaxy does not know about these files.
- Removal of tool input or output files. This will create problems with other tools using these datasets (note that most tool repositories use CI tests to to avoid this, but the problem may still occur).

Note that a tool only knows the paths to its inputs and outputs, but if using the default configuration for other paths (e.g. the configuration directory) also these paths can be calculated and accessed.

There are three approaches to protect Galaxy against these risks:

- Configure Galaxy to run jobs in a container and enable ``outputs_to_working_directory``. Then the tool will execute in an environment that allows write access only for the job working dir. All other paths will be accessible read only. 
- Use [Pulsar](https://pulsar.readthedocs.io/) to stage inputs and outputs.
- If containers and Pulsar are not an option, it is possible to use different credentials for running tools. This can be configured using the ``real_system_username`` config variable. Note that you also need to enable ``outputs_to_working_directory`` when enabling ``real_system_username``. Furthermore, check that files in directories like ``file_path`` and ``tool_data_path`` are writable only by the user running Galaxy. 

More information on pulsar configuration can be found in the [job configuration](jobs.md) documentation, and the other two are explained in [using a compute cluster](cluster.md).
