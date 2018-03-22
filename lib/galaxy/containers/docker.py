"""
Interface to Docker
"""
from __future__ import absolute_import

import logging

from six import string_types
from six.moves import shlex_quote

from galaxy.containers import ContainerInterface
from galaxy.containers.docker_decorators import (
    docker_columns,
    docker_json
)
from galaxy.containers.docker_model import (
    DockerContainer,
    DockerVolume
)
from galaxy.exceptions import (
    ContainerCLIError,
    ContainerImageNotFound,
    ContainerNotFound
)

try:
    import docker
except ImportError:
    docker = None

log = logging.getLogger(__name__)


class DockerInterface(ContainerInterface):
    container_class = DockerContainer
    volume_class = DockerVolume
    conf_defaults = {
        'host': None,
        'force_tlsverify': False,
        'auto_remove': True,
        'image': None,
        'cpus': None,
        'memory': None,
    }
    option_map = {
        # `run` options
        'environment': {'flag': '--env', 'type': 'list_of_kvpairs'},
        'volumes': {'flag': '--volume', 'type': 'docker_volumes'},
        'name': {'flag': '--name', 'type': 'string'},
        'detach': {'flag': '--detach', 'type': 'boolean'},
        'publish_all_ports': {'flag': '--publish-all', 'type': 'boolean'},
        'publish_port_random': {'flag': '--publish', 'type': 'string'},
        'auto_remove': {'flag': '--rm', 'type': 'boolean'},
        'cpus': {'flag': '--cpus', 'type': 'string'},
        'memory': {'flag': '--memory', 'type': 'string'},
    }

    @property
    def _default_image(self):
        assert self._conf.image is not None, "No default image for this docker interface"
        return self._conf.image

    def run_in_container(self, command, image=None, **kwopts):
        # FIXME: these containers_conf overrides should be defined as class vars
        for opt in ('cpus', 'memory'):
            if self._conf[opt]:
                kwopts[opt] = self._conf[opt]
        self.set_kwopts_name(kwopts)
        return self.run(command, image=image, **kwopts)

    def image_repodigest(self, image):
        """Get the digest image string for an image.

        :type image: str
        :param image: image id or image name and optionally, tag

        :returns: digest string, having the format `<name>@<hash_alg>:<digest>`, e.g.:
                  `'bgruening/docker-jupyter-notebook@sha256:3ec0bc9abc9d511aa602ee4fff2534d80dd9b1564482de52cb5de36cce6debae'`
                  or, the original image name if the digest cannot be
                  determined (the image has not been pulled)
        """
        try:
            inspect = self.image_inspect(image)
            return inspect['RepoDigests'][0]
        except ContainerImageNotFound:
            return image

    @property
    def host(self):
        return self._conf.host


class DockerCLIInterface(DockerInterface):

    container_type = 'docker_cli'
    conf_defaults = {
        'command_template': '{executable} {global_kwopts} {subcommand} {args}',
        'executable': 'docker',
    }

    def validate_config(self):
        log.warning('The `docker_cli` interface is deprecated and will be removed in Galaxy 18.09, please use `docker`')
        super(DockerCLIInterface, self).validate_config()
        global_kwopts = []
        if self._conf.host:
            global_kwopts.append('--host')
            global_kwopts.append(shlex_quote(self._conf.host))
        if self._conf.force_tlsverify:
            global_kwopts.append('--tlsverify')
        self._docker_command = self._conf['command_template'].format(
            executable=self._conf['executable'],
            global_kwopts=' '.join(global_kwopts),
            subcommand='{subcommand}',
            args='{args}'
        )

    def _stringify_kwopt_docker_volumes(self, flag, val):
        """The docker API will take a volumes argument in many formats, try to
        deal with that for the command line
        """
        l = []
        if isinstance(val, list):
            # ['/host/vol']
            l = val
        else:
            for hostvol, guestopts in val.items():
                if isinstance(guestopts, string_types):
                    # {'/host/vol': '/container/vol'}
                    l.append('{}:{}'.format(hostvol, guestopts))
                else:
                    # {'/host/vol': {'bind': '/container/vol'}}
                    # {'/host/vol': {'bind': '/container/vol', 'mode': 'rw'}}
                    mode = guestopts.get('mode', '')
                    l.append('{vol}:{bind}{mode}'.format(
                        vol=hostvol,
                        bind=guestopts['bind'],
                        mode=':' + mode if mode else ''
                    ))
        return self._stringify_kwopt_list(flag, l)

    def _run_docker(self, subcommand, args=None, verbose=False):
        command = self._docker_command.format(subcommand=subcommand, args=args or '')
        return self._run_command(command, verbose=verbose)

    #
    # docker subcommands
    #

    @docker_columns
    def ps(self):
        return self._run_docker(subcommand='ps')

    def run(self, command, image=None, **kwopts):
        args = '{kwopts} {image} {command}'.format(
            kwopts=self._stringify_kwopts(kwopts),
            image=image or self._default_image,
            command=command if command else ''
        ).strip()
        container_id = self._run_docker(subcommand='run', args=args, verbose=True)
        return DockerContainer.from_id(self, container_id)

    @docker_json
    def inspect(self, container_id):
        try:
            return self._run_docker(subcommand='inspect', args=container_id)[0]
        except (IndexError, ContainerCLIError) as exc:
            msg = "Invalid container id: %s" % container_id
            if exc.stdout == '[]' and exc.stderr == 'Error: no such object: {container_id}'.format(container_id=container_id):
                log.warning(msg)
                return []
            else:
                raise ContainerNotFound(msg, container_id=container_id)

    @docker_json
    def image_inspect(self, image):
        try:
            return self._run_docker(subcommand='image inspect', args=image)[0]
        except (IndexError, ContainerCLIError) as exc:
            msg = "%s not pulled, cannot get digest" % image
            if exc.stdout == '[]' and exc.stderr == 'Error: no such image: {image}'.format(image=image):
                log.warning(msg, image)
                return []
            else:
                raise ContainerImageNotFound(msg, image=image)


