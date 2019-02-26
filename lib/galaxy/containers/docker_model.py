"""
Model objects for docker objects
"""
from __future__ import absolute_import

import logging

try:
    import docker
except ImportError:
    from galaxy.util.bunch import Bunch
    docker = Bunch(errors=Bunch(NotFound=None))

from galaxy.containers import (
    Container,
    ContainerPort,
    ContainerVolume
)
from galaxy.util import pretty_print_time_interval


CPUS_LABEL = '_galaxy_cpus'
IMAGE_LABEL = '_galaxy_image'
CPUS_CONSTRAINT = 'node.labels.' + CPUS_LABEL
IMAGE_CONSTRAINT = 'node.labels.' + IMAGE_LABEL

log = logging.getLogger(__name__)


class DockerAttributeContainer(object):

    def __init__(self, members=None):
        if members is None:
            members = set()
        self._members = members

    def __eq__(self, other):
        return self.members == other.members

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(tuple(sorted([repr(x) for x in self._members])))

    def __str__(self):
        return ', '.join([str(x) for x in self._members]) or 'None'

    def __iter__(self):
        return iter(self._members)

    def __getitem__(self, name):
        for member in self._members:
            if member.name == name:
                return member
        else:
            raise KeyError(name)

    def __contains__(self, item):
        return item in self._members

    @property
    def members(self):
        return frozenset(self._members)

    def hash(self):
        return hex(self.__hash__())[2:]

    def get(self, name, default):
        try:
            return self[name]
        except KeyError:
            return default


class DockerVolume(ContainerVolume):
    @classmethod
    def from_str(cls, as_str):
        """Construct an instance from a string as would be passed to `docker run --volume`.

        A string in the format ``<host_path>:<mode>`` is supported for legacy purposes even though it is not valid
        Docker volume syntax.
        """
        if not as_str:
            raise ValueError("Failed to parse Docker volume from %s" % as_str)
        parts = as_str.split(":", 2)
        kwds = dict(host_path=parts[0])
        if len(parts) == 1:
            # auto-generated volume
            kwds["path"] = kwds["host_path"]
        elif len(parts) == 2:
            # /host_path:mode is not (or is no longer?) valid Docker volume syntax
            if parts[1] in DockerVolume.valid_modes:
                kwds["mode"] = parts[1]
                kwds["path"] = kwds["host_path"]
            else:
                kwds["path"] = parts[1]
        elif len(parts) == 3:
            kwds["path"] = parts[1]
            kwds["mode"] = parts[2]
        return cls(**kwds)

    def __str__(self):
        return ":".join(filter(lambda x: x is not None, (self.host_path, self.path, self.mode)))

    def to_native(self):
        host_path = self.host_path or self.path
        return (self.path, {host_path: {'bind': self.path, 'mode': self.mode}})


class DockerContainer(Container):

    def __init__(self, interface, id, name=None, inspect=None):
        super(DockerContainer, self).__init__(interface, id, name=name)
        self._inspect = inspect

    @classmethod
    def from_id(cls, interface, id):
        inspect = interface.inspect(id)
        return cls(interface, id, name=inspect['Name'], inspect=inspect)

    @property
    def ports(self):
        # {
        #     "NetworkSettings" : {
        #         "Ports" : {
        #             "3306/tcp" : [
        #                 {
        #                     "HostIp" : "127.0.0.1",
        #                     "HostPort" : "3306"
        #                 }
        #             ]
        rval = []
        try:
            port_mappings = self.inspect['NetworkSettings']['Ports']
        except KeyError as exc:
            log.warning("Failed to get ports for container %s from `docker inspect` output at "
                        "['NetworkSettings']['Ports']: %s: %s", self.id, exc.__class__.__name__, str(exc))
            return None
        for port_name in port_mappings:
            for binding in port_mappings[port_name]:
                rval.append(ContainerPort(
                    int(port_name.split('/')[0]),
                    port_name.split('/')[1],
                    self.address,
                    int(binding['HostPort']),
                ))
        return rval

    @property
    def address(self):
        if self._interface.host and self._interface.host.startswith('tcp://'):
            return self._interface.host.replace('tcp://', '').split(':', 1)[0]
        else:
            return 'localhost'

    def is_ready(self):
        return self.inspect['State']['Running']

    def __eq__(self, other):
        return self._id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._id)

    @property
    def inspect(self):
        if not self._inspect:
            self._inspect = self._interface.inspect(self._id)
        return self._inspect


