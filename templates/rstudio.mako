<%namespace file="ie.mako" name="ie"/>
<%
import os
import shutil
import tempfile
import time
import subprocess

# Sets ID and sets up a lot of other variables
ie.set_id("rstudio")
# Inform the IE of the remote port on docker's end
ie.attr.docker_port = 8787
# Create tempdir in galaxy
temp_dir = os.path.abspath( tempfile.mkdtemp() )
# Write out conf file...needs work
ie.write_conf_file(temp_dir, {'notebook_username': 'galaxy'})
USERNAME = "galaxy"

## General IE specific
# Access URLs for the notebook from within galaxy.
notebook_access_url = ie.url_template('${PROTO}://${HOST}/auth-sign-in')
notebook_login_url = ie.url_template('${PROTO}://${HOST}/auth-sign-in')

docker_cmd = ie.docker_cmd(temp_dir)
subprocess.call(docker_cmd, shell=True)
print docker_cmd

time.sleep(5)

try:
    # Get n, e from public key file
    with open(os.path.join(temp_dir, 'rserver_pub_key'), 'r') as pub_key_handle:
        n, e = pub_key_handle.read().split(':')
except:
    n = 0
    e = 0
    pass


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
var notebook_username = '${ USERNAME }';
var payload = "${ USERNAME }" + "\n" + ie_password;
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
    var rsa = new RSAKey();
    rsa.setPublic("${ e }", "${ n }");
    var res = rsa.encrypt(payload);
    var v = hex2b64(res);
    load_notebook(v, notebook_login_url, notebook_access_url);
});
</script>
<div id="main" width="100%" height="100%">
</div>
</body>
</html>
