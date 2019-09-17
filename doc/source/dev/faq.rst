How Do I...
===========

This section contains a number of smaller topics with links and examples meant
to provide relatively concrete answers for specific Galaxy development scenarios.

... interact with the Galaxy database interactively?
----------------------------------------------------

This can be done with either IPython or a plain Python console, depending on your preferences:

.. code-block:: python

    python -i scripts/db_shell.py

... build Galaxy Javascript frontend client?
--------------------------------------------

We have added a Makefile which will let you do this. You can simply run:

.. code-block:: bash

    make client

Please see the ``Makefile`` itself for details and other options. There is also a readme at
``client/README.md``.


