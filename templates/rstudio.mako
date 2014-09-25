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
notebook_access_url = ie.url_template('${PROTO}://${HOST}/rstudio/auth-sign-in')
notebook_login_url = ie.url_template('${PROTO}://${HOST}/rstudio/auth-do-sign-in')

docker_cmd = ie.docker_cmd(temp_dir)
subprocess.call(docker_cmd, shell=True)
print docker_cmd

pub_key = os.path.join(temp_dir, 'rserver_pub_key')

# Todo, migrate to JS
try_count = 0
while True:
    try_count += 1
    if os.path.isfile(pub_key):
        print "Pubkey exists!"
        break
    else:
        print "Pubkey doesn't exist yet"
        time.sleep(1)

    if try_count > 30:
        # Throw an error?
        break

try:
    # Get n, e from public key file
    with open(os.path.join(temp_dir, 'rserver_pub_key'), 'r') as pub_key_handle:
        n, e = pub_key_handle.read().split(':')
except:
    n = 0
    e = 0
    # Throw an error?
    pass


%>
<html>
<head>
${ ie.load_default_js() }
</head>
<body>

${ ie.attr.notebook_pw };
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
