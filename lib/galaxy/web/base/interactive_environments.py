import ConfigParser

import os
import stat
import random
import tempfile
from subprocess import Popen, PIPE

from galaxy.util.bunch import Bunch
from galaxy import web
from galaxy.managers import api_keys
from galaxy.tools.deps.docker_util import DockerVolume

import logging
log = logging.getLogger(__name__)


class InteractiveEnviornmentRequest(object):

    def __init__(self, trans, plugin):
        plugin_config = plugin.config

        self.trans = trans
        self.log = log

        self.attr = Bunch()
        self.attr.viz_id = plugin_config["name"].lower()
        self.attr.history_id = trans.security.encode_id( trans.history.id )
        self.attr.galaxy_config = trans.app.config
        self.attr.galaxy_root_dir = os.path.abspath(self.attr.galaxy_config.root)
        self.attr.root = web.url_for("/")
        self.attr.app_root = self.attr.root + "plugins/interactive_environments/" + self.attr.viz_id + "/static/"

        plugin_path = os.path.abspath( plugin.path )

        # Store our template and configuration path
        self.attr.our_config_dir = os.path.join(plugin_path, "config")
        self.attr.our_template_dir = os.path.join(plugin_path, "templates")
        self.attr.HOST = trans.request.host.rsplit(':', 1)[0]

        self.load_deploy_config()
        self.attr.docker_hostname = self.attr.viz_config.get("docker", "docker_hostname")
        self.attr.proxy_request = trans.app.proxy_manager.setup_proxy(
            trans, host=self.attr.docker_hostname
        )
        self.attr.proxy_url = self.attr.proxy_request[ 'proxy_url' ]
        self.attr.PORT = self.attr.proxy_request[ 'proxied_port' ]

        # Generate per-request passwords the IE plugin can use to configure
        # the destination container.
        self.notebook_pw_salt = self.generate_password(length=12)
        self.notebook_pw = self.generate_password(length=24)

        self.temp_dir = os.path.abspath( tempfile.mkdtemp() )
        if self.attr.viz_config.getboolean("docker", "wx_tempdir"):
            # Ensure permissions are set
            try:
                os.chmod( self.temp_dir, os.stat(self.temp_dir).st_mode | stat.S_IXOTH )
            except Exception:
                log.error( "Could not change permissions of tmpdir %s" % self.temp_dir )
                # continue anyway

    def load_deploy_config(self, default_dict={}):
        # For backwards compat, any new variables added to the base .ini file
        # will need to be recorded here. The ConfigParser doesn't provide a
        # .get() that will ignore missing sections, so we must make use of
        # their defaults dictionary instead.
        default_dict['command_inject'] = '--sig-proxy=true'
        default_dict['docker_hostname'] = 'localhost'
        default_dict['wx_tempdir'] = False
        viz_config = ConfigParser.SafeConfigParser(default_dict)
        conf_path = os.path.join( self.attr.our_config_dir, self.attr.viz_id + ".ini" )
        if not os.path.exists( conf_path ):
            conf_path = "%s.sample" % conf_path
        viz_config.read( conf_path )
        self.attr.viz_config = viz_config

        def _boolean_option(option, default=False):
            if self.attr.viz_config.has_option("main", option):
                return self.attr.viz_config.getboolean("main", option)
            else:
                return default

        # Older style port range proxying - not sure we want to keep these around or should
        # we always assume use of Galaxy dynamic proxy? None of these need to be specified
        # if using the Galaxy dynamic proxy.
        self.attr.PASSWORD_AUTH = _boolean_option("password_auth")
        self.attr.APACHE_URLS = _boolean_option("apache_urls")
        self.attr.SSL_URLS = _boolean_option("ssl")

    def get_conf_dict(self):
        """
            Build up a configuration dictionary that is standard for ALL IEs.

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

        if self.attr.viz_config.has_option("docker", "galaxy_url"):
            conf_file['galaxy_url'] = self.attr.viz_config.get("docker", "galaxy_url")
        elif self.attr.galaxy_config.galaxy_infrastructure_url_set:
            conf_file['galaxy_url'] = self.attr.galaxy_config.galaxy_infrastructure_url.rstrip('/') + '/'
        else:
            conf_file['galaxy_url'] = request.application_url.rstrip('/') + '/'
            web_port = self.attr.galaxy_config.galaxy_infrastructure_web_port
            conf_file['galaxy_web_port'] = web_port or self.attr.galaxy_config.guess_galaxy_port()
            # Galaxy paster port is deprecated
            conf_file['galaxy_paster_port'] = conf_file['galaxy_web_port']

        return conf_file

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

    def volume(self, host_path, container_path, **kwds):
        return DockerVolume(host_path, container_path, **kwds)

    def docker_cmd(self, env_override={}, volumes=[]):
        """
            Generate and return the docker command to execute
        """
        temp_dir = self.temp_dir
        conf = self.get_conf_dict()
        conf.update(env_override)
        env_str = ' '.join(['-e "%s=%s"' % (key.upper(), item) for key, item in conf.items()])
        volume_str = ' '.join(['-v "%s"' % volume for volume in volumes])
        return '%s run %s -d %s -p %s:%s -v "%s:/import/" %s %s' % \
            (self.attr.viz_config.get("docker", "command"),
             env_str,
             self.attr.viz_config.get("docker", "command_inject"),
             self.attr.PORT, self.attr.docker_port,
             temp_dir,
             volume_str,
             self.attr.viz_config.get("docker", "image"))

    def launch(self, raw_cmd=None, env_override={}, volumes=[]):
        if raw_cmd is None:
            raw_cmd = self.docker_cmd(env_override=env_override, volumes=volumes)
        log.info("Starting docker container for IE {0} with command [{1}]".format(
            self.attr.viz_id,
            raw_cmd
        ))
        p = Popen( raw_cmd, stdout=PIPE, stderr=PIPE, close_fds=True, shell=True)
        stdout, stderr = p.communicate()
        if p.returncode != 0 or len(stderr):
            log.error( "%s\n%s" % (stdout, stderr) )
        else:
            log.debug( "Container id: %s" % stdout)
