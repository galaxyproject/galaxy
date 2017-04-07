import ConfigParser

import os
import json
import yaml
import stat
import random
import tempfile
import uuid
from subprocess import Popen, PIPE

from galaxy.util import string_as_bool_or_none
from galaxy.util.bunch import Bunch
from galaxy.container import docker_swarm
from galaxy import web, model
from galaxy.managers import api_keys
from galaxy.tools.deps.docker_util import DockerVolume

import logging
log = logging.getLogger(__name__)


CONTAINER_NAME_PREFIX = 'galaxy_gie_'


class InteractiveEnvironmentRequest(object):

    def __init__(self, trans, plugin):
        self.trans = trans
        self.log = log

        self.attr = Bunch()
        self.attr.viz_id = plugin.name
        self.attr.history_id = trans.security.encode_id( trans.history.id )
        self.attr.galaxy_config = trans.app.config
        self.attr.galaxy_root_dir = os.path.abspath(self.attr.galaxy_config.root)
        self.attr.root = web.url_for("/")
        self.attr.app_root = self.attr.root + "plugins/interactive_environments/" + self.attr.viz_id + "/static/"
        self.attr.import_volume = True

        plugin_path = os.path.abspath( plugin.path )

        # Store our template and configuration path
        self.attr.our_config_dir = os.path.join(plugin_path, "config")
        self.attr.our_template_dir = os.path.join(plugin_path, "templates")
        self.attr.HOST = trans.request.host.rsplit(':', 1)[0]

        self.load_deploy_config()
        self.load_allowed_images()
        self.attr.docker_hostname = self.attr.viz_config.get("docker", "docker_hostname")
        self.attr.docker_connect_port = self.attr.viz_config.get("docker", "docker_connect_port") or None

        if string_as_bool_or_none(self.attr.viz_config.get("docker", "swarm_mode")) is not None:
            self.attr.swarm_mode = string_as_bool_or_none(self.attr.viz_config.get("docker", "swarm_mode"))
        else:
            self.attr.swarm_mode = trans.app.config.gie_swarm_mode

        # Generate per-request passwords the IE plugin can use to configure
        # the destination container.
        self.notebook_pw_salt = self.generate_password(length=12)
        self.notebook_pw = self.generate_password(length=24)

        ie_parent_temp_dir = self.attr.viz_config.get("docker", "docker_galaxy_temp_dir") or None
        self.temp_dir = os.path.abspath( tempfile.mkdtemp( dir=ie_parent_temp_dir ) )

        if self.attr.viz_config.getboolean("docker", "wx_tempdir"):
            # Ensure permissions are set
            try:
                os.chmod( self.temp_dir, os.stat(self.temp_dir).st_mode | stat.S_IXOTH )
            except Exception:
                log.error( "Could not change permissions of tmpdir %s" % self.temp_dir )
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

        assert not self.attr.swarm_mode or (self.attr.swarm_mode and
                                            self.attr.docker_connect_port is not None), \
            "Error: Docker swarm mode enabled but docker_connect_port is not set"

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
            self.allowed_images = [x['image'] for x in yaml.load(handle)]

            if len(self.allowed_images) == 0:
                raise Exception("No allowed images specified for " + self.attr.viz_id)

            self.default_image = self.allowed_images[0]

    def load_deploy_config(self, default_dict={}):
        # For backwards compat, any new variables added to the base .ini file
        # will need to be recorded here. The ConfigParser doesn't provide a
        # .get() that will ignore missing sections, so we must make use of
        # their defaults dictionary instead.
        default_dict = {
            'command': 'docker {docker_args}',
            'command_inject': '-e DEBUG=false -e DEFAULT_CONTAINER_RUNTIME=120',
            'docker_hostname': 'localhost',
            'wx_tempdir': 'False',
            'docker_galaxy_temp_dir': None,
            'docker_connect_port': None,
            'swarm_mode': None,
        }
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

    def volume(self, host_path, container_path, **kwds):
        return DockerVolume(host_path, container_path, **kwds)

    def docker_cmd(self, image, env_override=None, volumes=None):
        """
            Generate and return the docker command to execute
        """
        if env_override is None:
            env_override = {}
        if volumes is None:
            volumes = []
        temp_dir = self.temp_dir
        conf = self.get_conf_dict()
        conf.update(env_override)
        env_str = ' '.join(['-e "%s=%s"' % (key.upper(), item) for key, item in conf.items()])
        volume_str = ' '.join(['-v "%s"' % volume for volume in volumes])
        import_volume_str = '-v "{temp_dir}:/import/"'.format(temp_dir=temp_dir) if self.attr.import_volume else ''
        name = None
        # This is the basic docker command such as "sudo -u docker docker {docker_args}"
        # or just "docker {docker_args}"
        command = self.attr.viz_config.get("docker", "command")
        # Then we format in the entire docker command in place of
        # {docker_args}, so as to let the admin not worry about which args are
        # getting passed
        command_inject = self.attr.viz_config.get("docker", "command_inject")
        # --name should really not be set, but we'll try to honor it anyway
        if '--name' not in command_inject:
            name = CONTAINER_NAME_PREFIX + uuid.uuid4().hex
        if not self.attr.swarm_mode:
            command = command.format(docker_args='run {command_inject} {name} {environment} -d -P {import_volume_str} {volume_str} {image}')
            # --sig-proxy is not valid in the swarm mode context
            if '--sig-proxy=' not in command_inject:
                command_inject = '--sig-proxy=true ' + command_inject
        else:
            command = command.format(docker_args='service create --replicas 1 --restart-condition none {command_inject} {name} -p {docker_connect_port} {environment} {image}')

        # Once that's available, we format again with all of our arguments
        command = command.format(
            command_inject=command_inject,
            name='--name=%s' % name if name is not None else '',
            environment=env_str,
            import_volume_str=import_volume_str,
            volume_str=volume_str,
            image=image,
            docker_connect_port=self.attr.docker_connect_port,
        )
        return command

    def get_digest_image(self, image):
        """Get the digest image string for an image.

        :type image: str
        :param image: image name and optionally, tag

        :returns: digest string, having the format `<name>@<hash_alg>:<digest>`, e.g.:
                  `'bgruening/docker-jupyter-notebook@sha256:3ec0bc9abc9d511aa602ee4fff2534d80dd9b1564482de52cb5de36cce6debae'`
        """
        command = self.attr.viz_config.get("docker", "command")
        command = command.format(docker_args="image inspect --format '{{{{(index .RepoDigests 0)}}}}' {image}".format(image=image))
        p = Popen(command, stdout=PIPE, stderr=PIPE, close_fds=True, shell=True)
        stdout, stderr = p.communicate()
        digest = None
        if p.returncode == 0:
            digest = stdout.strip()
        elif p.returncode == 1 and stderr.strip() == 'Error: No such image: {image}'.format(image=image):
            log.warning("%s not pulled, cannot get digest", image)
        else:
            log.error( "%s\n%s" % (stdout, stderr) )
        return digest or image

    def _idsToVolumes(self, ids):
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
            volumes.append(self.volume(dataset.get_file_name(), '/import/[{0}] {1}.{2}'.format(dataset.id, dataset.name, dataset.ext)))
        return volumes

    def launch(self, image=None, additional_ids=None, raw_cmd=None, env_override={}, volumes=[]):
        """Launch a docker image.

        :type image: str
        :param image: Optional image name. If not provided, self.default_image
                      is used, which is the first image listed in the
                      allowed_images.yml{,.sample} file.

        :type additional_ids: str
        :param additional_ids: comma separated list of encoded HDA IDs. These
                               are transformed into Volumes and added to that
                               argument

        :type raw_cmd: str
        :param raw_cmd: raw docker command. Usually generated with self.docker_cmd()

        :type env_override: dict
        :param env_override: dictionary of environment variables to add.

        :type volumes: list of galaxy.tools.deps.docker_util.DockerVolume
        :param volumes: dictionary of docker volume mounts

        """
        if image is None:
            image = self.default_image

        if image not in self.allowed_images:
            # Now that we're allowing users to specify images, we need to ensure that they aren't
            # requesting images we have not specifically allowed.
            raise Exception("Attempting to launch disallowed image! %s not in list of allowed images [%s]"
                            % (image, ', '.join(self.allowed_images)))

        # The digest image is necessary if using swarm mode and the image's
        # registry (e.g. docker hub, quay.io) is down. See:
        # https://github.com/docker/docker/issues/31427
        image = self.get_digest_image(image)

        if additional_ids is not None:
            volumes += self._idsToVolumes(additional_ids)

        if raw_cmd is None:
            raw_cmd = self.docker_cmd(image, env_override=env_override, volumes=volumes)

        log.info("Starting docker container for IE {0} with command [{1}]".format(
            self.attr.viz_id,
            raw_cmd
        ))
        p = Popen( raw_cmd, stdout=PIPE, stderr=PIPE, close_fds=True, shell=True)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            log.error( "%s\n%s" % (stdout, stderr) )
            return None
        else:
            container_id = stdout.strip()
            log.debug( "Container id: %s" % container_id)
            inspect_data = self.inspect_container(container_id)
            port_mappings = self.get_container_port_mapping(inspect_data)
            self.attr.docker_hostname = self.get_container_host(inspect_data)
            log.debug( "Container host: %s", self.attr.docker_hostname )
            host_port = None

            if self.attr.swarm_mode:
                docker_swarm.main(argv=['-c', self.trans.app.config.config_file], fork=True)

            if len(port_mappings) > 1:
                if self.attr.docker_connect_port is not None:
                    for _service, _host_ip, _host_port in port_mappings:
                        if _service == self.attr.docker_connect_port:
                            host_port = _host_port
                else:
                    log.warning("Don't know how to handle proxies to containers with multiple exposed ports. Arbitrarily choosing first. Please set 'docker_connect_port' in your config file to be more specific.")
            elif len(port_mappings) == 0:
                log.warning("No exposed ports to map! Images MUST EXPOSE")
                return None

            if host_port is None:
                # Fetch the first port_mapping
                (service, host_ip, host_port) = port_mappings[0]

            # Now we configure our proxy_requst object and we manually specify
            # the port to map to and ensure the proxy is available.
            self.attr.proxy_request = self.trans.app.proxy_manager.setup_proxy(
                self.trans,
                host=self.attr.docker_hostname,
                port=host_port,
                proxy_prefix=self.attr.proxy_prefix,
                route_name=self.attr.viz_id,
                container_ids=[container_id] if not self.attr.swarm_mode else [],
                service_ids=[container_id] if self.attr.swarm_mode else [],
                docker_command=self.attr.viz_config.get("docker", "command"),
            )
            # These variables then become available for use in templating URLs
            self.attr.proxy_url = self.attr.proxy_request[ 'proxy_url' ]
            # Commented out because it needs to be documented and visible that
            # this variable was moved here. Usually would remove commented
            # code, but again, needs to be clear where this went. Remove at a
            # later time.
            #
            # PORT is no longer exposed internally. All requests are forced to
            # go through the proxy we ship.
            # self.attr.PORT = self.attr.proxy_request[ 'proxied_port' ]

    def inspect_container(self, container_id):
        """Runs docker inspect on a container and returns json response as python dictionary inspect_data.

        :type container_id: str
        :param container_id: a docker container ID

        :returns: inspect_data, a dict of docker inspect output
        """
        command = self.attr.viz_config.get("docker", "command")
        if not self.attr.swarm_mode:
            command = command.format(docker_args="inspect %s" % container_id)
        else:
            command = command.format(docker_args="service inspect %s" % container_id)
        log.info("Inspecting docker container {0} with command [{1}]".format(
            container_id,
            command
        ))

        p = Popen(command, stdout=PIPE, stderr=PIPE, close_fds=True, shell=True)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            log.error( "%s\n%s" % (stdout, stderr) )
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
        elif self.attr.docker_hostname == "localhost":
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
        # non-swarm:
        # [{
        #     "NetworkSettings" : {
        #         "Ports" : {
        #             "3306/tcp" : [
        #                 {
        #                     "HostIp" : "127.0.0.1",
        #                     "HostPort" : "3306"
        #                 }
        #             ]
        # swarm:
        # [{
        #     "Endpoint": {
        #         "Ports": [
        #             {
        #                 "Protocol": "tcp",
        #                 "TargetPort": 8888,
        #                 "PublishedPort": 30000,
        #                 "PublishMode": "ingress"
        #             }
        #         ]
        mappings = []
        if not self.attr.swarm_mode:
            port_mappings = inspect_data[0]['NetworkSettings']['Ports']
            for port_name in port_mappings:
                for binding in port_mappings[port_name]:
                    mappings.append((
                        port_name.replace('/tcp', '').replace('/udp', ''),
                        binding['HostIp'],
                        binding['HostPort']
                    ))
        else:
            port_mappings = inspect_data[0]['Endpoint']['Ports']
            for binding in port_mappings:
                mappings.append((
                    binding['TargetPort'],
                    '127.0.0.1',                # use the routing mesh
                    binding['PublishedPort']
                ))
        return mappings
