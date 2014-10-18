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
     "level": 1,
     "metadata": {},
     "source": [
      "Welcome to the interactive Galaxy IPython Notebook."
     ]
    },
    {
     "cell_type": "markdown",
     "metadata": {},
     "source": [
      "You can access your data via the dataset number. For example, `handle = get(42)`.\\n",
      "To save data, write your data to a file, and then call `put('filename.txt')`. The dataset will then be available in your galaxy history."
     ]
    },
    {
     "cell_type": "code",
     "collapsed": false,
     "input": [
      "# This button just calls put('ipython_galaxy_notebook.ipynb')"
     ],
     "language": "python",
     "metadata": {},
     "outputs": [
      {
       "html": [
        "<button onclick=\\\"save()\\\">Save Notebook to Galaxy</button>\\n",
        "<script type=\\\"text/Javascript\\\">\\n",
        "    function save(){\\n",
        "        console.log(IPython.notebook.kernel.execute(\\\"put('ipython_galaxy_notebook.ipynb')\\\"));\\n",
        "    }\\n",
        "</script>\\n"
       ],
       "metadata": {},
       "output_type": "pyout",
       "prompt_number": 1,
       "text": [
        "<IPython.core.display.HTML at 0x3b33650>"
       ]
      }
     ],
     "prompt_number": 1
    },
    {
     "cell_type": "code",
     "collapsed": false,
     "input": [
     ],
     "language": "python",
     "metadata": {},
     "outputs": [],
     "prompt_number": 2
    }
   ],
   "metadata": {}
  }
 ]
}
""" % (notebook_id, )


# Find all ports that are already occupied
import shlex
cmd_netstat = shlex.split("netstat -tuln")
p1 = subprocess.Popen(cmd_netstat, stdout=subprocess.PIPE)

cmd_awk = shlex.split("awk 'NR >= 3 { print $4 }'")
p2 = subprocess.Popen(cmd_awk, stdin=p1.stdout, stdout=subprocess.PIPE)

cmd_cut = shlex.split("cut -d: -f2")
p3 = subprocess.Popen(cmd_cut, stdin=p2.stdout, stdout=subprocess.PIPE)

cmd_sort = shlex.split("sort -un")
p4 = subprocess.Popen(cmd_sort, stdin=p3.stdout, stdout=subprocess.PIPE)

netstat_out = p4.stdout.read()

occupied_ports = [port for port in netstat_out.split('\n') if port.isdigit()]

# Generate random free port number for our docker container
while True:
    PORT = random.randrange(10000,15000)
    if PORTS not in occupied_ports:
        break
HOST = request.host
# Strip out port, we just want the URL this galaxy server was accessed at.
if ':' in HOST:
    HOST = HOST[0:HOST.index(':')]

temp_dir = os.path.abspath( tempfile.mkdtemp() )

############### Getting of port galaxy is being served on.
p1 = subprocess.Popen(shlex.split("""ps a"""), stdout=subprocess.PIPE)
p2 = subprocess.Popen(shlex.split("""grep 'python ./scripts'"""), stdin=p1.stdout,
                      stdout=subprocess.PIPE)
p3 = subprocess.Popen(shlex.split("""grep -v 'grep'"""), stdin=p2.stdout, stdout=subprocess.PIPE)
p4 = subprocess.Popen(shlex.split("""awk '{print $1}'"""), stdin=p3.stdout, stdout=subprocess.PIPE)
# Only take first PID in case we have multiple.
galaxy_paster_pid = p4.stdout.read().split('\n')[0]
galaxy_paster_port = None
if len(galaxy_paster_pid) > 0:
    # Find all files opened by the process of interest
    p1 = subprocess.Popen(shlex.split("""lsof -p %d""" % (int(galaxy_paster_pid),) ),
                          stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    # Grep out the TCP connections opened by this process
    p2 = subprocess.Popen(shlex.split("""grep -o 'TCP [^:]*:[0-9]*'"""), stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    # Remove 'TCP *:' from 'TCP *:4000'
    p3 = subprocess.Popen(shlex.split("""cut -d: -f2"""), stdin=p2.stdout,
                          stdout=subprocess.PIPE)
    galaxy_paster_port = p3.stdout.read().strip()

conf_file = {
    'history_id': history_id,
    'galaxy_url': request.application_url,
    'api_key': trans.user.api_keys[0].key,
    'remote_host': request.remote_addr,
    'galaxy_paster_port': galaxy_paster_port,
}
with open( os.path.join( temp_dir, 'conf.yaml' ), 'wb' ) as handle:
    handle.write( yaml.dump(conf_file, default_flow_style=False) )

# TODO: Implement proper IPyNB datatype atop a proper JSON datatype
# For now we assume all "text" datatypes are ipynbs.
# <datatype extension="ipynb" type="galaxy.datatypes.data:Text" mimetype="application/json" subclass="True" display_in_upload="True"/>
empty_nb_path = os.path.join(temp_dir, 'ipython_galaxy_notebook.ipynb')
if hda.datatype.__class__.__name__ != "Text":
    with open( empty_nb_path, 'w+' ) as handle:
        handle.write( empty_nb )
else:
    shutil.copy( hda.file_name, empty_nb_path )

docker_cmd = 'docker run -d --sig-proxy=true -p %s:6789 -v "%s:/import/" bgruening/docker-ipython-notebook' % (PORT, temp_dir)
subprocess.call(docker_cmd, shell=True)

# We need to wait until the Image and IPython in loaded
# TODO: This can be enhanced later, with some JS spinning if needed.
time.sleep(1)

%>
<html>


<body>
    <object data="http://${HOST}:${PORT}/notebooks/ipython_galaxy_notebook.ipynb" height="100%" width="100%">
        <embed src="http://${HOST}:${PORT}/notebooks/ipython_galaxy_notebook.ipynb" height="100%" width="100%">
        </embed>
    </object>
</body>
</html>
