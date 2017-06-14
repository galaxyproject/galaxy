<%namespace name="ie" file="ie.mako"/>

<%
import os
import shutil
import time

# Sets ID and sets up a lot of other variables
ie_request.load_deploy_config()
ie_request.attr.docker_port = 80
PASSWORD = "rstudio"
USERNAME = "rstudio"
# Then override it again
ie_request.notebook_pw = "rstudio"

additional_ids = trans.request.params.get('additional_dataset_ids', None)
if not additional_ids:
    additional_ids = str(trans.security.encode_id( hda.id ) )
else:
    additional_ids += "," + trans.security.encode_id( hda.id )

DATASET_HID = hda.hid

# Add all environment variables collected from Galaxy's IE infrastructure
ie_request.launch(
    image=trans.request.params.get('image_tag', None),
    additional_ids=additional_ids if ie_request.use_volumes else None,
    env_override={
        'notebook_username': USERNAME,
        'notebook_password': PASSWORD,
        'dataset_hid': DATASET_HID,
        'additional_ids': additional_ids if not ie_request.use_volumes else None,
    }
)

## General IE specific
# Access URLs for the notebook from within galaxy.
notebook_access_url = ie_request.url_template('${PROXY_URL}/rstudio/')
notebook_login_url = ie_request.url_template('${PROXY_URL}/rstudio/auth-do-sign-in')
notebook_pubkey_url = ie_request.url_template('${PROXY_URL}/rstudio/auth-public-key')

%>
<html>
<head>
${ ie.load_default_js() }
</head>
<body style="margin: 0px">

<script type="text/javascript">
${ ie.default_javascript_variables() }
var notebook_login_url = '${ notebook_login_url }';
var notebook_access_url = '${ notebook_access_url }';
var notebook_pubkey_url = '${ notebook_pubkey_url }';
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
        load_notebook(notebook_login_url, notebook_access_url, notebook_pubkey_url);
    });
});
</script>
<div id="main" width="100%" height="100%">
</div>
</body>
</html>