class DockerService(Container):

    def __init__(self, interface, id, name=None, image=None, inspect=None):
        super(DockerService, self).__init__(interface, id, name=name)
        self._image = image
        self._inspect = inspect
        self._env = {}
        self._tasks = []
        if inspect:
            self._name = name or inspect['Spec']['Name']
            self._image = image or inspect['Spec']['TaskTemplate']['ContainerSpec']['Image']

    @classmethod
    def from_cli(cls, interface, s, task_list):
        service = cls(interface, s['ID'], name=s['NAME'], image=s['IMAGE'])
        for task_dict in task_list:
            if task_dict['NAME'].strip().startswith(r'\_'):
                continue    # historical task
            service.task_add(DockerTask.from_cli(interface, task_dict, service=service))
        return service

    @classmethod
    def from_id(cls, interface, id):
        inspect = interface.service_inspect(id)
        service = cls(interface, id, inspect=inspect)
        for task in interface.service_tasks(service):
            service.task_add(task)
        return service

    @property
    def ports(self):
        # {
        #     "Endpoint": {
        #         "Ports": [
        #             {
        #                 "Protocol": "tcp",
        #                 "TargetPort": 8888,
        #                 "PublishedPort": 30000,
        #                 "PublishMode": "ingress"
        #             }
        #         ]
        rval = []
        try:
            port_mappings = self.inspect['Endpoint']['Ports']
        except (IndexError, KeyError) as exc:
            log.warning("Failed to get ports for container %s from `docker service inspect` output at "
                        "['Endpoint']['Ports']: %s: %s", self.id, exc.__class__.__name__, str(exc))
            return None
        for binding in port_mappings:
            rval.append(ContainerPort(
                binding['TargetPort'],
                binding['Protocol'],
                self.address,               # use the routing mesh
                binding['PublishedPort']
            ))
        return rval

    @property
    def address(self):
        if self._interface.host and self._interface.host.startswith('tcp://'):
            return self._interface.host.replace('tcp://', '').split(':', 1)[0]
        else:
            return 'localhost'

    def is_ready(self):
        return self.in_state('Running', 'Running')

    def __eq__(self, other):
        return self._id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._id)

    def task_add(self, task):
        self._tasks.append(task)

    @property
    def inspect(self):
        if not self._inspect:
            self._inspect = self._interface.service_inspect(self._id)
        return self._inspect

    @property
    def state(self):
        """If one of this service's tasks desired state is running, return that task state, otherwise, return the state
        of a non-running task.

        This is imperfect because it doesn't attempt to provide useful information for replicas > 1 tasks, but it suits
        our purposes for now.
        """
        state = None
        for task in self.tasks:
            state = task.state
            if task.desired_state == 'running':
                break
        return state

    @property
    def env(self):
        if not self._env:
            try:
                for env_str in self.inspect['Spec']['TaskTemplate']['ContainerSpec']['Env']:
                    try:
                        self._env.update([env_str.split('=', 1)])
                    except ValueError:
                        self._env[env_str] = None
            except KeyError as exc:
                log.debug('Cannot retrieve container environment: KeyError: %s', str(exc))
        return self._env

    @property
    def terminal(self):
        """Same caveats as :meth:`state`.
        """
        for task in self.tasks:
            if task.desired_state == 'running':
                return False
        return True

    @property
    def node(self):
        """Same caveats as :meth:`state`.
        """
        for task in self.tasks:
            if task.node is not None:
                return task.node
        return None

    @property
    def image(self):
        if self._image is None:
            self._image = self.inspect['Spec']['TaskTemplate']['ContainerSpec']['Image']
        return self._image

    @property
    def cpus(self):
        try:
            cpus = self.inspect['Spec']['TaskTemplate']['Resources']['Limits']['NanoCPUs'] / 1000000000.0
            if cpus == int(cpus):
                cpus = int(cpus)
            return cpus
        except KeyError:
            return 0

    @property
    def constraints(self):
        constraints = self.inspect['Spec']['TaskTemplate']['Placement'].get('Constraints', [])
        return DockerServiceConstraints.from_constraint_string_list(constraints)

    @property
    def tasks(self):
        """A list of *all* tasks, including terminal ones.
        """
        if not self._tasks:
            self._tasks = []
            for task in self._interface.service_tasks(self):
                self.task_add(task)
        return self._tasks

    @property
    def task_count(self):
        """A count of *all* tasks, including terminal ones.
        """
        return len(self.tasks)

    def in_state(self, desired, current, tasks='any'):
        """Indicate if one of this service's tasks matches the desired state.
        """
        for task in self.tasks:
            if task.in_state(desired, current):
                if tasks == 'any':
                    # at least 1 task in desired state
                    return True
            elif tasks == 'all':
                # at least 1 task not in desired state
                return False
        else:
            return False if tasks == 'any' else True

    def constraint_add(self, name, op, value):
        self._interface.service_constraint_add(self.id, name, op, value)

    def set_cpus(self):
        self.constraint_add(CPUS_LABEL, '==', self.cpus)

    def set_image(self):
        self.constraint_add(IMAGE_LABEL, '==', self.image)


