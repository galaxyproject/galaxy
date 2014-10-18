<%
import os
import sys
import time
import yaml
import shlex
import random
import shutil
import hashlib
import tempfile
import subprocess
import ConfigParser

galaxy_root_dir = os.path.abspath(trans.app.config.root)
history_id = trans.security.encode_id( trans.history.id )
dataset_id = trans.security.encode_id( hda.id )

config = ConfigParser.SafeConfigParser({'port': '8080'})
config.read( os.path.join( galaxy_root_dir, 'universe_wsgi.ini' ) )

galaxy_paster_port = config.getint('server:main', 'port')

# Find out where we are
viz_plugin_dir = config.get('app:main', 'visualization_plugins_directory')
if not os.path.isabs(viz_plugin_dir):
    # If it is NOT absolute, i.e. relative, append to galaxy root
    viz_plugin_dir = os.path.join(galaxy_root_dir, viz_plugin_dir)
# Get this plugin's directory
viz_plugin_dir = os.path.join(viz_plugin_dir, "ipython")
# Store our template and configuration path
our_config_dir = os.path.join(viz_plugin_dir, "config")
our_template_dir = os.path.join(viz_plugin_dir, "templates")
ipy_viz_config = ConfigParser.SafeConfigParser({'apache_urls': False, 'command': 'docker', 'image':
                                                'bgruening/docker-ipython-notebook'})
ipy_viz_config.read( os.path.join( our_config_dir, "ipython.conf" ) )

# Ensure generation of notebook id is deterministic for the dataset. Replace with history id
# whenever we figure out how to access that.
random.seed( history_id )
notebook_id = ''.join(random.choice('0123456789abcdef') for _ in range(64))

with open( os.path.join( our_template_dir, 'notebook.ipynb' ), 'r') as nb_handle:
    empty_nb = nb_handle.read()
empty_nb = empty_nb % notebook_id


# Find all ports that are already occupied
cmd_netstat = shlex.split("netstat -tuln")
p1 = subprocess.Popen(cmd_netstat, stdout=subprocess.PIPE)

occupied_ports = set()
for line in p1.stdout.read().split('\n'):
    if line.startswith('tcp') or line.startswith('tcp6'):
        col = line.split()
        local_address = col[3]
        local_port = local_address.split(':')[-1]
        occupied_ports.add( int(local_port) )

# Generate random free port number for our docker container
while True:
    PORT = random.randrange(10000,15000)
    if PORT not in occupied_ports:
        break

HOST = request.host
# Strip out port, we just want the URL this galaxy server was accessed at.
if ':' in HOST:
    HOST = HOST[0:HOST.index(':')]

temp_dir = os.path.abspath( tempfile.mkdtemp() )

# Generate a random password + salt
notebook_pw_salt = ''.join(random.choice('0123456789abcdefghijklmnopqrstuvwxyz') for _ in range(12))
notebook_pw = ''.join(random.choice('0123456789abcdefghijklmnopqrstuvwxyz') for _ in range(24))
m = hashlib.sha1()
m.update( notebook_pw + notebook_pw_salt )

conf_file = {
    'history_id': history_id,
    'galaxy_url': request.application_url.rstrip('/'),
    'api_key': trans.user.api_keys[0].key,
    'remote_host': request.remote_addr,
    'galaxy_paster_port': galaxy_paster_port,
    'docker_port': PORT,
    'notebook_password': 'sha1:%s:%s' % (notebook_pw_salt, m.hexdigest()),
}

with open( os.path.join( temp_dir, 'conf.yaml' ), 'wb' ) as handle:
    handle.write( yaml.dump(conf_file, default_flow_style=False) )

empty_nb_path = os.path.join(temp_dir, 'ipython_galaxy_notebook.ipynb')
if hda.datatype.__class__.__name__ != "Ipynb":
    with open( empty_nb_path, 'w+' ) as handle:
        handle.write( empty_nb )
else:
    shutil.copy( hda.file_name, empty_nb_path )

docker_cmd = '%s run -d --sig-proxy=true -p %s:6789 -v "%s:/import/" %s' % \
    (ipy_viz_config.get("docker", "command"), PORT, temp_dir, ipy_viz_config.get("docker", "image"))

if ipy_viz_config.getboolean("main", "apache_urls"):
    notebook_access_url = "http://%s/ipython/%s/notebooks/ipython_galaxy_notebook.ipynb" % ( HOST, PORT )
else:
    notebook_access_url = "http://%s:%s/ipython/%s/notebooks/ipython_galaxy_notebook.ipynb" % ( HOST, PORT, PORT )
subprocess.call(docker_cmd, shell=True)

# We need to wait until the Image and IPython in loaded
# TODO: This can be enhanced later, with some JS spinning if needed.
time.sleep(1)

%>
<html>


<body>
Your password is: ${ notebook_pw }
    <object data="${notebook_access_url}" height="100%" width="100%">
        <embed src="${notebook_access_url}" height="100%" width="100%">
        </embed>
    </object>
</body>
</html>
