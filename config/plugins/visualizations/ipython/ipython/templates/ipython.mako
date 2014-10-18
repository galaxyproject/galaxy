<%
import os
import sys
import tempfile
import shutil
import time
import subprocess
import yaml
import random


history_id = trans.security.encode_id( trans.history.id )
dataset_id = trans.security.encode_id( hda.id )
# Ensure generation of notebook id is deterministic for the dataset. Replace with history id
# whenever we figure out how to access that.
random.seed( history_id )
notebook_id = ''.join(random.choice('0123456789abcdef') for _ in range(64))
empty_nb = """{
 "metadata": {
  "name": "",
  "signature": "sha256:%s"
 },
 "nbformat": 3,
 "nbformat_minor": 0,
 "worksheets": [
  {
   "cells": [
    {
     "cell_type": "heading",
     "level": 2,
     "metadata": {},
     "source": [
      "Welcome to the interactive Galaxy IPython Notebook."
     ]
    },
    {
     "cell_type": "markdown",
     "metadata": {},
     "source": [
      "You can access your data via the dataset number. For example: handle = open('42', 'r')"
     ]
    },
    {
     "cell_type": "code",
     "collapsed": false,
     "input": [],
     "language": "python",
     "metadata": {},
     "outputs": []
    }
   ],
   "metadata": {}
  }
 ]
}""" % (notebook_id, )

PORT = 7777

temp_dir = os.path.abspath( tempfile.mkdtemp() )

# TODO: Provide a method to allow selecting which datasets are used
for dataset in trans.history.active_datasets:
    shutil.copy( dataset.file_name, os.path.join( temp_dir, str( hda.hid ) ) )


conf_file = {
    'history_id': history_id,
    'galaxy_url': None,
    'api_key': None,
}
with open( os.path.join( temp_dir, 'conf.yaml' ), 'wb' ) as handle:
    handle.write( yaml.dump(conf_file) )

empty_nb_path = os.path.join(temp_dir, 'ipython_galaxy_notebook.ipynb')
with open( empty_nb_path, 'w+' ) as handle:
    handle.write( empty_nb )

docker_cmd = 'docker run -d --sig-proxy=true -p %s:6789 -v "%s:/import/" bgruening/docker-ipython-notebook' % (PORT, temp_dir)

subprocess.call(docker_cmd, shell=True)

# We need to wait until the Image and IPython in loaded
# TODO: This can be enhanced later, with some JS spinning if needed.
time.sleep(1)

%>
<html>


<body>
    <object data="http://localhost:${PORT}/notebooks/ipython_galaxy_notebook.ipynb" height="100%" width="100%">
        <embed src="http://localhost:${PORT}/notebooks/ipython_galaxy_notebook.ipynb" height="100%" width="100%">
        </embed>
    </object>
</body>
</html>
