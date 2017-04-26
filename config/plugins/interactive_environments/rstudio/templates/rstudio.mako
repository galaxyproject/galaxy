<%namespace file="ie.mako" name="ie"/>
<%
import os
import shutil
import time

# Sets ID and sets up a lot of other variables
ie_request.load_deploy_config()
ie_request.attr.docker_port = 80
# Create tempdir in galaxy
temp_dir = ie_request.temp_dir
PASSWORD = "rstudio"
USERNAME = "rstudio"
# Then override it again
ie_request.notebook_pw = "rstudio"

# Did the user give us an RData file?
if hda.datatype.__class__.__name__ == "RData":
    shutil.copy( hda.file_name, os.path.join(temp_dir, '.RData') )

ie_request.launch(
    image=trans.request.params.get('image_tag', None),
    additional_ids=trans.request.params.get('additional_dataset_ids', None),
    env_override={
        'notebook_username': USERNAME,
        'notebook_password': PASSWORD,
    }
)

## General IE specific
# Access URLs for the notebook from within galaxy.
# TODO: Make this work without pointing directly to IE. Currently does not work
# through proxy.
notebook_pubkey_url = ie_request.url_template('${PROXY_URL}/rstudio/auth-public-key')
notebook_access_url = ie_request.url_template('${PROXY_URL}/rstudio/')
notebook_login_url =  ie_request.url_template('${PROXY_URL}/rstudio/auth-do-sign-in')

%>
<html>
<head>
${ ie.load_default_js() }
</head>
<body style="margin:0px">
<script type="text/javascript">
${ ie.default_javascript_variables() }
var notebook_login_url = '${ notebook_login_url }';
var notebook_access_url = '${ notebook_access_url }';
var notebook_pubkey_url = '${ notebook_pubkey_url }';
var notebook_username = '${ USERNAME }';
require.config({
    baseUrl: app_root,
    paths: {
        "interactive_environments": "${h.url_for('/static/scripts/galaxy.interactive_environments')}",
        "plugin" : app_root + "js/",
        "crypto" : app_root + "js/crypto/",
    },
});
requirejs([
    'interactive_environments',
    'crypto/prng4',
    'crypto/rng',
    'crypto/rsa',
    'crypto/jsbn',
    'crypto/base64',
    'plugin/rstudio'
], function(){
    load_when_ready(ie_readiness_url, function(){
        load_notebook(notebook_login_url, notebook_access_url, notebook_pubkey_url, "${ USERNAME }");
    });
});
</script>
<div id="main">
</div>
</body>
</html>
