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
    self.attr.proxy_request = trans.app.proxy_manager.setup_proxy( trans )
    self.attr.proxy_url = self.attr.proxy_request[ 'proxy_url' ]
    self.attr.galaxy_config = trans.app.config
    self.attr.galaxy_root_dir = os.path.abspath(self.attr.galaxy_config.root)
    self.attr.root = h.url_for("/")
    self.attr.app_root = self.attr.root + "plugins/visualizations/" + self.attr.viz_id + "/static/"

    # Store our template and configuration path
    self.attr.our_config_dir = os.path.join(plugin_path, "config")
    self.attr.our_template_dir = os.path.join(plugin_path, "templates")
    self.attr.viz_config = ConfigParser.SafeConfigParser(default_dict)
    conf_path = os.path.join( self.attr.our_config_dir, self.attr.viz_id + ".ini" )
    if not os.path.exists( conf_path ):
        conf_path = "%s.sample" % conf_path
    self.attr.viz_config.read( conf_path )
    # Store some variables we want by default
    self.attr.PASSWORD_AUTH = self.attr.viz_config.getboolean("main", "password_auth")
    self.attr.APACHE_URLS = self.attr.viz_config.getboolean("main", "apache_urls")
    self.attr.SSL_URLS = self.attr.viz_config.getboolean("main", "ssl")
    self.attr.PORT = self.attr.proxy_request[ 'proxied_port' ]
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
        'api_key': get_api_key(),
        'remote_host': request.remote_addr,
        'docker_port': self.attr.PORT,
        'cors_origin': request.host_url,
    }

    if self.attr.galaxy_config.galaxy_infrastructure_url_set:
        conf_file['galaxy_url'] = self.attr.galaxy_config.galaxy_infrastructure_url.rstrip('/') + '/'
    else:
        conf_file['galaxy_url'] = request.application_url.rstrip('/') + '/'
        conf_file['galaxy_paster_port'] = self.attr.galaxy_config.guess_galaxy_port()

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

            - ${PROXY_URL} will be replaced with dynamically create proxy
            - ${PORT} will be replaced with the port the docker image is attached to
    """
    url = url_template.replace('${PROXY_URL}', str(self.attr.proxy_url)) \
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