class DockerAPIInterface(DockerInterface):
    container_type = 'docker'

    # FIXME: these only work for CLI arg maps
    option_map = {
        # `run` options
        'environment': {'type': 'list_of_kvpairs'},  # FIXME: can be list of kvpairs or dict
        'volumes': {'flag': '--volume', 'type': 'docker_volumes'},
        'name': {'flag': '--name', 'type': 'string'},
        'detach': {'flag': '--detach', 'type': 'boolean'},
        'publish_all_ports': {'flag': '--publish-all', 'type': 'boolean'},
        'publish_port_random': {'flag': '--publish', 'type': 'string'},
        'cpus': {'flag': '--cpus', 'type': 'string'},
        'memory': {'flag': '--memory', 'type': 'string'},
    }
    host_config_opts = {
        # supported options that are part of the `host_config` param to `container_create()`, use a value of `None` if
        # the expected option name is the same as the create_host_config() param
        'auto_remove': None,
        'publish_all_ports': None,
        #'publish_port_random': this is a special case handled in _create_host_config()
        'cpus': 'nano_cpus',
        'mem': 'mem_limit',
    }

    def validate_config(self):
        assert docker is not None, "Docker module could not be imported, DockerAPIInterface unavailable"
        super(DockerAPIInterface, self).validate_config()
        self.__client = None

    @property
    def _client(self):
        if not self.__client:
            self.__client = docker.APIClient(
                base_url=self._conf.host,
                tls=self._conf.force_tlsverify,
            )
        return self.__client

    def _volumes_to_native(self, volumes):
        paths = []
        binds = {}
        for v in volumes:
            path, bind = v.to_native()
            paths.append(path)
            binds.update(bind)
        return (paths, binds)

    def _create_host_config(self, **kwopts):
        """Separate docker host config options from ``kwopts``.

        After this method, ``kwopts`` is modified to have the host config options removed

        Returns the return value of `docker.APIClient.create_host_config()`
        """
        host_config_kwopts = {}
        if 'publish_port_random' in kwopts:
            host_config_kwopts['port_bindings'] = {int(kwopts.pop('publish_port_random')): None}
        if 'volumes' in kwopts:
            paths, binds = self._volumes_to_native(kwopts.pop('volumes'))
            host_config_kwopts['binds'] = binds
            kwopts['volumes'] = paths
        for k in kwopts.keys():
            if k in DockerAPIInterface.host_config_opts:
                # FIXME
                if k == 'cpus':
                    kwopts[k] = int(kwopts[k] * 1000000000)
                host_config_kwopts[DockerAPIInterface.host_config_opts.get(k) or k] = kwopts.pop(k)
        return self._client.create_host_config(**host_config_kwopts)

    #
    # docker subcommands
    #

    def ps(self):
        return self._client.containers()

    def run(self, command, image=None, **kwopts):
        # the kwopts value format is docker's format, so there's nothing to transmogrify other than key names
        try:
            ports = [int(kwopts.get('publish_port_random'))]
        except (TypeError, ValueError):
            ports = []
        try:
            container = self._client.create_container(
                image or self._default_image,
                command=command if command else None,
                ports=ports,
                host_config=self._create_host_config(**kwopts),
            )
            container_id = container.get('Id')
            self._client.start(container=container_id)
            return DockerContainer.from_id(self, container_id)
        except Exception:
            raise

    def inspect(self, container_id):
        try:
            return self._client.inspect_container(container_id)
        except docker.errors.NotFound:
            raise ContainerNotFound("Invalid container id: %s" % container_id, container_id=container_id)

    def image_inspect(self, image):
        try:
            return self._client.inspect_image(image)
        except docker.errors.NotFound:
            raise ContainerImageNotFound("%s not pulled, cannot get digest" % image, image=image)
