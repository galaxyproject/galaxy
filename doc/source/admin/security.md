# Security considerations

### Protect Galaxy against data loss due to misbehaving tools

Tools have access to the paths of input and output data sets which are stored in
``file_path`` and by default the credentials used for running tools are the same
as for running Galaxy. Thus its possible that tools modify data in Galaxy's
``file_path``. Examples for such changes are:

- Creation of additional files, e.g. indices, which is a problem for cleaning up data, because Galaxy does not know about these files.
- Removal of input or output files of the tools. This will create problems with other tools using these data sets (note that most tool repositories use CI tests to to avoid this, but the problem may still occur).

Note that the tool only knows the paths to inputs and outputs, but if using the default configuration for other paths (e.g. configuration directory) also these paths are easily accessible.

There are three approaches to protect Galaxy against this:

- Use different credentials for running tools. This can be configured using the ``real_system_username`` config variable.
- Configure Galaxy to run jobs in a container and enable ``outputs_to_working_directory``. Then the tool will execute in an environment that allows write access only for the job working dir. All other paths will be accessible read only. 
- Use pulsar to stage inputs and outputs

More information on pulsar configuration can be found in the [job configuration](jobs.md) documentation, and the other two are explained in [using a compute cluster](cluster.md).
