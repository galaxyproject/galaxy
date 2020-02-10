# Supported Python versions

Galaxy's core functionality is currently supported on Python **2.7** (although
deprecated) and **>=3.5** .

If Galaxy complains about the version of Python you are using, check that
`python --version` reports a supported version. If this is not the case:

1. Completely remove the virtualenv used by Galaxy, e.g. with:
   `rm -rf /path/to/galaxy/.venv`

2. Let Galaxy know the path of the correct version of Python.

    - If you are using Galaxy >= 20.05, just execute:
      `export GALAXY_PYTHON=/path/to/python`
    - If instead you are using an older version of Galaxy, you can manipulate
      your shell's `$PATH` variable to place the correct version first. This can
      be done for just Python by creating a new directory, adding a symbolic
      link to python in there, and putting that directory at the front of
      `$PATH`:

        ```sh
        % mkdir ~/galaxy-python
        % ln -s /path/to/python ~/galaxy-python/python
        % export PATH=~/galaxy-python:$PATH
        ```

3. Start Galaxy again.

N.B. If you have compiled your own Python interpreter from source, please ensure
that the `ssl`, `sqlite3`, `curses` and `bz2` modules were built and can be
imported after installation. These "extra" modules are built at the end of the
compilation process and are required by the Galaxy framework. If building on
Linux, you may need to install the appropriate `-dev` packages for OpenSSL and
Bzip2. You may also need to build Python with shared libraries
(`--enable-shared`).

