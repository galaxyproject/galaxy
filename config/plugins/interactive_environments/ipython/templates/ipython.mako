 <%namespace name="ie" file="ie.mako" />

<%
import os
import shutil
import tempfile
import subprocess

# Sets ID and sets up a lot of other variables
ie_request.load_deploy_config()
ie_request.attr.docker_port = 6789
# Create tempdir in galaxy
temp_dir = os.path.abspath( tempfile.mkdtemp() )
# Write out conf file...needs work
ie_request.write_conf_file(temp_dir)

## IPython Specific
# Prepare an empty notebook
notebook_id = ie_request.generate_hex(64)
with open( os.path.join( ie_request.attr.our_template_dir, 'notebook.ipynb' ), 'r') as nb_handle:
    empty_nb = nb_handle.read()
empty_nb = empty_nb % notebook_id
# Copy over default notebook, unless the dataset this viz is running on is a notebook
empty_nb_path = os.path.join(temp_dir, 'ipython_galaxy_notebook.ipynb')
if hda.datatype.__class__.__name__ != "Ipynb":
    with open( empty_nb_path, 'w+' ) as handle:
        handle.write( empty_nb )
else:
    shutil.copy( hda.file_name, empty_nb_path )


## General IE specific
# Access URLs for the notebook from within galaxy.
notebook_access_url = ie_request.url_template('${PROXY_URL}/ipython/${PORT}/notebooks/ipython_galaxy_notebook.ipynb')
notebook_login_url = ie_request.url_template('${PROXY_URL}/ipython/${PORT}/login?next=%2Fipython%2F${PORT}%2Ftree')

docker_cmd = ie_request.docker_cmd(temp_dir)
subprocess.call(docker_cmd, shell=True)
%>
<html>
<head>
${ ie.load_default_js() }
</head>
<body>

<script type="text/javascript">
${ ie.default_javascript_variables() }
var notebook_login_url = '${ notebook_login_url }';
var notebook_access_url = '${ notebook_access_url }';
${ ie.plugin_require_config() }

// Load notebook

requirejs(['interactive_environments', 'plugin/ipython'], function(){
    load_notebook(ie_password, notebook_login_url, notebook_access_url);
});
</script>
<div id="main" width="100%" height="100%">
</div>
</body>
</html>
