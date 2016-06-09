<%namespace name="ie" file="ie.mako" />

<%
import os
import shutil
import hashlib

# Sets ID and sets up a lot of other variables
ie_request.load_deploy_config()
ie_request.attr.docker_port = 8888
ie_request.attr.import_volume = False

if ie_request.attr.PASSWORD_AUTH:
    m = hashlib.sha1()
    m.update( ie_request.notebook_pw + ie_request.notebook_pw_salt )
    PASSWORD = 'sha1:%s:%s' % (ie_request.notebook_pw_salt, m.hexdigest())
else:
    PASSWORD = "none"

## Jupyter Notbook Specific
if hda.datatype.__class__.__name__ == "Ipynb":
    DATASET_HID = hda.hid
else:
    DATASET_HID = None

# Add all environment variables collected from Galaxy's IE infrastructure
ie_request.launch(
    image=trans.request.params.get('image_tag', None),
    additional_ids=trans.request.params.get('additional_dataset_ids', None),
    env_override={
        'notebook_password': PASSWORD,
        'dataset_hid': DATASET_HID,
    }
)

## General IE specific
# Access URLs for the notebook from within galaxy.
notebook_access_url = ie_request.url_template('${PROXY_URL}/ipython/notebooks/ipython_galaxy_notebook.ipynb')
notebook_login_url = ie_request.url_template('${PROXY_URL}/ipython/login?next=${PROXY_PREFIX}%2Fipython%2Ftree')

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

// Keep container running
requirejs(['interactive_environments', 'plugin/jupyter'], function(){
    keep_alive();
});


// Load notebook

requirejs(['interactive_environments', 'plugin/jupyter'], function(){
    load_notebook(ie_password, notebook_login_url, notebook_access_url);
});





</script>
<div id="main" width="100%" height="100%">
</div>
</body>
</html>
