<%namespace file="ie.mako" name="ie"/>
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

ie.set_id("ipython")
ie.register_galaxy_objects(trans, h, response, plugin_path)
ie.register_defaults({
    'apache_urls': False,
    'command': 'docker',
    'image': 'bgruening/docker-ipython-notebook',
    'password_auth': False,
    'ssl': False})

galaxy_paster_port = ie.get_galaxy_paster_port(ie.attr.galaxy_root_dir, ie.attr.galaxy_config)


#PASSWORD_AUTH = ie.attr.ipy_viz_config.getboolean("main", "password_auth")
#APACHE_URLS = ie.attr.ipy_viz_config.getboolean("main", "apache_urls")
#SSL_URLS = ie.attr.ipy_viz_config.getboolean("main", "ssl")
PASSWORD_AUTH = False
APACHE_URLS = False
SSL_URLS = False
PORT = ie.proxy_request_port()
HOST = request.host
# Strip out port, we just want the URL this galaxy server was accessed at.
if ':' in HOST:
    HOST = HOST[0:HOST.index(':')]

temp_dir = os.path.abspath( tempfile.mkdtemp() )
api_key = get_api_key()

conf_file = {
    'history_id': ie.attr.history_id,
    'galaxy_url': request.application_url.rstrip('/') + '/',
    'api_key': api_key,
    'remote_host': request.remote_addr,
    'galaxy_paster_port': galaxy_paster_port,
    'docker_port': PORT,
    'cors_origin': request.host_url,
}

if PASSWORD_AUTH:
    # Generate a random password + salt
    notebook_pw_salt = ie.generate_password(length=12)
    notebook_pw = ie.generate_password(length=24)
    m = hashlib.sha1()
    m.update( notebook_pw + notebook_pw_salt )
    conf_file['notebook_password'] = 'sha1:%s:%s' % (notebook_pw_salt, m.hexdigest())
    # Should we use password based connection or "default" connection style in galaxy
else:
    notebook_pw = "None"

# Write conf
with open( os.path.join( temp_dir, 'conf.yaml' ), 'wb' ) as handle:
    handle.write( yaml.dump(conf_file, default_flow_style=False) )

# Prepare an empty notebook
notebook_id = ie.generate_hex(64)
with open( os.path.join( ie.attr.our_template_dir, 'notebook.ipynb' ), 'r') as nb_handle:
    empty_nb = nb_handle.read()
empty_nb = empty_nb % notebook_id
# Copy over default notebook, unless the dataset this viz is running on is a notebook
empty_nb_path = os.path.join(temp_dir, 'ipython_galaxy_notebook.ipynb')
if hda.datatype.__class__.__name__ != "Ipynb":
    with open( empty_nb_path, 'w+' ) as handle:
        handle.write( empty_nb )
else:
    shutil.copy( hda.file_name, empty_nb_path )

docker_cmd = ie.docker_cmd(ie.attr.ipy_viz_config, PORT, temp_dir)

# Set our proto so passwords don't go in clear
if SSL_URLS:
    PROTO = "https"
else:
    PROTO = "http"

# Access URLs for the notebook from within galaxy.
if APACHE_URLS:
    notebook_access_url = "%s://%s/ipython/%s/notebooks/ipython_galaxy_notebook.ipynb" % ( PROTO, HOST, PORT )
    notebook_login_url = "%s://%s/ipython/%s/login" % ( PROTO, HOST, PORT )
else:
    notebook_access_url = "%s://%s:%s/ipython/%s/notebooks/ipython_galaxy_notebook.ipynb" % ( PROTO, HOST, PORT, PORT )
    notebook_login_url = "%s://%s:%s/ipython/%s/login" % ( PROTO, HOST, PORT, PORT )
subprocess.call(docker_cmd, shell=True)

%>
<html>
<head>
${h.css( 'base' ) }
${h.js( 'libs/jquery/jquery' ) }
${h.js( 'libs/toastr' ) }
## Load IPython-Galaxy connector
${h.javascript_link( ie.attr.app_root + 'ipy-galaxy.js' )}
</head>
<body>

<script type="text/javascript">
var password_auth = ${ ie.javascript_boolean(PASSWORD_AUTH) };
var apache_urls = ${ ie.javascript_boolean(APACHE_URLS) };
var notebook_login_url = '${ notebook_login_url }';
var password = '${ notebook_pw }';
var notebook_access_url = '${ notebook_access_url }';
var galaxy_root = '${ ie.attr.root }';
// Load notebook
load_notebook(password_auth, password, notebook_login_url, notebook_access_url, apache_urls, galaxy_root);
</script>

<div id="main" width="100%" height="100%">
</div>

</body>
</html>
