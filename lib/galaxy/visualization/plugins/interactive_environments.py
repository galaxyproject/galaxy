import json
import logging
import os
import random
import re
import shlex
import stat
import string
import tempfile
import uuid
from itertools import product
from subprocess import PIPE, Popen
from sys import platform as _platform

import yaml
from six.moves import configparser, shlex_quote

from galaxy import model, web
from galaxy.containers import ContainerPort
from galaxy.containers.docker_model import DockerVolume
from galaxy.managers import api_keys
from galaxy.util import string_as_bool_or_none
from galaxy.util.bunch import Bunch


IS_OS_X = _platform == "darwin"
CONTAINER_NAME_PREFIX = 'gie_'
ENV_OVERRIDE_CAPITALIZE = frozenset([
    'notebook_username',
    'notebook_password',
    'dataset_hid',
    'dataset_filename',
    'additional_ids',
])

log = logging.getLogger(__name__)


class InteractiveEnvironmentRequest(object):

    def __init__(self, trans, plugin):
        self.trans = trans
        self.log = log

        self.attr = Bunch()
        self.attr.viz_id = plugin.name
        self.attr.history_id = trans.security.encode_id(trans.history.id)
        self.attr.galaxy_config = trans.app.config
        self.attr.redact_username_in_logs = trans.app.config.redact_username_in_logs
        self.attr.galaxy_root_dir = os.path.abspath(self.attr.galaxy_config.root)
        self.attr.root = web.url_for("/")
        self.attr.app_root = self.attr.root + "static/plugins/interactive_environments/" + self.attr.viz_id + "/static/"
        self.attr.import_volume = True

        plugin_path = os.path.abspath(plugin.path)

        # Store our template and configuration path
        self.attr.our_config_dir = os.path.join(plugin_path, "config")
        self.attr.our_template_dir = os.path.join(plugin_path, "templates")
        self.attr.HOST = trans.request.host.rsplit(':', 1)[0]

        self.load_deploy_config()
        self.load_allowed_images()
        self.load_container_interface()

        self.attr.docker_hostname = self.attr.viz_config.get("docker", "docker_hostname")
        raw_docker_connect_port = self.attr.viz_config.get("docker", "docker_connect_port")
        self.attr.docker_connect_port = int(raw_docker_connect_port) if raw_docker_connect_port else None

        # Generate per-request passwords the IE plugin can use to configure
        # the destination container.
        self.notebook_pw_salt = self.generate_password(length=12)
        self.notebook_pw = self.generate_password(length=24)

        ie_parent_temp_dir = self.attr.viz_config.get("docker", "docker_galaxy_temp_dir") or None
        self.temp_dir = os.path.abspath(tempfile.mkdtemp(dir=ie_parent_temp_dir))

        if self.attr.viz_config.getboolean("docker", "wx_tempdir"):
            # Ensure permissions are set
            try:
                os.chmod(self.temp_dir, os.stat(self.temp_dir).st_mode | stat.S_IXOTH)
            except Exception:
                log.error("Could not change permissions of tmpdir %s" % self.temp_dir)
                # continue anyway

        # This duplicates the logic in the proxy manager
        if self.attr.galaxy_config.dynamic_proxy_external_proxy:
            self.attr.proxy_prefix = '/'.join(
                (
                    '',
                    self.attr.galaxy_config.cookie_path.strip('/'),
                    self.attr.galaxy_config.dynamic_proxy_prefix.strip('/'),
                    self.attr.viz_id,
                )
            )
        else:
            self.attr.proxy_prefix = ''
        # If cookie_path is unset (thus '/'), the proxy prefix ends up with
        # multiple leading '/' characters, which will cause the client to
        # request resources from http://dynamic_proxy_prefix
        if self.attr.proxy_prefix.startswith('/'):
            self.attr.proxy_prefix = '/' + self.attr.proxy_prefix.lstrip('/')

        assert not self.attr.container_interface \
            or not self.attr.container_interface.publish_port_list_required \
            or (self.attr.container_interface.publish_port_list_required and self.attr.docker_connect_port is not None), \
            "Error: Container interface requires publish port list but docker_connect_port is not set"

    def load_allowed_images(self):
        if os.path.exists(os.path.join(self.attr.our_config_dir, 'allowed_images.yml')):
            fn = os.path.join(self.attr.our_config_dir, 'allowed_images.yml')
        elif os.path.exists(os.path.join(self.attr.our_config_dir, 'allowed_images.yml.sample')):
            fn = os.path.join(self.attr.our_config_dir, 'allowed_images.yml.sample')
        else:
            # If we don't have an allowed images, then we fall back to image
            # name specified in the .ini file
            try:
                self.allowed_images = [self.attr.viz_config.get('docker', 'image')]
                self.default_image = self.attr.viz_config.get('docker', 'image')
                return
            except AttributeError:
                raise Exception("[{0}] Could not find allowed_images.yml, or image tag in {0}.ini file for ".format(self.attr.viz_id))

        with open(fn, 'r') as handle:
            self.allowed_images = [x['image'] for x in yaml.safe_load(handle)]

            if len(self.allowed_images) == 0:
                raise Exception("No allowed images specified for " + self.attr.viz_id)

            self.default_image = self.allowed_images[0]

    def load_deploy_config(self, default_dict={}):
        # For backwards compat, any new variables added to the base .ini file
        # will need to be recorded here. The configparser doesn't provide a
        # .get() that will ignore missing sections, so we must make use of
        # their defaults dictionary instead.
        default_dict = {
            'container_interface': None,
            'command': 'docker',
            'command_inject': '-e DEBUG=false -e DEFAULT_CONTAINER_RUNTIME=120',
            'docker_hostname': 'localhost',
            'wx_tempdir': 'False',
            'docker_galaxy_temp_dir': None,
            'docker_connect_port': None,
        }
        viz_config = configparser.SafeConfigParser(default_dict)
        conf_path = os.path.join(self.attr.our_config_dir, self.attr.viz_id + ".ini")
        if not os.path.exists(conf_path):
            conf_path = "%s.sample" % conf_path
        viz_config.read(conf_path)
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
        self.attr.SSL_URLS = _boolean_option("ssl")

    def load_container_interface(self):
        self.attr.container_interface = None
        key = None
        if string_as_bool_or_none(self.attr.viz_config.get("main", "container_interface")) is not None:
            key = self.attr.viz_config.get("main", "container_interface")
        elif self.attr.galaxy_config.enable_beta_containers_interface:
            # TODO: don't hardcode this, and allow for mapping
            key = '_default_'
        if key:
            try:
                self.attr.container_interface = self.trans.app.containers[key]
            except KeyError:
                log.error("Unable to load '%s' container interface: invalid key", key)

    def get_conf_dict(self):
        """
            Build up a configuration dictionary that is standard for ALL IEs.

            TODO: replace hashed password with plaintext.
        """
        trans = self.trans
        request = trans.request
        api_key = api_keys.ApiKeyManager(trans.app).get_or_create_api_key(trans.user)
        conf_file = {
            'history_id': self.attr.history_id,
            'api_key': api_key,
            'remote_host': request.remote_addr,
            # DOCKER_PORT is NO LONGER AVAILABLE. All IEs must update.
            'cors_origin': request.host_url,
            'user_email': self.trans.user.email,
            'proxy_prefix': self.attr.proxy_prefix,
        }

        web_port = self.attr.galaxy_config.galaxy_infrastructure_web_port
        conf_file['galaxy_web_port'] = web_port or self.attr.galaxy_config.guess_galaxy_port()

        if self.attr.viz_config.has_option("docker", "galaxy_url"):
            conf_file['galaxy_url'] = self.attr.viz_config.get("docker", "galaxy_url")
        elif self.attr.galaxy_config.galaxy_infrastructure_url_set:
            conf_file['galaxy_url'] = self.attr.galaxy_config.galaxy_infrastructure_url.rstrip('/') + '/'
        else:
            conf_file['galaxy_url'] = request.application_url.rstrip('/') + '/'
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
        """Process a URL template

        There are several variables accessible to the user:

            - ${PROXY_URL} will be replaced with the dynamically create proxy's url
            - ${PROXY_PREFIX} will be replaced with the prefix that may occur
        """
        # Next several lines for older style replacements (not used with Galaxy dynamic
        # proxy)
        if self.attr.SSL_URLS:
            protocol = 'https'
        else:
            protocol = 'http'

        url_template = url_template.replace('${PROTO}', protocol) \
            .replace('${HOST}', self.attr.HOST)

        # Only the following replacements are used with Galaxy dynamic proxy
        # URLs
        url = url_template.replace('${PROXY_URL}', str(self.attr.proxy_url)) \
            .replace('${PROXY_PREFIX}', str(self.attr.proxy_prefix.replace('/', '%2F')))
        return url

    def volume(self, container_path, host_path, **kwds):
        if self.attr.container_interface is None:
            return DockerVolume(container_path, host_path, **kwds)
        else:
            return self.attr.container_interface.volume_class(
                container_path,
                host_path=host_path,
                mode=kwds.get('mode', 'ro'))

    def _get_env_for_run(self, env_override=None):
        if env_override is None:
            env_override = {}
        conf = self.get_conf_dict()
        conf = dict([(key.upper(), item) for key, item in conf.items()])
        for key, item in env_override.items():
            if key in ENV_OVERRIDE_CAPITALIZE:
                key = key.upper()
            conf[key] = item
        return conf

    def _get_import_volume_for_run(self):
        if self.use_volumes and self.attr.import_volume:
            return '{temp_dir}:/import/'.format(temp_dir=self.temp_dir)
        return ''

    def _get_name_for_run(self):
        return CONTAINER_NAME_PREFIX + uuid.uuid4().hex

    def base_docker_cmd(self, subcmd=None):
        # This is the basic docker command such as "sudo -u docker docker" or just "docker"
        # Previously, {docker_args} was required to be in the string, this is no longer the case
        base = shlex.split(self.attr.viz_config.get("docker", "command").format(docker_args='').strip())
        if subcmd:
            base.append(subcmd)
        return base

    def docker_cmd(self, image, env_override=None, volumes=None):
        """
            Generate and return the docker command to execute
        """
        def _flag_opts(flag, opts):
            return [arg for pair in product((flag,), opts) for arg in pair]

        def _check_uid_and_gid(cmd_inject):
            """
            Check and replace shell uid and gid using os
            :param cmd_inject:
            """
            # --user="$(id -u):$(id -g)"
            # https://docs.docker.com/engine/reference/run/#user
            # -e USER_UID=$(id -u) -e USER_GID=$(id -g)
            uid_gid_subs = {"$(id -u)": "{}".format(os.geteuid()), "$(id -g)": "{}".format(os.getgid())}
            subs = sorted(uid_gid_subs)
            regex = re.compile('|'.join(map(re.escape, subs)))
            return regex.sub(lambda match: uid_gid_subs[match.group(0)], cmd_inject)

        command_inject = self.attr.viz_config.get("docker", "command_inject")
        command_inject = _check_uid_and_gid(command_inject)

        # --name should really not be set, but we'll try to honor it anyway
        name = ['--name=%s' % self._get_name_for_run()] if '--name' not in command_inject else []
        env = self._get_env_for_run(env_override)
        import_volume_def = self._get_import_volume_for_run()
        if volumes is None:
            volumes = []
        if import_volume_def:
            volumes.insert(0, import_volume_def)

        return (
            self.base_docker_cmd('run') +
            shlex.split(command_inject) +
            name +
            _flag_opts('-e', ['='.join(map(str, t)) for t in env.items()]) +
            ['-d', '-P'] +
            _flag_opts('-v', map(str, volumes)) +
            [image]
        )

    @property
    def use_volumes(self):
        if self.attr.container_interface and not self.attr.container_interface.supports_volumes:
            return False
        elif self.attr.viz_config.has_option("docker", "use_volumes"):
            return string_as_bool_or_none(self.attr.viz_config.get("docker", "use_volumes"))
        else:
            return True

    def _get_command_inject_env(self):
        """For the containers interface, parse any -e/--env flags from `command_inject`.
        """
        # using a list ensures that later vars override earlier ones with the
        # same name, which is how `docker run` works on the command line
        envsets = []
        command_inject = self.attr.viz_config.get("docker", "command_inject").strip().split()
        for i, item in enumerate(command_inject):
            if item.startswith('-e=') or item.startswith('--env='):
                envsets.append(item.split('=', 1)[1])
            elif item == ('-e') or item == ('--env'):
                envsets.append(command_inject[i + 1])
            elif item.startswith('-e'):
                envsets.append(item[2:])
            elif item.startswith('--env'):
                envsets.append(item[5:])
        return dict(map(lambda s: string.split(s, '=', 1), envsets))

    def container_run_args(self, image, env_override=None, volumes=None):
        if volumes is None:
            volumes = []
        import_volume_def = self._get_import_volume_for_run()
        if import_volume_def:
            volumes.append(import_volume_def)
        env = self._get_command_inject_env()
        env.update(self._get_env_for_run(env_override))
        args = {
            'image': image,
            'environment': env,
            'volumes': volumes,
            'name': self._get_name_for_run(),
            'detach': True,
            'publish_all_ports': True,
        }
        if self.attr.docker_connect_port:
            # TODO: we can inspect the image for this, and if it's not pulled
            # yet we can query the registry for it
            args['publish_port_random'] = self.attr.docker_connect_port
        return args

    def _ids_to_volumes(self, ids):
        if len(ids.strip()) == 0:
            return []

        # They come as a comma separated list
        ids = ids.split(',')

        # Next we need to turn these into volumes
        volumes = []
        for id in ids:
            decoded_id = self.trans.security.decode_id(id)
            dataset = self.trans.sa_session.query(model.HistoryDatasetAssociation).get(decoded_id)
            # TODO: do we need to check if the user has access?
            volumes.append(self.volume('/import/[{0}] {1}.{2}'.format(dataset.id, dataset.name, dataset.ext), dataset.get_file_name()))
        return volumes

    def _find_port_mapping(self, port_mappings):
        port_mapping = None
        if len(port_mappings) > 1:
            if self.attr.docker_connect_port is not None:
                for _port_mapping in port_mappings:
                    if _port_mapping[0] == self.attr.docker_connect_port:
                        port_mapping = _port_mapping
                        break
            else:
                log.warning("Don't know how to handle proxies to containers with multiple exposed ports. Arbitrarily choosing first. Please set 'docker_connect_port' in your config file to be more specific.")
        elif len(port_mappings) == 0:
            log.warning("No exposed ports to map! Images MUST EXPOSE")
            return None
        if port_mapping is None:
            # Fetch the first port_mapping
            port_mapping = port_mappings[0]
        return port_mapping

    def _launch_legacy(self, image, env_override, volumes):
        """Legacy launch method for use when the container interface is not enabled
        """
        raw_cmd = self.docker_cmd(image, env_override=env_override, volumes=volumes)
        redacted_command = raw_cmd
        if self.attr.redact_username_in_logs:
            def make_safe(param):
                if 'USER_EMAIL' in param:
                    return re.sub('USER_EMAIL=[^ ]*', 'USER_EMAIL=*********', param)
                else:
                    return param

            redacted_command = [make_safe(x) for x in raw_cmd]

        log.info("Starting docker container for IE {0} with command [{1}]".format(
            self.attr.viz_id,
            ' '.join([shlex_quote(x) for x in redacted_command])
        ))
        p = Popen(raw_cmd, stdout=PIPE, stderr=PIPE, close_fds=True)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            log.error("Container Launch error\n\n%s\n%s" % (stdout, stderr))
            return None
        else:
            container_id = stdout.strip()
            log.debug("Container id: %s" % container_id)
            inspect_data = self.inspect_container(container_id)
            port_mappings = self.get_container_port_mapping(inspect_data)
            self.attr.docker_hostname = self.get_container_host(inspect_data)
            host_port = self._find_port_mapping(port_mappings)[-1]
            log.debug("Container host/port: %s:%s", self.attr.docker_hostname, host_port)

            # Now we configure our proxy_request object and we manually specify
            # the port to map to and ensure the proxy is available.
            self.attr.proxy_request = self.trans.app.proxy_manager.setup_proxy(
                self.trans,
                host=self.attr.docker_hostname,
                port=host_port,
                proxy_prefix=self.attr.proxy_prefix,
                route_name=self.attr.viz_id,
                container_ids=[container_id],
            )
            # These variables then become available for use in templating URLs
            self.attr.proxy_url = self.attr.proxy_request['proxy_url']
            # Commented out because it needs to be documented and visible that
            # this variable was moved here. Usually would remove commented
            # code, but again, needs to be clear where this went. Remove at a
            # later time.
            #
            # PORT is no longer exposed internally. All requests are forced to
            # go through the proxy we ship.
            # self.attr.PORT = self.attr.proxy_request[ 'proxied_port' ]

    def _launch_container_interface(self, image, env_override, volumes):
        """Launch method for use when the container interface is enabled
        """
        run_args = self.container_run_args(image, env_override, volumes)
        container = self.attr.container_interface.run_in_container(None, **run_args)
        container_port = container.map_port(self.attr.docker_connect_port)
        if not container_port:
            log.warning("Container %s (%s) created but no port information available, readiness check will determine "
                        "ports", container.name, container.id)
            container_port = ContainerPort(self.attr.docker_connect_port, None, None, None)
            # a negated docker_connect_port will be stored in the proxy to indicate that the readiness check should
            # attempt to determine the port
        log.debug("Container %s (%s) port %s accessible at: %s:%s", container.name, container.id, container_port.port,
                  container_port.hostaddr, container_port.hostport)
        self.attr.proxy_request = self.trans.app.proxy_manager.setup_proxy(
            self.trans,
            host=container_port.hostaddr,
            port=container_port.hostport or -container_port.port,
            proxy_prefix=self.attr.proxy_prefix,
            route_name=self.attr.viz_id,
            container_ids=[container.id],
            container_interface=self.attr.container_interface.key
        )
        self.attr.proxy_url = self.attr.proxy_request['proxy_url']

    def launch(self, image=None, additional_ids=None, env_override=None, volumes=None):
        """Launch a docker image.

        :type image: str
        :param image: Optional image name. If not provided, self.default_image
                      is used, which is the first image listed in the
                      allowed_images.yml{,.sample} file.

        :type additional_ids: str
        :param additional_ids: comma separated list of encoded HDA IDs. These
                               are transformed into Volumes and added to that
                               argument

        :type env_override: dict
        :param env_override: dictionary of environment variables to add.

        :type volumes: list of :class:`galaxy.containers.docker_model.DockerVolume`s
        :param volumes: dictionary of docker volume mounts

        """
        if volumes is None:
            volumes = []
        if image is None:
            image = self.default_image

        if image not in self.allowed_images:
            # Now that we're allowing users to specify images, we need to ensure that they aren't
            # requesting images we have not specifically allowed.
            raise Exception("Attempting to launch disallowed image! %s not in list of allowed images [%s]"
                            % (image, ', '.join(self.allowed_images)))

        if additional_ids is not None:
            volumes += self._ids_to_volumes(additional_ids)

        if self.attr.container_interface is None:
            self._launch_legacy(image, env_override, volumes)
        else:
            self._launch_container_interface(image, env_override, volumes)

    def inspect_container(self, container_id):
        """Runs docker inspect on a container and returns json response as python dictionary inspect_data.

        :type container_id: str
        :param container_id: a docker container ID

        :returns: inspect_data, a dict of docker inspect output
        """
        raw_cmd = self.base_docker_cmd('inspect') + [container_id]
        log.info("Inspecting docker container {0} with command [{1}]".format(
            container_id,
            ' '.join([shlex_quote(x) for x in raw_cmd])
        ))

        p = Popen(raw_cmd, stdout=PIPE, stderr=PIPE, close_fds=True)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            log.error("Container Launch error\n\n%s\n%s" % (stdout, stderr))
            return None

        inspect_data = json.loads(stdout)
        return inspect_data

    def get_container_host(self, inspect_data):
        """
        Determine the ip address on the container. If inspect_data contains
        Node.IP return that (e.g. running in Docker Swarm). If the hostname
        is "localhost", look for NetworkSettings.Gateway. Otherwise, just
        return the configured docker_hostname.

        :type inspect_data: dict
        :param inspect_data: output of docker inspect
        :returns: IP address or hostname of the node the conatainer is
                  running on.
        """
        inspect_data = inspect_data[0]
        if 'Node' in inspect_data:
            return inspect_data['Node']['IP']
        elif self.attr.docker_hostname == "localhost" and not IS_OS_X:
            # If this is on Docker of Mac OS X that Gateway will be an
            # IP address only available in the Docker host VM - so we
            # stick with localhost.
            return inspect_data['NetworkSettings']['Gateway']
        else:
            return self.attr.docker_hostname

    def get_container_port_mapping(self, inspect_data):
        """
        :type inspect_data: dict
        :param inspect_data: output of docker inspect
        :returns: a list of triples containing (internal_port, external_ip,
                  external_port), of which the ports are probably the only
                  useful information.

        Someday code that calls this should be refactored whenever we get
        containers with multiple ports working.
        """
        # [{
        #     "NetworkSettings" : {
        #         "Ports" : {
        #             "3306/tcp" : [
        #                 {
        #                     "HostIp" : "127.0.0.1",
        #                     "HostPort" : "3306"
        #                 }
        #             ]
        mappings = []
        port_mappings = inspect_data[0]['NetworkSettings']['Ports']
        for port_name in port_mappings:
            for binding in port_mappings[port_name]:
                mappings.append((
                    int(port_name.replace('/tcp', '').replace('/udp', '')),
                    binding['HostIp'],
                    int(binding['HostPort'])
                ))
        return mappings
