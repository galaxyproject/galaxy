"""
Interfaces to containerization software
"""
from __future__ import absolute_import

import errno
import inspect
import logging
import shlex
import subprocess
import sys
import uuid
from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty
)
from collections import namedtuple

import yaml
from six import string_types, with_metaclass
from six.moves import shlex_quote

from galaxy.exceptions import ContainerCLIError
from galaxy.util.submodules import import_submodules


DEFAULT_CONTAINER_TYPE = 'docker'
DEFAULT_CONF = {'_default_': {'type': DEFAULT_CONTAINER_TYPE}}

log = logging.getLogger(__name__)


class ContainerPort(namedtuple('ContainerPort', ('port', 'protocol', 'hostaddr', 'hostport'))):
    """Named tuple representing ports published by a container, with attributes:

    :ivar       port:       Port number (inside the container)
    :vartype    port:       int
    :ivar       protocol:   Port protocol, either ``tcp`` or ``udp``
    :vartype    protocol:   str
    :ivar       hostaddr:   Address or hostname where the published port can be accessed
    :vartype    hostaddr:   str
    :ivar       hostport:   Published port number on which the container can be accessed
    :vartype    hostport:   int
    """


class ContainerVolume(with_metaclass(ABCMeta, object)):

    valid_modes = frozenset(["ro", "rw"])

    def __init__(self, path, host_path=None, mode=None):
        self.path = path
        self.host_path = host_path
        self.mode = mode
        if mode and not self.mode_is_valid:
            raise ValueError("Invalid container volume mode: %s" % mode)

    @abstractmethod
    def from_str(cls, as_str):
        """Classmethod to convert from this container type's string representation.

        :param  as_str: string representation of volume
        :type   as_str: str
        """

    @abstractmethod
    def __str__(self):
        """Return this container type's string representation of the volume.
        """

    @abstractmethod
    def to_native(self):
        """Return this container type's native representation of the volume.
        """

    @property
    def mode_is_valid(self):
        return self.mode in self.valid_modes


class Container(with_metaclass(ABCMeta, object)):

    def __init__(self, interface, id, name=None, **kwargs):
        """:param   interface:  Container interface for the given container type
        :type       interface:  :class:`ContainerInterface` subclass instance
        :param      id:         Container identifier
        :type       id:         str
        :param      name:       Container name
        :type       name:       str
        """
        self._interface = interface
        self._id = id
        self._name = name

    @property
    def id(self):
        """The container's id"""
        return self._id

    @property
    def name(self):
        """The container's name"""
        return self._name

    @abstractmethod
    def from_id(cls, interface, id):
        """Classmethod to create an instance of Container from the container system's id for the given container type.

        :param  interface:  Container insterface for the given id
        :type   interface:  :class:`ContainerInterface` subclass instance
        :param  id:         Container identifier
        :type   id:         str
        :returns:           Container object
        :rtype:             :class:`Container` subclass instance
        """

    @abstractproperty
    def ports(self):
        """Attribute for accessing details of ports published by the container.

        :returns:   Port details
        :rtype:     list of :class:`ContainerPort`s
        """

    @abstractproperty
    def address(self):
        """Attribute for accessing the address or hostname where published ports can be accessed.

        :returns:   Hostname or IP address
        :rtype:     str
        """

    @abstractmethod
    def is_ready(self):
        """Indicate whether or not the container is "ready" (up, available, running).

        :returns:   True if ready, else False
        :rtpe:      bool
        """

    def map_port(self, port):
        """Map a given container port to a host address/port.

        For legacy reasons, if port is ``None``, the first port (if any) will be returned

        :param  port:   Container port to map
        :type   port:   int
        :returns:       Mapping to host address/port for given container port
        :rtype:         :class:`ContainerPort` instance
        """
        mapping = None
        ports = self.ports or []
        for mapping in ports:
            if port == mapping.port:
                return mapping
            if port is None:
                log.warning("Container %s (%s): Don't know how to map ports to containers with multiple exposed ports "
                            "when a specific port is not requested. Arbitrarily choosing first: %s",
                            self.name, self.id, mapping)
                return mapping
        else:
            if port is None:
                log.warning("Container %s (%s): No exposed ports found!", self.name, self.id)
            else:
                log.warning("Container %s (%s): No mapping found for port: %s", self.name, self.id, port)
        return None


