<%
import os
import sys
import tempfile
import shutil
import subprocess

empty_nb = """{
 "metadata": {
  "name": "",
  "signature": "sha256:201eaf53a7ca0a5b661e0c8925adc61714a91ac871471604c428cbda4a698239"
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
}"""

PORT = 7777

temp_dir = os.path.abspath( tempfile.mkdtemp() )
new_dataset_path = os.path.join( temp_dir, str( hda.hid ) )
shutil.copy( hda.file_name, new_dataset_path )


empty_nb_path = os.path.join(temp_dir, 'ipython_galaxy_notebook.ipynb')
with open( empty_nb_path, 'w+' ) as handle:
    handle.write( empty_nb )

docker_cmd = 'docker run -d -p %s:6789 -v "%s:/import/" bgruening/docker-ipython-notebook' % (PORT, temp_dir)

subprocess.call(docker_cmd, shell=True)


%>
<html>


<body>
    <object data="http://localhost:${PORT}/notebooks/ipython_galaxy_notebook.ipynb" height="100%" width="100%">
        <embed src="http://localhost:${PORT}/notebooks/ipython_galaxy_notebook.ipynb" height="100%" width="100%">
        </embed>
    </object>
</body>
</html>
