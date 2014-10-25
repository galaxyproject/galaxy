<%namespace file="ie.mako" name="ie"/>
<%
import os
import shutil
import tempfile
import time
import subprocess

# Sets ID and sets up a lot of other variables
ie.set_id("rstudio")
# In order to keep 302 redirects happy, nginx needs to be aware there's a proxy in front of it,
# which may be using a different port. As a result, we have to start nginx on whichever port it is
# we plan to use.
ie.attr.docker_port = ie.attr.PORT
# Create tempdir in galaxy
temp_dir = os.path.abspath( tempfile.mkdtemp() )
# Write out conf file...needs work
ie.write_conf_file(temp_dir, {'notebook_username': 'galaxy'})
USERNAME = "galaxy"

## General IE specific
# Access URLs for the notebook from within galaxy.
notebook_pubkey_url = ie.url_template('${PROTO}://${HOST}/rstudio/${PORT}/auth-public-key')
notebook_access_url = ie.url_template('${PROTO}://${HOST}/rstudio/${PORT}/')
notebook_login_url = ie.url_template('${PROTO}://${HOST}/rstudio/${PORT}/auth-do-sign-in')

docker_cmd = ie.docker_cmd(temp_dir)
subprocess.call(docker_cmd, shell=True)
print docker_cmd
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
var notebook_pubkey_url = '${ notebook_pubkey_url }';
var notebook_username = '${ USERNAME }';
require.config({
    baseUrl: app_root,
    paths: {
        "plugin" : app_root + "js/",
        "crypto" : app_root + "js/crypto/",
    },
});
requirejs([
    'plugin/ie',
    'plugin/rstudio',
    'crypto/prng4',
    'crypto/rng',
    'crypto/rsa',
    'crypto/jsbn',
    'crypto/base64'
], function(){
    load_notebook(notebook_login_url, notebook_access_url, notebook_pubkey_url, "${ USERNAME }");
});
</script>

<form action="auth-do-sign-in" name="realform" id="realform" method="POST">
   <input name="persist" id="persist" value="1" type="hidden">
   <input name="appUri" value="" type="hidden">
   <input name="clientPath" id="clientPath" value="/rstudio/auth-sign-in" type="hidden">
   <input id="package" name="v" value="" type="hidden">
</form>
<div id="main" width="100%" height="100%">
</div>
</body>
</html>
