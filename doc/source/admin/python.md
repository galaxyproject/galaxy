# Supported Python versions

Galaxy's core functionality is currently supported on Python **>=3.8** .

If Galaxy complains about the version of Python you are using:

1. Completely remove the Python virtualenv used by Galaxy (which can be
   configured with the `GALAXY_VIRTUAL_ENV` environment variable and defaults to
   `.venv`), e.g. with: `rm -rf /path/to/galaxy/.venv`

2. If you were using a Python from a conda environment (which can be configured
   with the `GALAXY_CONDA_ENV` environment variable and defaults to `_galaxy_`),
   remove it, e.g. with: `conda env remove -n _galaxy_`

3. Let Galaxy know which Python to use in one of the following methods:

    - If you want to use Python from conda, just activate the `base` environment
      and Galaxy will create a new conda environment for itself.
    - Otherwise:
        1. Make sure a supported version of Python is installed.
        2. Verify that the Python interpreter you want to use is first in the
           output of `which -a python3 python` (or `which -a python` if you are
           using Galaxy <=19.09). If this is not the case:
           - If you are using Galaxy >= 20.01, just execute:
             `export GALAXY_PYTHON=/path/to/python`
           - If instead you are using an older version of Galaxy, you can
            manipulate your shell's `PATH` variable to place the correct version
            first. This can be done for just Python by creating a new directory,
            adding a symbolic link to `python` in there, and putting that
            directory at the front of `PATH`:

              ```sh
              % mkdir ~/galaxy-python
              % ln -s /path/to/python ~/galaxy-python/python
              % export PATH=~/galaxy-python:$PATH
              ```

4. Remove compiled mako templates when upgrading from Python 2:
     ```sh
     % rm -rf /path/to/galaxy/database/compiled_templates/
     ```
   These templated will be regenerated automatically when starting Galaxy.

5. Start Galaxy again.

N.B. If you have compiled your own Python interpreter from source, please ensure
that the `ssl`, `sqlite3`, `curses` and `bz2` modules were built and can be
imported after installation. These "extra" modules are built at the end of the
compilation process and are required by the Galaxy framework. If building on
Linux, you may need to install the appropriate `-dev` packages for OpenSSL and
Bzip2. You may also need to build Python with shared libraries
(`--enable-shared`).
