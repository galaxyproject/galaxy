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

additional_ids = trans.request.params.get('additional_dataset_ids', None)

## Jupyter Notbook Specific
if hda.datatype.__class__.__name__ == "Ipynb":
    DATASET_HID = hda.hid
else:
    DATASET_HID = None
    if not additional_ids:
        additional_ids = str(trans.security.encode_id( hda.id ) )
    else:
        additional_ids += "," + trans.security.encode_id( hda.id )

# Add all environment variables collected from Galaxy's IE infrastructure
ie_request.launch(
    image=trans.request.params.get('image_tag', None),
    additional_ids=additional_ids if ie_request.use_volumes else None,
    env_override={
        'notebook_password': PASSWORD,
        'dataset_hid': DATASET_HID,
        'additional_ids': additional_ids if not ie_request.use_volumes else None,
    }
)

## General IE specific
# Access URLs for the notebook from within galaxy.
notebook_access_url = ie_request.url_template('${PROXY_URL}/ipython/notebooks/ipython_galaxy_notebook.ipynb')
notebook_login_url = ie_request.url_template('${PROXY_URL}/ipython/login?next=${PROXY_PREFIX}%2Fipython%2Ftree')
notebook_keepalive_url = ie_request.url_template('${PROXY_URL}/ipython/tree')

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
var notebook_keepalive_url = '${ notebook_keepalive_url }';
${ ie.plugin_require_config() }

// Load notebook

requirejs(['galaxy.interactive_environments', 'plugin/jupyter'], function(IES){
    // This global is not awesome, get rid of it when possible (when IES are a part of the build process)
    window.IES = IES;
    IES.load_when_ready(ie_readiness_url, function(){
        load_notebook(ie_password, notebook_login_url, notebook_access_url);
    });
});





</script>
<div id="main" width="100%" height="100%">
</div>
</body>
</html>
