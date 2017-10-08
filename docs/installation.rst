============
Installation
============

pip_
===================

For a traditional Python installation of `galaxy-lib`, first set up a virtualenv
for ``galaxy-lib`` (this example creates a new one in ``.venv``) and then
install with ``pip``.

::

    $ virtualenv .venv; . .venv/bin/activate
    $ pip install galaxy-lib

When installed this way, galaxy-lib can be upgraded as follows:

::

    $ . .venv/bin/activate
    $ pip install -U galaxy-lib

To install or update to the latest development branch of galaxy-lib with ``pip``, 
use the  following ``pip install`` idiom instead:

::

    $ pip install -U git+git://github.com/galaxyproject/galaxy-lib.git

Conda_
===================

Another approach for installing `galaxy-lib` is to use Conda_
(most easily obtained via the
`Miniconda Python distribution <http://conda.pydata.org/miniconda.html>`__).
Afterwards run the following commands.

::

    $ conda config --add channels bioconda
    $ conda install galaxy-lib


Other Applications
===================

`galaxy-lib` is bundled with various other pieces of software that leverage it
in various ways. Consider installing one those applications if they are correct
for what you are trying to accomplish.

- `Planemo <http://planemo.readthedocs.io/>`__
- `Pulsar <http://pulsar.readthedocs.io/>`__
- `cwltool <https://github.com/common-workflow-language/cwltool/blob/master/README.rst#leveraging-softwarerequirements-beta>`__

.. _pip: https://pip.pypa.io/
.. _Conda: http://conda.pydata.org/docs/
