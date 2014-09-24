<%
import os
import sys
import time
import yaml
import shlex
import random
import shutil
import crypt
import tempfile
import subprocess
import ConfigParser


def gen_hex_str(length=12):
    return ''.join(random.choice('0123456789abcdef') for _ in range(length))

def generate_password(length=12):
    return ''.join(random.choice('0123456789qwertzuiopasdfghjklyxcvbnm') for _ in range(length))

def generate_sha512(salt, password):
    return crypt.crypt(password, '$6$%s' % salt)

def find_occupied_ports():
    # Find all ports that are already occupied
    cmd_netstat = shlex.split("netstat -tuln")
    p1 = subprocess.Popen(cmd_netstat, stdout=subprocess.PIPE)

    occupied_ports = set()
    for line in p1.stdout.read().split('\n'):
        if line.startswith('tcp') or line.startswith('tcp6'):
            col = line.split()
            local_address = col[3]
            local_port = local_address.split(':')[-1]
            occupied_ports.add( int(local_port) )
    return occupied_ports

def find_free_port():
    # Generate random free port number for our docker container
    while True:
        PORT = random.randrange(10000,15000)
        if PORT not in find_occupied_ports():
            break
    return PORT

def get_host():
    HOST = request.host
    # Strip out port, we just want the URL this galaxy server was accessed at.
    if ':' in HOST:
        HOST = HOST[0:HOST.index(':')]
    return HOST

galaxy_root_dir = os.path.abspath(trans.app.config.root)
history_id = trans.security.encode_id( trans.history.id )
dataset_id = trans.security.encode_id( hda.id )

config = ConfigParser.SafeConfigParser({'port': '8080'})
config.read( os.path.join( galaxy_root_dir, 'universe_wsgi.ini' ) )

galaxy_paster_port = config.getint('server:main', 'port')

# Find out where we are
viz_plugin_dir = config.get('app:main', 'visualization_plugins_directory')
if not os.path.isabs(viz_plugin_dir):
    # If it is NOT absolute, i.e. relative, append to galaxy root
    viz_plugin_dir = os.path.join(galaxy_root_dir, viz_plugin_dir)
# Get this plugin's directory
viz_plugin_dir = os.path.join(viz_plugin_dir, "rstudio")
# Store our template and configuration path
our_config_dir = os.path.join(viz_plugin_dir, "config")
our_template_dir = os.path.join(viz_plugin_dir, "templates")
ipy_viz_config = ConfigParser.SafeConfigParser({'apache_urls': False, 'command': 'docker', 'image':
                                                'rstudio-notebook'})
ipy_viz_config.read( os.path.join( our_config_dir, "rstudio.conf" ) )

PORT = find_free_port()
PORT=7777
HOST = get_host()

PASSWORD = generate_password(24)
PASSWORD = "password"
USERNAME = "galaxy"
salt = generate_password(12)


temp_dir = os.path.abspath( tempfile.mkdtemp() )

# Copy a single dataset in
for dataset in trans.history.active_datasets:
    shutil.copy( dataset.file_name, os.path.join( temp_dir, str( dataset.hid ) ) )

conf_file = {
    'history_id': history_id,
    #'galaxy_url': request.application_url.rstrip('/'),
    #'api_key': trans.user.api_keys[0].key,
    #'remote_host': request.remote_addr,
    #'galaxy_paster_port': galaxy_paster_port,
    'docker_port': PORT,
    'use_auth': True,
    'notebook_username': USERNAME,
    'notebook_password': generate_sha512(salt, PASSWORD)
}


with open( os.path.join( temp_dir, 'conf.yaml' ), 'wb' ) as handle:
    handle.write( yaml.dump(conf_file, default_flow_style=False) )


docker_cmd = '%s run -d --sig-proxy=true -p %s:8787 -v "%s:/import/" %s' % \
    (ipy_viz_config.get("docker", "command"), PORT, temp_dir, ipy_viz_config.get("docker", "image"))
print docker_cmd

if ipy_viz_config.getboolean("main", "apache_urls"):
    notebook_access_url = "http://%s/rstudio/%s/" % ( HOST, PORT )
    notebook_login_url = "http://%s/rstudio/%s/" % ( HOST, PORT )
    apache_urls_jsvar = "true"
else:
    notebook_access_url = "http://%s:%s/" % ( HOST, PORT )
    notebook_login_url = "http://%s:%s/auth-sign-in" % ( HOST, PORT )
    #apache_urls_jsvar = "false"
subprocess.call(docker_cmd, shell=True)

# We need to wait until the Image and IPython in loaded
# TODO: This can be enhanced later, with some JS spinning if needed.
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
${h.css( 'base' ) }
${h.js( 'libs/jquery/jquery' ) }
${h.js( 'libs/toastr' ) }
//<script src="http://www-cs-students.stanford.edu/~tjw/jsbn/rsa.js"></script>
//<script src="http://www-cs-students.stanford.edu/~tjw/jsbn/jsbn.js"></script>
//<script src="http://www-cs-students.stanford.edu/~tjw/jsbn/rng.js"></script>
//<script src="http://www-cs-students.stanford.edu/~tjw/jsbn/prng4.js"></script>
//<script src="http://www-cs-students.stanford.edu/~tjw/jsbn/base64.js"></script>
</head>
<body>
Password: ${ PASSWORD }
<script type="text/javascript">



$( document ).ready(function() {


//var payload = "${ USERNAME }" + "\n" + "${ PASSWORD }";
//var rsa = new RSAKey();
//rsa.setPublic("${ n }", "${ e }");
//var res = rsa.encrypt(payload);
//var v = hex2b64(res);
//




//        // Make an AJAX POST
//        $.ajax({
//            type: "POST",
//            // to the Login URL
//            url: "${ notebook_login_url }",
//            // With our password
//            data: {
//                'v': v,
//                'clientPath': '/auth-do-signin',
//            },
//            success: function(){
//                console.log("Success");
//            }
//            error: function(jqxhr, status, error){
//                console.log("Error" + status +"\n" + error);
//            }
//        });
//    $('body').append('<object data="${ notebook_access_url }" height="100%" width="100%">'
//    +'<embed src="${ notebook_access_url }" height="100%" width="100%"/></object>'
//    );
});
</script>
</body>
</html>
