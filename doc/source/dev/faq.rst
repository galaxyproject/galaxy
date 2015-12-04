How Do I...
===========

This section contains a number of smaller topics with links and examples meant
to provide relatively concrete answers for specific Galaxy development scenarios.

... interact with the Galaxy codebase interactively?
----------------------------------------------------

This can be done with either IPython/Jupyter or a plain python console, depending on your preferences::

    python -i scripts/db_shell.py

... build Galaxy Javascript frontend client?
--------------------------------------------

We've added a makefile which will let you do this. If you have docker installed, you can simple run::

    make grunt-docker

Otherwise, you can run

    make grunt