class ContainerInterface(with_metaclass(ABCMeta, object)):

    container_type = None
    container_class = None
    volume_class = None
    conf_defaults = {
        'name_prefix': 'galaxy_',
    }
    option_map = {}
    publish_port_list_required = False
    supports_volumes = True

    def __init__(self, conf, key, containers_config_file):
        self._key = key
        self._containers_config_file = containers_config_file
        mro = reversed(self.__class__.__mro__)
        next(mro)
        self._conf = ContainerInterfaceConfig()
        for c in mro:
            self._conf.update(c.conf_defaults)
        self._conf.update(conf)
        self.validate_config()

    def _normalize_command(self, command):
        if isinstance(command, string_types):
            command = shlex.split(command)
        return command

    def _guess_kwopt_type(self, val):
        opttype = 'string'
        if isinstance(val, bool):
            opttype = 'boolean'
        elif isinstance(val, list):
            opttype = 'list'
            try:
                if isinstance(val[0], tuple) and len(val[0]) == 3:
                    opttype = 'list_of_kovtrips'
            except IndexError:
                pass
        elif isinstance(val, dict):
            opttype = 'list_of_kvpairs'
        return opttype

    def _guess_kwopt_flag(self, opt):
        return '--%s' % opt.replace('_', '-')

    def _stringify_kwopts(self, kwopts):
        opts = []
        for opt, val in kwopts.items():
            try:
                optdef = self.option_map[opt]
            except KeyError:
                optdef = {
                    'flag': self._guess_kwopt_flag(opt),
                    'type': self._guess_kwopt_type(val),
                }
                log.warning("option '%s' not in %s.option_map, guessing flag '%s' type '%s'",
                            opt, self.__class__.__name__, optdef['flag'], optdef['type'])
            opts.append(getattr(self, '_stringify_kwopt_' + optdef['type'])(optdef['flag'], val))
        return ' '.join(opts)

    def _stringify_kwopt_boolean(self, flag, val):
        """
        """
        return '{flag}={value}'.format(flag=flag, value=str(val).lower())

    def _stringify_kwopt_string(self, flag, val):
        """
        """
        return '{flag} {value}'.format(flag=flag, value=shlex_quote(str(val)))

    def _stringify_kwopt_list(self, flag, val):
        """
        """
        if isinstance(val, string_types):
            return self._stringify_kwopt_string(flag, val)
        return ' '.join(['{flag} {value}'.format(flag=flag, value=shlex_quote(str(v))) for v in val])

    def _stringify_kwopt_list_of_kvpairs(self, flag, val):
        """
        """
        l = []
        if isinstance(val, list):
            # ['foo=bar', 'baz=quux']
            l = val
        else:
            # {'foo': 'bar', 'baz': 'quux'}
            for k, v in dict(val).items():
                l.append('{k}={v}'.format(k=k, v=v))
        return self._stringify_kwopt_list(flag, l)

    def _stringify_kwopt_list_of_kovtrips(self, flag, val):
        """
        """
        if isinstance(val, string_types):
            return self._stringify_kwopt_string(flag, val)
        l = []
        for k, o, v in val:
            l.append('{k}{o}{v}'.format(k=k, o=o, v=v))
        return self._stringify_kwopt_list(flag, l)

    def _run_command(self, command, verbose=False):
        if verbose:
            log.debug('running command: [%s]', command)
        command_list = self._normalize_command(command)
        p = subprocess.Popen(command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
        stdout, stderr = p.communicate()
        if p.returncode == 0:
            return stdout.strip()
        else:
            msg = "Command '{}' returned non-zero exit status {}".format(command, p.returncode)
            log.error(msg + ': ' + stderr.strip())
            raise ContainerCLIError(
                msg,
                stdout=stdout.strip(),
                stderr=stderr.strip(),
                returncode=p.returncode,
                command=command,
                subprocess_command=command_list)

    @property
    def key(self):
        return self._key

    @property
    def containers_config_file(self):
        return self._containers_config_file

    def get_container(self, container_id):
        return self.container_class.from_id(self, container_id)

    def set_kwopts_name(self, kwopts):
        if self._name_prefix is not None:
            name = '{prefix}{name}'.format(
                prefix=self._name_prefix,
                name=kwopts.get('name', uuid.uuid4().hex)
            )
            kwopts['name'] = name

    def validate_config(self):
        """
        """
        self._name_prefix = self._conf.name_prefix

    @abstractmethod
    def run_in_container(self, command, image=None, **kwopts):
        """
        """


class ContainerInterfaceConfig(dict):

    def __setattr__(self, name, value):
        self[name] = value

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))

    def get(self, name, default=None):
        try:
            return self[name]
        except KeyError:
            return default


def build_container_interfaces(containers_config_file, containers_conf=None):
    """Build :class:`ContainerInterface`s. Pass ``containers_conf`` to avoid rereading the config file.

    :param  containers_config_file: Filename of containers_conf.yml
    :type   containers_config_file: str
    :param  containers_conf:        Optional containers conf (as read from containers_conf.yml), will be used in place
                                    of containers_config_file
    :type   containers_conf:        dict
    :returns:                       Instantiated container interfaces with keys corresponding to ``containers`` keys
    :rtype:                         dict of :class:`ContainerInterface` subclass instances
    """
    if not containers_conf:
        containers_conf = parse_containers_config(containers_config_file)
    interface_classes = _get_interface_modules()
    interfaces = {}
    for k, conf in containers_conf.items():
        container_type = conf.get('type', DEFAULT_CONTAINER_TYPE)
        assert container_type in interface_classes, "unknown container interface type: %s" % container_type
        interfaces[k] = interface_classes[container_type](conf, k, containers_config_file)
    return interfaces


def parse_containers_config(containers_config_file):
    """Parse a ``containers_conf.yml`` and return the contents of its ``containers`` dictionary.

    :param  containers_config_file: Filename of containers_conf.yml
    :type   containers_config_file: str
    :returns:                       Contents of the dictionary under the ``containers`` key
    :rtype:                         dict
    """
    conf = DEFAULT_CONF.copy()
    try:
        with open(containers_config_file) as fh:
            c = yaml.safe_load(fh)
            conf.update(c.get('containers', {}))
    except (OSError, IOError) as exc:
        if exc.errno == errno.ENOENT:
            log.debug("config file '%s' does not exist, running with default config", containers_config_file)
        else:
            raise
    return conf


def _get_interface_modules():
    interfaces = []
    modules = import_submodules(sys.modules[__name__])
    for module in modules:
        module_names = [getattr(module, _) for _ in dir(module)]
        classes = [_ for _ in module_names if inspect.isclass(_) and
            not _ == ContainerInterface and issubclass(_, ContainerInterface)]
        interfaces.extend(classes)
    return dict((x.container_type, x) for x in interfaces)
