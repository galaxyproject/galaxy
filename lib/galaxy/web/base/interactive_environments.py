import ConfigParser

import hashlib
import os
import random

from galaxy.util.bunch import Bunch
from galaxy import web
import yaml
from galaxy.managers import api_keys


class InteractiveEnviornmentRequest(object):

    def __init__(self, trans, plugin):
        plugin_config = plugin.config

        self.trans = trans

        self.attr = Bunch()
        self.attr.viz_id = plugin_config["name"].lower()
        self.attr.history_id = trans.security.encode_id( trans.history.id )
        self.attr.proxy_request = trans.app.proxy_manager.setup_proxy( trans )
        self.attr.proxy_url = self.attr.proxy_request[ 'proxy_url' ]
        self.attr.galaxy_config = trans.app.config
        self.attr.galaxy_root_dir = os.path.abspath(self.attr.galaxy_config.root)

        self.attr.root = web.url_for("/")
        self.attr.app_root = self.attr.root + "plugins/visualizations/" + self.attr.viz_id + "/static/"

        plugin_path = os.path.abspath( plugin.path )

        # Store our template and configuration path
        self.attr.our_config_dir = os.path.join(plugin_path, "config")
        self.attr.our_template_dir = os.path.join(plugin_path, "templates")
        self.attr.HOST = trans.request.host.rsplit(':', 1)[0]
        self.attr.PORT = self.attr.proxy_request[ 'proxied_port' ]

    def load_deploy_config(self, default_dict={}):
        viz_config = ConfigParser.SafeConfigParser(default_dict)
        conf_path = os.path.join( self.attr.our_config_dir, self.attr.viz_id + ".ini" )
        if not os.path.exists( conf_path ):
            conf_path = "%s.sample" % conf_path
        viz_config.read( conf_path )
        self.attr.viz_config = viz_config

        # Older style port range proxying - not sure we want to keep these around or should
        # we always assume use of Galaxy dynamic proxy? None of these need to be specified
        # if using the Galaxy dynamic proxy.
        self.attr.PASSWORD_AUTH = self.attr.viz_config.getboolean("main", "password_auth")
        self.attr.APACHE_URLS = self.attr.viz_config.getboolean("main", "apache_urls")
        self.attr.SSL_URLS = self.attr.viz_config.getboolean("main", "ssl")

    def write_conf_file(self, output_directory, extra={}):
        """
            Build up a configuration file that is standard for ALL IEs.

            TODO: replace hashed password with plaintext.
        """
        trans = self.trans
        request = trans.request
        api_key = api_keys.ApiKeyManager( trans.app ).get_or_create_api_key( trans.user )
        conf_file = {
            'history_id': self.attr.history_id,
            'api_key': api_key,
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

    def generate_hex(self, length):
        return ''.join(random.choice('0123456789abcdef') for _ in range(length))

    def generate_password(self, length):
        """
            Generate a random alphanumeric password
        """
        return ''.join(random.choice('0123456789abcdefghijklmnopqrstuvwxyz') for _ in range(length))

    def javascript_boolean(self, python_boolean):
        """
            Convenience function to convert boolean for use in JS
        """
        if python_boolean:
            return "true"
        else:
            return "false"

    def url_template(self, url_template):
        """
            Process a URL template

            There are several variables accessible to the user:

                - ${PROXY_URL} will be replaced with dynamically create proxy
                - ${PORT} will be replaced with the port the docker image is attached to
        """
        # Figure out our substitutions

        # Next several lines for older style replacements (not used with Galaxy dynamic
        # proxy)

        if self.attr.SSL_URLS:
            protocol = 'https'
        else:
            protocol = 'http'

        if not self.attr.APACHE_URLS:
            # If they are not using apache URLs, that implies there's a port attached to the host
            # string, thus we replace just the first instance of host that we see.
            url_template = url_template.replace('${HOST}', '${HOST}:${PORT}', 1)

        url_template = url_template.replace('${PROTO}', protocol) \
            .replace('${HOST}', self.attr.HOST)

        # Only the following replacements are used with Galaxy dynamic proxy
        # URLs
        url = url_template.replace('${PROXY_URL}', str(self.attr.proxy_url)) \
            .replace('${PORT}', str(self.attr.PORT))
        return url

    def docker_cmd(self, temp_dir):
        """
            Generate and return the docker command to execute
        """
        return '%s run -d --sig-proxy=true -p %s:%s -v "%s:/import/" %s' % \
            (self.attr.viz_config.get("docker", "command"), self.attr.PORT, self.attr.docker_port,
             temp_dir, self.attr.viz_config.get("docker", "image"))