class DockerServiceConstraint(object):

    def __init__(self, name=None, op=None, value=None):
        self._name = name
        self._op = op
        self._value = value

    def __eq__(self, other):
        return self._name == other._name and \
            self._op == other._op and \
            self._value == other._value

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self._name, self._op, self._value))

    def __repr__(self):
        return '%s(%s%s%s)' % (self.__class__.__name__, self._name, self._op, self._value)

    def __str__(self):
        return '%s%s%s' % (self._name, self._op, self._value)

    @staticmethod
    def split_constraint_string(constraint_str):
        constraint = (constraint_str, '', '')
        for op in '==', '!=':
            t = constraint_str.partition(op)
            if len(t[0]) < len(constraint[0]):
                constraint = t
        if constraint[0] == constraint_str:
            raise Exception('Unable to parse constraint string: %s' % constraint_str)
        return [x.strip() for x in constraint]

    @classmethod
    def from_str(cls, constraint_str):
        name, op, value = DockerServiceConstraint.split_constraint_string(constraint_str)
        return cls(name=name, op=op, value=value)

    @property
    def name(self):
        return self._name

    @property
    def op(self):
        return self._op

    @property
    def value(self):
        return self._value

    @property
    def label(self):
        return DockerNodeLabel(
            name=self.name.replace('node.labels.', ''),
            value=self.value
        )


class DockerServiceConstraints(DockerAttributeContainer):

    member_class = DockerServiceConstraint

    @classmethod
    def from_constraint_string_list(cls, inspect):
        members = []
        for member_str in inspect:
            members.append(cls.member_class.from_str(member_str))
        return cls(members=members)

    @property
    def labels(self):
        return DockerNodeLabels(members=[x.label for x in self.members])


