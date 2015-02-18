Galaxy
======

.. figure:: https://wiki.galaxyproject.org/Images/Logos?action=AttachFile&do=get&target=galaxyLogoTrimmed.png
   :alt: Galaxy Logo

   Galaxy Logo
`galaxyproject.org <http://galaxyproject.org/>`__

The latest information about Galaxy is always available via the Galaxy
website above.

Starting Galaxy
---------------

Galaxy requires Python 2.6 or 2.7. To check your python version, run:

.. code:: console

    $ python -V
    Python 2.7.3

Start Galaxy:

.. code:: console

    $ sh run.sh

Once Galaxy completes startup, you should be able to view Galaxy in your
browser at:

http://localhost:8080

You may wish to make changes from the default configuration. This can be
done in the ``config/galaxy.ini`` file. Tools can be either installed
from the Tool Shed or added manually. For details please see the Galaxy
wiki:

https://wiki.galaxyproject.org/Admin/Tools/AddToolFromToolShedTutorial

Not all dependencies are included for the tools provided in the sample
``tool_conf.xml``. A full list of external dependencies is available at:

https://wiki.galaxyproject.org/Admin/Tools/ToolDependencies

Issues
------

Issues can be submitted to trello via the `galaxyproject
website <http://galaxyproject.org/trello/>`__ and viewed on the `Galaxy
Trello Board <https://trello.com/b/75c1kASa/galaxy-development>`__
