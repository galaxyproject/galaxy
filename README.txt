GALAXY
======
http://galaxyproject.org/

The latest information about Galaxy is always available via the Galaxy
website above.

HOW TO START
============
Galaxy requires Python 2.6 or 2.7. To check your python version, run:

% python -V
Python 2.7.3

Start Galaxy:

% sh run.sh

Once Galaxy completes startup, you should be able to view Galaxy in your
browser at:

http://localhost:8080

You may wish to make changes from the default configuration. This can be done
in the config/galaxy.ini file. Tools can be either installed from the Tool Shed
or added manually. For details please see the Galaxy wiki: 

https://wiki.galaxyproject.org/Admin/Tools/AddToolFromToolShedTutorial


Not all dependencies are included for the tools provided in the sample
tool_conf.xml. A full list of external dependencies is available at:

https://wiki.galaxyproject.org/Admin/Tools/ToolDependencies
