<%!
import os
import yaml
import shlex
import random
import shutil
import hashlib
import subprocess
import ConfigParser

%>

<%def name="set_id(name)">
<%
    """
        IEs must register their name, so it can be used in constructing strings

        Additionally this method stores lots of config options we want to access elsewhere.
    """
    self.attr.viz_id = name
    self.attr.history_id = trans.security.encode_id( trans.history.id )
    self.attr.galaxy_config = trans.app.config
    self.attr.galaxy_root_dir = os.path.abspath(self.attr.galaxy_config.root)
    self.attr.root = h.url_for("/")
    self.attr.app_root = self.attr.root + "plugins/visualizations/" + self.attr.viz_id + "/static/"

    # Store our template and configuration path
    self.attr.our_config_dir = os.path.join(plugin_path, "config")
    self.attr.our_template_dir = os.path.join(plugin_path, "templates")
    self.attr.viz_config = ConfigParser.SafeConfigParser(default_dict)
    self.attr.viz_config.read( os.path.join( self.attr.our_config_dir, self.attr.viz_id + ".conf" ) )
    # Store some variables we want by default
    self.attr.PASSWORD_AUTH = self.attr.viz_config.getboolean("main", "password_auth")
    self.attr.APACHE_URLS = self.attr.viz_config.getboolean("main", "apache_urls")
    self.attr.SSL_URLS = self.attr.viz_config.getboolean("main", "ssl")
    self.attr.PORT = self.proxy_request_port()

    self.attr.HOST = request.host.rsplit(':', 1)[0]
%>
</%def>

<%def name="write_conf_file(output_directory, extra={})">
<%
    """
        Build up a configuration file that is standard for ALL IEs.

        TODO: replace hashed password with plaintext.
    """
    conf_file = {
        'history_id': self.attr.history_id,
        'galaxy_url': request.application_url.rstrip('/') + '/',
        'api_key': get_api_key(),
        'remote_host': request.remote_addr,
        'galaxy_paster_port': self.get_galaxy_paster_port(self.attr.galaxy_root_dir,
                                                          self.attr.galaxy_config),
        'docker_port': self.attr.PORT,
        'cors_origin': request.host_url,
    }

    if self.attr.PASSWORD_AUTH:
        # Generate a random password + salt
        notebook_pw_salt = self.generate_password(length=12)
        notebook_pw = self.generate_password(length=24)
        m = hashlib.sha1()
        m.update( notebook_pw + notebook_pw_salt )
        conf_file['notebook_password'] = 'sha1:%s:%s' % (notebook_pw_salt, m.hexdigest())
        # Should we use password based connection or "default" connection style in galaxy
    else:
        notebook_pw = "None"

    # Some will need to pass extra data
    for extra_key in extra:
        conf_file[extra_key] = extra[extra_key]

    self.attr.notebook_pw = notebook_pw
    # Write conf
    with open( os.path.join( output_directory, 'conf.yaml' ), 'wb' ) as handle:
        handle.write( yaml.dump(conf_file, default_flow_style=False) )

%>
</%def>

<%def name="get_galaxy_paster_port(galaxy_root_dir, galaxy_config)">
  <%
    """
        Get port galaxy is running on (if running under paster)
    """
    config = ConfigParser.SafeConfigParser({'port': '8080'})
    config.read( os.path.join( galaxy_root_dir, 'universe_wsgi.ini' ) )

    # uWSGI galaxy installations don't use paster and only speak uWSGI not http
    try:
        port = config.getint('server:%s' % galaxy_config.server_name, 'port')
    except:
        port = None
    return port
  %>
</%def>

<%def name="proxy_request_port()">
<%
    """
        Refactor of our port getting...eventually this will be replaced with an API call instead.
    """
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

    # Generate random free port number for our docker container
    while True:
        port = random.randrange(10000,15000)
        if port not in occupied_ports:
            break
    return port
%>
</%def>

<%def name="generate_hex(length)">
<%
    """
        Generate a hex string
    """
    return ''.join(random.choice('0123456789abcdef') for _ in range(length))
%>
</%def>

<%def name="generate_password(length)">
<%
    """
        Generate a random alphanumeric password
    """
    return ''.join(random.choice('0123456789abcdefghijklmnopqrstuvwxyz') for _ in range(length))
%>
</%def>

<%def name="javascript_boolean(python_boolean)">
<%
    """
        Convenience function to convert boolean for use in JS
    """
    if python_boolean:
        return "true";
    else:
        return "false"
%>
</%def>


<%def name="url_template(url_template)">
<%
    """
        Process a URL template

        There are several variables accessible to the user:

            - ${PROTO} will be replaced with protocol (http/https)
            - ${HOST} will be replaced with the correct hostname
            - ${PORT} will be replaced with the port the docker image is attached to

        In the case that `apache_urls = False`, the first instance of HOST has a PORT appeneded to
        it, so the user doesn't have to template 2x urls.
    """
    # Figure out our substitutions
    if self.attr.SSL_URLS:
        protocol = 'https'
    else:
        protocol = 'http'

    if not self.attr.APACHE_URLS:
        # If they are not using apache URLs, that implies there's a port attached to the host
        # string, thus we replace just the first instance of host that we see.
        url_template = url_template.replace('${HOST}', '${HOST}:${PORT}', 1)

    url = url_template.replace('${PROTO}', protocol) \
            .replace('${HOST}', self.attr.HOST) \
            .replace('${PORT}', str(self.attr.PORT))
    return url
%>
</%def>


<%def name="docker_cmd(temp_dir)">
<%
    """
        Generate and return the docker command to execute
    """
    return '%s run -d --sig-proxy=true -p %s:%s -v "%s:/import/" %s' % \
        (self.attr.viz_config.get("docker", "command"), self.attr.PORT, self.attr.docker_port,
         temp_dir, self.attr.viz_config.get("docker", "image"))
%>
</%def>


<%def name="default_javascript_variables()">
// Globals
ie_password_auth = ${ self.javascript_boolean(self.attr.PASSWORD_AUTH) };
ie_apache_urls = ${ self.javascript_boolean(self.attr.APACHE_URLS) };
ie_password = '${ self.attr.notebook_pw }';
var galaxy_root = '${ self.attr.root }';
var app_root = '${ self.attr.app_root }';
</%def>


<%def name="load_default_js()">
${h.css( 'base' ) }
${h.js( 'libs/jquery/jquery',
        'libs/toastr',
        'libs/require')}
</%def>
