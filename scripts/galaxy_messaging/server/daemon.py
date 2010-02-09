#!/usr/bin/python
"""

Data Transfer Script Daemon

This script is called from Galaxy LIMS once the lab admin starts the data 
transfer process using the user interface. This creates a child process and 
this child process starts the data_transfer.py script as a new process

This script passes all the arguments from Galaxy LIMS to the data_transfer.py script

Usage:

python daemon.py <sequencer_host> 
                <username> 
                <password> 
                <source_file> 
                <sample_id>
                <dataset_index>
                <library_id>
                <folder_id>
"""

import sys, os
# Perform first fork.
try:
    pid = os.fork( )
    if pid > 0:
        sys.exit(0) # Exit first parent.
except OSError, e:
    sys.stderr.write("fork #1 failed: (%d) %sn" % (e.errno, e.strerror))
    sys.exit(2)
os.execv(os.path.join( os.getcwd(), "scripts/galaxy_messaging/server/data_transfer.py"), sys.argv)

