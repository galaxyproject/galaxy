"""
Model objects for docker objects
"""
from __future__ import absolute_import

import logging

from galaxy.containers import Container, ContainerPort


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


class DockerContainer(Container):

    def __init__(self, interface, id, name=None, inspect=None):
        super(DockerContainer, self).__init__(interface, id, name=name)
        self._inspect = inspect

    @classmethod
    def from_id(cls, interface, id):
        inspect = interface.inspect(id)
        return cls(interface, id, name=inspect[0]['Name'], inspect=inspect)

    @property
    def ports(self):
        # [{
        #     "NetworkSettings" : {
        #         "Ports" : {
        #             "3306/tcp" : [
        #                 {
        #                     "HostIp" : "127.0.0.1",
        #                     "HostPort" : "3306"
        #                 }
        #             ]
        rval = []
        port_mappings = self.inspect[0]['NetworkSettings']['Ports']
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
        return self.inspect[0]['State']['Running']

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
        self._interface = interface
        self._id = id
        self._name = name
        self._image = image
        self._inspect = inspect
        self._tasks = []
        if inspect:
            self._name = name or inspect[0]['Spec']['Name']
            self._image = image or inspect[0]['Spec']['TaskTemplate']['ContainerSpec']['Image']

    @classmethod
    def from_cli(cls, docker_interface, s, task_list):
        service = cls(docker_interface, s['ID'], name=s['NAME'], image=s['IMAGE'])
        for task_dict in task_list:
            if task_dict['NAME'].strip().startswith('\_'):
                continue    # historical task
            service.task_add(DockerTask.from_cli(docker_interface, task_dict, service=service))
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
        rval = []
        port_mappings = self.inspect[0]['Endpoint']['Ports']
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
        """Return the state of the first task in the service."""
        for task in self._tasks:
            return task.state
        else:
            return None

    @property
    def image(self):
        if self._image is None:
            self._image = self.inspect[0]['Spec']['TaskTemplate']['ContainerSpec']['Image']
        return self._image

    @property
    def cpus(self):
        try:
            cpus = self.inspect[0]['Spec']['TaskTemplate']['Resources']['Limits']['NanoCPUs'] / 1000000000.0
            if cpus == int(cpus):
                cpus = int(cpus)
            return cpus
        except KeyError:
            return 0

    @property
    def constraints(self):
        constraints = self.inspect[0]['Spec']['TaskTemplate']['Placement'].get('Constraints', [])
        return DockerServiceConstraints.from_constraint_string_list(constraints)

    def in_state(self, desired, current):
        try:
            for task in self._tasks:
                assert task.in_state(desired, current)
        except AssertionError:
            return False
        return True

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
                 availability=None, manager=False):
        self._interface = interface
        self._id = id
        self._name = name
        self._status = status
        self._availability = availability
        self._manager = manager
        self._inspect = None
        self._tasks = []

    @classmethod
    def from_cli(cls, docker_interface, n, task_list):
        node = cls(docker_interface, id=n['ID'], name=n['HOSTNAME'], status=n['STATUS'],
                   availability=n['AVAILABILITY'], manager=True if n['MANAGER STATUS'] else False)
        for task_dict in task_list:
            node.task_add(DockerTask.from_cli(docker_interface, task_dict, node=node))
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
    def inspect(self):
        if not self._inspect:
            self._inspect = self._interface.node_inspect(self._id or self._name)
        return self._inspect

    @property
    def state(self):
        return ('%s-%s' % (self._status, self._availability)).lower()

    @property
    def cpus(self):
        return self.inspect[0]['Description']['Resources']['NanoCPUs'] / 1000000000

    @property
    def labels(self):
        labels = self.inspect[0]['Spec'].get('Labels', {})
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
        return self._tasks

    @property
    def task_count(self):
        return len(self._tasks)

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
    def from_cli(cls, docker_interface, t, service=None, node=None):
        state = t['CURRENT STATE'].split()[0]
        return cls(docker_interface, id=t['ID'], name=t['NAME'], image=t['IMAGE'],
                   desired_state=t['DESIRED STATE'], state=state, error=t['ERROR'],
                   ports=t['PORTS'], service=service, node=node)

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def inspect(self):
        if not self._inspect:
            self._inspect = self._interface.task_inspect(self._id)
        return self._inspect

    @property
    def cpus(self):
        try:
            cpus = self.inspect[0]['Spec']['Resources']['Reservations']['NanoCPUs'] / 1000000000.0
            if cpus == int(cpus):
                cpus = int(cpus)
            return cpus
        except KeyError:
            return 0

    @property
    def state(self):
        return ('%s-%s' % (self._desired_state, self._state)).lower()

    def in_state(self, desired, current):
        return self._desired_state.lower() == desired.lower() and self._state.lower() == current.lower()