class DockerNode(object):

    def __init__(self, interface, id=None, name=None, status=None,
                 availability=None, manager=False, inspect=None):
        self._interface = interface
        self._id = id
        self._name = name
        self._status = status
        self._availability = availability
        self._manager = manager
        self._inspect = inspect
        if inspect:
            self._name = name or inspect['Description']['Hostname']
            self._status = status or inspect['Status']['State']
            self._availability = inspect['Spec']['Availability']
            self._manager = manager or inspect['Spec']['Role'] == 'manager'
        self._tasks = []

    @classmethod
    def from_cli(cls, interface, n, task_list):
        node = cls(interface, id=n['ID'], name=n['HOSTNAME'], status=n['STATUS'],
                   availability=n['AVAILABILITY'], manager=True if n['MANAGER STATUS'] else False)
        for task_dict in task_list:
            node.task_add(DockerTask.from_cli(interface, task_dict, node=node))
        return node

    @classmethod
    def from_id(cls, interface, id):
        inspect = interface.node_inspect(id)
        node = cls(interface, id, inspect=inspect)
        for task in interface.node_tasks(node):
            node.task_add(task)
        return node

    def task_add(self, task):
        self._tasks.append(task)

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        # this changes on update so don't cache
        return self._interface.node_inspect(self._id or self._name)['Version']['Index']

    @property
    def inspect(self):
        if not self._inspect:
            self._inspect = self._interface.node_inspect(self._id or self._name)
        return self._inspect

    @property
    def state(self):
        return ('%s-%s' % (self._status, self._availability)).lower()

    @property
    def cpus(self):
        return self.inspect['Description']['Resources']['NanoCPUs'] / 1000000000

    @property
    def labels(self):
        labels = self.inspect['Spec'].get('Labels', {}) or {}
        return DockerNodeLabels.from_label_dictionary(labels)

    def label_add(self, label, value):
        self._interface.node_update(self.id, label_add={label: value})

    @property
    def labels_as_constraints(self):
        constraints_strings = [x.constraint_string for x in self.labels]
        return DockerServiceConstraints.from_constraint_string_list(constraints_strings)

    def set_labels_for_constraints(self, constraints):
        for label in self._constraints_to_label_args(constraints):
            if label not in self.labels:
                log.info("setting node '%s' label '%s' to '%s'", self.name, label.name, label.value)
                self.label_add(label.name, label.value)

    def _constraints_to_label_args(self, constraints):
        constraints = filter(lambda x: x.name.startswith('node.labels.') and x.op == '==', constraints)
        labels = map(lambda x: DockerNodeLabel(name=x.name.replace('node.labels.', '', 1), value=x.value), constraints)
        return labels

    @property
    def tasks(self):
        """A list of *all* tasks, including terminal ones.
        """
        if not self._tasks:
            self._tasks = []
            for task in self._interface.node_tasks(self):
                self.task_add(task)
        return self._tasks

    @property
    def non_terminal_tasks(self):
        r = []
        for task in self.tasks:
            # ensure the task has a service - it is possible for "phantom" tasks to exist (service is removed, no
            # container is running, but the task still shows up in the node's task list)
            if not task.terminal and task.service is not None:
                r.append(task)
        return r

    @property
    def task_count(self):
        """A count of *all* tasks, including terminal ones.
        """
        return len(self.tasks)

    def in_state(self, status, availability):
        return self._status.lower() == status.lower() and self._availability.lower() == availability.lower()

    def is_ok(self):
        return self.in_state('Ready', 'Active')

    def is_managed(self):
        return not self._manager

    def destroyable(self):
        return not self._manager and self.is_ok() and self.task_count == 0

    def drain(self):
        self._interface.node_update(self.id, availability='drain')


class DockerNodeLabel(object):

    def __init__(self, name=None, value=None):
        self._name = name
        self._value = value

    def __eq__(self, other):
        return self._name == other._name and \
            self._value == other._value

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self._name, self._value))

    def __repr__(self):
        return '%s(%s: %s)' % (self.__class__.__name__, self._name, self._value)

    def __str__(self):
        return '%s: %s' % (self._name, self._value)

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    @property
    def constraint_string(self):
        return 'node.labels.{name}=={value}'.format(name=self.name, value=self.value)

    @property
    def constraint(self):
        return DockerServiceConstraint(
            name='node.labels.{name}'.format(name=self.name),
            op='==',
            value=self.value
        )


class DockerNodeLabels(DockerAttributeContainer):

    member_class = DockerNodeLabel

    @classmethod
    def from_label_dictionary(cls, inspect):
        members = []
        for k, v in inspect.items():
            members.append(cls.member_class(name=k, value=v))
        return cls(members=members)

    @property
    def constraints(self):
        return DockerServiceConstraints(members=[x.constraint for x in self.members])


