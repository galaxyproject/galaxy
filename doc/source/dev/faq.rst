How Do I...
===========

This section contains a number of smaller topics with links and examples meant
to provide relatively concrete answers for specific Galaxy development scenarios.

... interact with the Galaxy database interactively?
----------------------------------------------------

This can be done with either IPython or a plain Python console, depending on your preferences::

    python -i scripts/db_shell.py

... build Galaxy Javascript frontend client?
--------------------------------------------

We've added a makefile which will let you do this. You can simple run::

    make client

If you prefer docker and aren't a JS developer primarily, you can run

    make grunt-docker

Please see the ``Makefile`` itself for details and other options. There is also a readme at
``client/README.md``.


