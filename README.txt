GALAXY
======
http://galaxyproject.org/

The latest information about Galaxy is always available via the Galaxy
website above.

HOW TO START
============
Galaxy requires Python 2.4, 2.5 or 2.6. To check your python version, run:

% python -V
Python 2.4.4

Start Galaxy:

% sh run.sh

Once Galaxy completes startup, you should be able to view Galaxy in your
browser at:

http://localhost:8080

You may wish to make changes from the default configuration.  This can be done
in the universe_wsgi.ini file.  Tools are configured in tool_conf.xml.  Details
on adding tools can be found on the Galaxy website (linked above).

Not all dependencies are included for the tools provided in the sample
tool_conf.xml.  A full list of external dependencies is available at:

http://bitbucket.org/galaxy/galaxy-central/wiki/ToolDependencies