class DockerTask(object):

    # these are the possible *current* state terminal states
    terminal_states = (
        'shutdown',  # this is normally only a desired state but I've seen a task with it as current as well
        'complete',
        'failed',
        'rejected',
        'orphaned',
    )

    def __init__(self, interface, id=None, name=None, image=None, desired_state=None,
                 state=None, error=None, ports=None, service=None, node=None):
        self._interface = interface
        self._id = id
        self._name = name
        self._image = image
        self._desired_state = desired_state
        self._state = state
        self._error = error
        self._ports = ports
        self._service = service
        self._node = node
        self._inspect = None

    @classmethod
    def from_cli(cls, interface, t, service=None, node=None):
        state = t['CURRENT STATE'].split()[0]
        return cls(interface, id=t['ID'], name=t['NAME'], image=t['IMAGE'],
                   desired_state=t['DESIRED STATE'], state=state, error=t['ERROR'],
                   ports=t['PORTS'], service=service, node=node)

    @classmethod
    def from_api(cls, interface, t, service=None, node=None):
        service = service or interface.service(id=t.get('ServiceID'))
        node = node or interface.node(id=t.get('NodeID'))
        if service:
            name = service.name + '.' + str(t['Slot'])
        else:
            name = t['ID']
        image = t['Spec']['ContainerSpec']['Image'].split('@', 1)[0],  # remove pin
        return cls(interface, id=t['ID'], name=name, image=image, desired_state=t['DesiredState'],
                   state=t['Status']['State'], ports=t['Status']['PortStatus'], error=t['Status']['Message'],
                   service=service, node=node)

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def inspect(self):
        if not self._inspect:
            try:
                self._inspect = self._interface.task_inspect(self._id)
            except docker.errors.NotFound:
                # This shouldn't be possible, appears to be some kind of Swarm bug (the node claims to have a task that
                # does not actually exist anymore, nor does its service exist).
                log.error('Task could not be inspected because Docker claims it does not exist: %s (%s)',
                          self.name, self.id)
                return None
        return self._inspect

    @property
    def slot(self):
        try:
            return self.inspect['Slot']
        except TypeError:
            return None

    @property
    def node(self):
        if not self._node:
            try:
                self._node = self._interface.node(id=self.inspect['NodeID'])
            except TypeError:
                return None
        return self._node

    @property
    def service(self):
        if not self._service:
            try:
                self._service = self._interface.service(id=self.inspect['ServiceID'])
            except TypeError:
                return None
        return self._service

    @property
    def cpus(self):
        try:
            cpus = self.inspect['Spec']['Resources']['Reservations']['NanoCPUs'] / 1000000000.0
            if cpus == int(cpus):
                cpus = int(cpus)
            return cpus
        except TypeError:
            return None
        except KeyError:
            return 0

    @property
    def state(self):
        return ('%s-%s' % (self._desired_state, self._state)).lower()

    @property
    def current_state(self):
        try:
            return self._state.lower()
        except TypeError:
            log.warning("Current state of %s (%s) is not a string: %s", self.name, self.id, str(self._state))
            return None

    @property
    def current_state_time(self):
        # Docker API returns a stamp w/ higher second precision than Python takes
        try:
            stamp = self.inspect['Status']['Timestamp']
        except TypeError:
            return None
        return pretty_print_time_interval(time=stamp[:stamp.index('.') + 7], precise=True, utc=stamp[-1] == 'Z')

    @property
    def desired_state(self):
        try:
            return self._desired_state.lower()
        except TypeError:
            log.warning("Desired state of %s (%s) is not a string: %s", self.name, self.id, str(self._desired_state))
            return None

    @property
    def terminal(self):
        return self.desired_state == 'shutdown' and self.current_state in self.terminal_states

    def in_state(self, desired, current):
        return self.desired_state == desired.lower() and self.current_state == current.lower()
