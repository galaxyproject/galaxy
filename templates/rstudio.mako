<%namespace file="ie.mako" name="ie"/>
<%
import os
import shutil
import tempfile
import subprocess

# Sets ID and sets up a lot of other variables
ie.set_id("ipython")
# Create tempdir in galaxy
temp_dir = os.path.abspath( tempfile.mkdtemp() )
# Write out conf file...needs work
ie.write_conf_file(temp_dir)

## General IE specific
# Access URLs for the notebook from within galaxy.
notebook_access_url = ie.url_template('${PROTO}://${HOST}:${PORT}/rstudio/')
notebook_login_url = ie.url_template('${PROTO}://${HOST}:${PORT}/auth-sign-in')

docker_cmd = ie.docker_cmd(temp_dir)
subprocess.call(docker_cmd, shell=True)

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
// Load notebook
//<script src="http://www-cs-students.stanford.edu/~tjw/jsbn/rsa.js"></script>
//<script src="http://www-cs-students.stanford.edu/~tjw/jsbn/jsbn.js"></script>
//<script src="http://www-cs-students.stanford.edu/~tjw/jsbn/rng.js"></script>
//<script src="http://www-cs-students.stanford.edu/~tjw/jsbn/prng4.js"></script>
//<script src="http://www-cs-students.stanford.edu/~tjw/jsbn/base64.js"></script>
//var payload = "${ USERNAME }" + "\n" + "${ PASSWORD }";
//var rsa = new RSAKey();
//rsa.setPublic("${ n }", "${ e }");
//var res = rsa.encrypt(payload);
//var v = hex2b64(res);
//

require.config({
    baseUrl: app_root,
    paths: {
        "plugin" : app_root + "js/",
    },
});
requirejs(['plugin/ie', 'plugin/rstudio'], function(){
    //load_notebook(ie_password, notebook_login_url, notebook_access_url);
});
</script>
<div id="main" width="100%" height="100%">
</div>
</body>
</html>
