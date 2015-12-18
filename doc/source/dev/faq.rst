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

We've added a makefile which will let you do this. If you have nodejs and npm installed, you can simple run::

    make grunt

If you prefer docker and aren't a JS developer primarily, you can run

    make grunt-docker


