INTRO
=====

This program requires python 2.4 or later. To check your python version type:

python -V.

To start a server you need to do run the server as:

python universe.py

This will start a server on localhost port 8080. 
In your browser go to: http://localhost:8080 and you should see the 
Galaxy environment with some default tools. To customize the tools that 
are loaded see tool.conf.sample To customize the way your server is ran edit 
universe.conf 

*Note* certain tools may require certain libraries to be present.
(See run.sh for more details)


RUNTIME ENVIRONMENT
===================

The default server home will be the directory where the program starts.
You can use the UNIVERSE_HOME environment variable to point to a different
server home. The path that the UNIVERSE_HOME variable points to must be 
a directory with the following subdirectories:

database
database/files
database/import
tools

OPTIMIZED LIBRARIES
===================

To allow python to load optimized libraries the path to these must be listed 
in the python path. See the previous section or run.sh for an example. Loading 
the optimized Cheetah templating libraries can lead to significant 
performance gains. 

At startup you the log message: 

Optimized  Namemapper: True|False

will tell you whether the optimized Cheetah template was loaded (or not).

The log message:

database type: dbhash|....

will tell you what kind of underlying database is the server using. Dbhash 
stands for the BerkleyDB. The server should work fine with other libraries 
as well but BerkleyDB is provides the most reliable and efficient storage.

TOOL DEVELOPMENT
================

See the wiki pages for more details:

http://g2.bx.psu.edu


CREATING A RELEASE
==================

type:

python setup.py sdist 
