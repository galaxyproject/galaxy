"""
Interface to Docker
"""
from __future__ import absolute_import

import logging
import os
from functools import partial
from time import sleep

try:
    import docker
except ImportError:
    docker = None

import requests.exceptions
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
from galaxy.util.json import safe_dumps_formatted

log = logging.getLogger(__name__)


class DockerInterface(ContainerInterface):
    container_class = DockerContainer
    volume_class = DockerVolume
    conf_defaults = {
        'host': None,
        'tls': False,
        'force_tlsverify': False,
        'auto_remove': True,
        'image': None,
        'cpus': None,
        'memory': None,
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

    def _filter_by_id_or_name(self, id, name):
        if id:
            return '--filter id={}'.format(id)
        elif name:
            return '--filter name={}'.format(name)
        return None

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
    def ps(self, id=None, name=None):
        return self._run_docker(subcommand='ps', args=self._filter_by_id_or_name(id, name))

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


class DockerAPIClient(object):
    """Wraps a ``docker.APIClient`` to catch exceptions.
    """

    exception_retry_time = 5
    client_handler_map = {}

    @staticmethod
    def _qualname(f):
        return getattr(f, '__qualname__', f.im_class.__name__ + '.' + f.__name__)

    @staticmethod
    def default_client_handler(f, *args, **kwargs):
        exc = None
        tries = 0
        success_test = kwargs.pop('success_test', lambda: False)
        max_tries = kwargs.pop('max_tries', -1)
        while True:
            retry_time = DockerAPIClient.exception_retry_time
            try:
                r = f(*args, **kwargs)
                if tries:
                    log.info('%s() succeeded after %s tries', DockerAPIClient._qualname(f), tries)
                return r
            except (requests.exceptions.ConnectionError, docker.errors.APIError) as exc:
                pass
            except requests.exceptions.ReadTimeout as exc:
                retry_time = 0
            log.warning("Caught exception on %s(): %s: %s", DockerAPIClient._qualname(f), exc.__class__.__name__, exc)
            r = success_test()
            if r:
                log.warning("The request appears to have succeeded, will not retry. Response is: %s", str(r))
                return r
            elif max_tries > 0 and tries > max_tries:
                log.error("Maximum number of attempts (%s) exceeded", max_tries)
            else:
                tries += 1
                of = " of %s" % max_tries if max_tries > 0 else ""
                log.error("Retrying in %s seconds (attempt: %s%s)", retry_time, tries, of)
                sleep(retry_time)

    def __init__(self, *args, **kwargs):
        self.__client = docker.APIClient(*args, **kwargs)

    def __getattr__(self, attr):
        cattr = getattr(self.__client, attr)
        if callable(cattr):
            def wrapped(*args, **kwargs):
                handler_name = DockerAPIClient.client_handler_map.get(attr, 'default_client_handler')
                handler = getattr(DockerAPIClient, handler_name)
                return handler(cattr, *args, **kwargs)
            return wrapped
        else:
            return cattr


class DockerAPIInterface(DockerInterface):

    container_type = 'docker'

    # 'publish_port_random' and 'volumes' are special cases handled in _create_host_config()
    host_config_option_map = {
        'auto_remove': {},
        'publish_all_ports': {},
        'cpus': {'param': 'nano_cpus', 'map': lambda x: int(x * 1000000000)},
        'memory': {'param': 'mem_limit'},
        'binds': {},
        'port_bindings': {},
    }

    def validate_config(self):
        assert docker is not None, "Docker module could not be imported, DockerAPIInterface unavailable"
        super(DockerAPIInterface, self).validate_config()
        self.__client = None

    @property
    def _client(self):
        # TODO: add cert options to containers conf
        cert_path = os.environ.get('DOCKER_CERT_PATH') or None
        if not cert_path:
            cert_path = os.path.join(os.path.expanduser('~'), '.docker')
        if self._conf.force_tlsverify or self._conf.tls:
            tls_config = docker.tls.TLSConfig(
                client_cert=(os.path.join(cert_path, 'cert.pem'),
                             os.path.join(cert_path, 'key.pem')),
                ca_cert=os.path.join(cert_path, 'ca.pem'),
                verify=self._conf.force_tlsverify,
            )
        else:
            tls_config = False
        if not self.__client:
            self.__client = DockerAPIClient(
                base_url=self._conf.host,
                tls=tls_config,
            )
        return self.__client

    @staticmethod
    def _first(f, *args, **kwargs):
        try:
            return f(*args, **kwargs)[0]
        except IndexError:
            return None

    @staticmethod
    def _filter_by_id_or_name(id, name):
        if id:
            return {'id': id}
        elif name:
            return {'name': name}
        return None

    @staticmethod
    def _kwopt_to_param_names(map_spec, key):
        params = []
        if 'param' not in map_spec and 'params' not in map_spec:
            params.append(key)
        elif 'param' in map_spec:
            params.append(map_spec['param'])
        params.extend(map_spec.get('params', ()))
        return params

    @staticmethod
    def _kwopt_to_params(map_spec, key, value):
        params = {}
        if 'map' in map_spec:
            value = map_spec['map'](value)
        for param in DockerAPIInterface._kwopt_to_param_names(map_spec, key):
            params[param] = value
        return params

    def _create_docker_api_spec(self, option_map_name, spec_class, kwopts):
        """Creates docker-py objects used as arguments to API methods.

        This method modifies ``kwopts`` by removing options that match the spec.

        :param  option_map_name:    Name of option map class variable (``_option_map`` is automatically appended)
        :type   option_map_name:    str
        :param  spec_class:         docker-py specification class or callable returning an instance
        :type   spec_class:         :class:`docker.types.Resources`, :class:`docker.types.ContainerSpec`, etc. or
                                    callable
        :param  kwopts:             Keyword options passed to calling method (e.g. :method:`DockerInterface.run()`)
        :type   kwopts:             dict
        :returns:                   Instantiated ``spec_class`` object
        :rtype:                     ``type(spec_class)``
        """
        def _kwopt_to_arg(map_spec, key, value, param=None):
            if isinstance(map_spec.get('param'), int):
                spec_opts.append((map_spec.get('param'), value))
            elif param is not None:
                spec_kwopts[param] = value
            else:
                spec_kwopts.update(DockerAPIInterface._kwopt_to_params(map_spec, key, value))
        # TODO: make this cleaner
        spec_opts = []
        spec_kwopts = {}
        option_map = getattr(self, option_map_name + '_option_map')
        # set defaults
        for key in filter(lambda k: option_map[k].get('default'), option_map.keys()):
            map_spec = option_map[key]
            _kwopt_to_arg(map_spec, key, map_spec['default'])
        # don't allow kwopts that start with _, those are reserved for "child" classes
        for kwopt in filter(lambda k: not k.startswith('_') and k in option_map, kwopts.keys()):
            map_spec = option_map[kwopt]
            _v = kwopts.pop(kwopt)
            _kwopt_to_arg(map_spec, kwopt, _v)
        # look for any child classes that need to be checked
        for _sub_k in filter(lambda k: k.startswith('_') and 'spec_class' in option_map[k], option_map.keys()):
            map_spec = option_map[_sub_k]
            param = _sub_k.lstrip('_')
            _sub_v = self._create_docker_api_spec(param, map_spec['spec_class'], kwopts)
            if _sub_v is not None or map_spec.get('required') or isinstance(map_spec.get('param'), int):
                _kwopt_to_arg(map_spec, None, _sub_v, param=param)
        # override params with values defined in the config
        for key in filter(lambda k: self._conf.get(k) is not None, option_map.keys()):
            _kwopt_to_arg(map_spec, key, self._conf[key])
        if spec_opts:
            spec_opts = sorted(spec_opts, key=lambda x: x[0])
            spec_opts = [i[1] for i in spec_opts]
        if spec_kwopts:
            return spec_class(*spec_opts, **spec_kwopts)
        else:
            return None

    def _volumes_to_native(self, volumes):
        """Convert a list of volume definitions to the docker-py container creation method parameters.

        :param  volumes:    List of volumes to translate
        :type   volumes:    list of :class:`galaxy.containers.docker_model.DockerVolume`s
        """
        paths = []
        binds = {}
        for v in volumes:
            path, bind = v.to_native()
            paths.append(path)
            binds.update(bind)
        return (paths, binds)

    def _create_host_config(self, kwopts):
        """Build the host configuration parameter for docker-py container creation.

        This method modifies ``kwopts`` by removing host config options and potentially setting the ``ports`` and
        ``volumes`` keys.

        :param  kwopts: Keyword options passed to calling method (e.g. :method:`DockerInterface.run()`)
        :type   kwopts: dict
        :returns:       The return value of `docker.APIClient.create_host_config()`
        :rtype:         dict
        """
        if 'publish_port_random' in kwopts:
            port = int(kwopts.pop('publish_port_random'))
            kwopts['port_bindings'] = {port: None}
            kwopts['ports'] = [port]
        if 'volumes' in kwopts:
            paths, binds = self._volumes_to_native(kwopts.pop('volumes'))
            kwopts['binds'] = binds
            kwopts['volumes'] = paths
        return self._create_docker_api_spec('host_config', self._client.create_host_config, kwopts)

    #
    # docker subcommands
    #

    def ps(self, id=None, name=None, running=True):
        return self._client.containers(all=not running, filters=self._filter_by_id_or_name(id, name))

    def run(self, command, image=None, **kwopts):
        image = image or self._default_image
        command = command or None
        log.debug("Creating docker container with image '%s' for command: %s", image, command)
        host_config = self._create_host_config(kwopts)
        log.debug("Docker container host configuration:\n%s", safe_dumps_formatted(host_config))
        log.debug("Docker container creation parameters:\n%s", safe_dumps_formatted(kwopts))
        success_test = partial(self._first, self.ps, name=kwopts['name'], running=False)
        # this can raise exceptions, if necessary we could wrap them in a more generic "creation failed" exception class
        container = self._client.create_container(
            image,
            command=command if command else None,
            host_config=host_config,
            success_test=success_test,
            max_tries=5,
            **kwopts
        )
        container_id = container.get('Id')
        log.debug("Starting container: %s (%s)", kwopts['name'], str(container_id))
        # start can safely be run more than once
        self._client.start(container=container_id)
        return DockerContainer.from_id(self, container_id)

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
