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
ie.register_galaxy_objects(trans, h, response, plugin_path, request)
ie.register_defaults({
    'apache_urls': False,
    'command': 'docker',
    'image': 'bgruening/docker-ipython-notebook',
    'password_auth': False,
    'ssl': False})

galaxy_paster_port = ie.get_galaxy_paster_port(ie.attr.galaxy_root_dir, ie.attr.galaxy_config)


PORT = ie.proxy_request_port()
HOST = request.host
# Strip out port, we just want the URL this galaxy server was accessed at.
if ':' in HOST:
    HOST = HOST[0:HOST.index(':')]

temp_dir = os.path.abspath( tempfile.mkdtemp() )
ie.attr.api_key = get_api_key()

# Write out conf file...needs work
ie.write_conf_file(temp_dir)


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


# Access URLs for the notebook from within galaxy.
notebook_access_url = ie.url_template('${PROTO}://${HOST}/ipython/${PORT}/notebooks/ipython_galaxy_notebook.ipynb')
notebook_login_url = ie.url_template('${PROTO}://${HOST}/ipython/${PORT}/login')

docker_cmd = ie.docker_cmd(temp_dir)
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
${ ie.default_javascript_variables() }
var notebook_login_url = '${ notebook_login_url }';
var notebook_access_url = '${ notebook_access_url }';
// Load notebook
load_notebook(password_auth, password, notebook_login_url, notebook_access_url, apache_urls, galaxy_root);
</script>

<div id="main" width="100%" height="100%">
</div>

</body>
</html>
