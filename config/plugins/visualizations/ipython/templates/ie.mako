<%!
import os
import sys
import time
import yaml
import shlex
import random
import shutil
import hashlib
import tempfile
import subprocess
import ConfigParser

%>

<%def name="set_id(name)">
<%
    self.attr.viz_id = name
%>
</%def>

<%def name="register_galaxy_objects(trans, h, response, plugin_path, request)">
<%
    self.attr.trans = trans
    self.attr.history_id = trans.security.encode_id( trans.history.id )
    self.attr.h = h
    self.attr.plugin_path = plugin_path
    self.attr.response = response
    self.attr.galaxy_config = trans.app.config
    self.attr.galaxy_root_dir = os.path.abspath(self.attr.galaxy_config.root)
    self.attr.root = h.url_for("/")
    self.attr.app_root = self.attr.root + "plugins/visualizations/ipython/static/"
    self.attr.request = request
%>
</%def>

<%def name="register_defaults(default_dict)">
<%
    # Store our template and configuration path
    self.attr.our_config_dir = os.path.join(self.attr.plugin_path, "config")
    self.attr.our_template_dir = os.path.join(self.attr.plugin_path, "templates")
    ipy_viz_config = ConfigParser.SafeConfigParser(default_dict)
    ipy_viz_config.read( os.path.join( self.attr.our_config_dir, "ipython.conf" ) )
    self.attr.ipy_viz_config = ipy_viz_config
    # Store some variables we want by default
    self.attr.PASSWORD_AUTH = self.attr.ipy_viz_config.getboolean("main", "password_auth")
    self.attr.APACHE_URLS = self.attr.ipy_viz_config.getboolean("main", "apache_urls")
    self.attr.SSL_URLS = self.attr.ipy_viz_config.getboolean("main", "ssl")
    self.attr.PORT = self.proxy_request_port()

    HOST = self.attr.request.host
    # Strip out port, we just want the URL this galaxy server was accessed at.
    if ':' in HOST:
        HOST = HOST[0:HOST.index(':')]
    self.attr.HOST = HOST
%>
</%def>

<%def name="write_conf_file(output_directory)">
<%
    conf_file = {
        'history_id': self.attr.history_id,
        'galaxy_url': self.attr.request.application_url.rstrip('/') + '/',
        'api_key': self.attr.api_key,
        'remote_host': self.attr.request.remote_addr,
        'galaxy_paster_port': self.get_galaxy_paster_port(self.attr.galaxy_root_dir,
                                                          self.attr.galaxy_config),
        'docker_port': self.attr.PORT,
        'cors_origin': self.attr.request.host_url,
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

    self.attr.notebook_pw = notebook_pw
    # Write conf
    with open( os.path.join( output_directory, 'conf.yaml' ), 'wb' ) as handle:
        handle.write( yaml.dump(conf_file, default_flow_style=False) )

%>
</%def>

<%def name="get_galaxy_paster_port(galaxy_root_dir, galaxy_config)">
  <%
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
    return ''.join(random.choice('0123456789abcdef') for _ in range(length))
%>
</%def>

<%def name="generate_password(length)">
<%
    return ''.join(random.choice('0123456789abcdefghijklmnopqrstuvwxyz') for _ in range(length))
%>
</%def>

<%def name="javascript_boolean(length)">
<%
    """
        Convenience function to convert boolean for use in JS
    """
    if boolean:
        return "true";
    else:
        return "false"
%>
</%def>


<%def name="url_template(url_template)">
<%
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
    return '%s run -d --sig-proxy=true -p %s:6789 -v "%s:/import/" %s' % \
        (self.attr.ipy_viz_config.get("docker", "command"), self.attr.PORT, temp_dir,
         self.attr.ipy_viz_config.get("docker", "image"))
%>
</%def>


<%def name="default_javascript_variables()">
var password_auth = ${ self.javascript_boolean(self.attr.PASSWORD_AUTH) };
var apache_urls = ${ self.javascript_boolean(self.attr.APACHE_URLS) };
var password = '${ self.attr.notebook_pw }';
var galaxy_root = '${ self.attr.root }';
</%def>


<%def name="load_default_js()">
${h.css( 'base' ) }
${h.js( 'libs/jquery/jquery' ) }
${h.js( 'libs/toastr' ) }
${h.javascript_link( ie.attr.app_root + 'ie.js' )}
${h.javascript_link( ie.attr.app_root + ie.attr.viz_name + '.js' )}
</%def>
