#!/usr/bin/env python
"""
Docker Swarm mode management
"""
from __future__ import absolute_import, print_function

import argparse
import errno
import logging
import os
import subprocess
import sys
import time

try:
    import daemon
    import daemon.pidfile
    import lockfile
except ImportError:
    print('ERROR: The daemon module is required to use the swarm manager, '
          'install it with `pip install python-daemon`', file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

from galaxy.containers import (
    build_container_interfaces,
    ContainerInterfaceConfig,
    parse_containers_config,
)
from galaxy.containers.docker_model import (
    CPUS_CONSTRAINT,
    DockerServiceConstraints,
    IMAGE_CONSTRAINT,
)


DESCRIPTION = "Daemon to manage a Docker Swarm (running in Docker Swarm mode)."
SWARM_MANAGER_CONF_DEFAULTS = {
    'pid_file': '{xdg_data_home}/galaxy_swarm_manager.pid',
    'log_file': '{xdg_data_home}/galaxy_swarm_manager.log',
    'service_wait_count_limit': 0,
    'service_wait_time_limit': 5,
    'slots_min_limit': 0,
    'slots_max_limit': sys.maxsize,
    'slots_min_spare': 0,
    'node_idle_limit': 120,
    'limits': [],
    'spawn_wait_time': 30,
    'spawn_command': '/bin/true',
    'destroy_command': '/bin/true',
    'command_failure_command': '/bin/true',
    'command_retries': 0,
    'command_retry_wait': 10,
    'terminate_when_idle': True,
    'log_environment_variables': [],
}
log = logging.getLogger(__name__)


class SwarmManager(object):

    def __init__(self, conf, docker_interface):
        self._conf = conf
        self._cpus = docker_interface._conf.cpus
        self._docker_interface = docker_interface
        self._state = SwarmState(conf, docker_interface._conf)
        self._log_interval = 60
        self._last_log = time.time() - self._log_interval

    def run(self):
        while True:
            self._maintain_pool()
            self._check_for_new_nodes()
            self._clean_services()
            self._log_state()
            self._terminate_if_idle()
            time.sleep(1)

    def _run_command(self, command, command_retries=None, returncodes=None, **kwargs):
        stdout = None
        attempt = 0
        if not command_retries:
            command_retries = self._conf.command_retries
        allowed_returncodes = (0,)
        if returncodes:
            allowed_returncodes = returncodes
        raw_cmd = command.format(**kwargs)
        log.debug('running command: %s', raw_cmd)
        success = False
        while not success and attempt < command_retries + 1:
            attempt += 1
            p = subprocess.Popen(raw_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, shell=True)
            stdout, stderr = p.communicate()
            if p.returncode not in allowed_returncodes:
                msg = "error running '%s': returned %s" % (raw_cmd, p.returncode)
                if attempt < command_retries + 1:
                    msg += ', waiting %s seconds' % self._conf.command_retry_wait
                    time.sleep(self._conf.command_retry_wait)
                    log.warning(msg + "\nstdout: %s\nstderr: %s\n", stdout, stderr)
                else:
                    msg += ' (final attempt)'
                    log.error(msg + "\nstdout: %s\nstderr: %s\n", stdout, stderr)
                    self._run_command(self._conf.command_failure_command.format(failed_command=raw_cmd), command_retries=0)
                stdout = None
            else:
                stdout = stdout.strip()
                success = True
        if returncodes:
            return p.returncode, stdout
        else:
            return stdout

    # main loop methods

    def _maintain_pool(self):
        waiting = self._docker_interface.services_waiting_by_constraints()
        active = self._docker_interface.nodes_active_by_constraints()
        for constraints, needed_dict in self._state.slots_needed(waiting, active).items():
            services = needed_dict['services']
            nodes = needed_dict['nodes']
            slots_needed = needed_dict['slots_needed']
            if slots_needed > 0:
                self._spawn_nodes(constraints, services, slots_needed)
            elif slots_needed < 0:
                self._destroy_nodes(constraints, nodes, slots_needed)

    def _check_for_new_nodes(self):
        nodes = None
        for node_state in self._state.spawning_nodes():
            name = node_state['name']
            elapsed = node_state['elapsed']
            constraints = node_state['constraints']
            state = node_state['state']
            if not nodes:
                nodes = self._docker_interface.nodes()
            node = ([x for x in nodes if x.name == name] + [None])[0]
            if not node:
                if elapsed > self._conf.spawn_wait_time:
                    log.warning("spawning node '%s' not found in `docker node ls` and spawn_wait_time exceeded! %d seconds have elapsed", name, elapsed)
                    self._run_command(self._conf.command_failure_command.format(failed_command='wait_for_spawning_node %s' % name), command_retries=0)
                    self.mark_spawning_node_timeout(name)
            elif node.is_ok():
                node.set_labels_for_constraints(constraints)
                self._state.mark_spawning_node_ready(name)
                log.info("spawning node '%s' is ready!", name)
            elif node.state != state:
                log.info("spawning node '%s' state changed from '%s' to '%s'", name, state, node.state)
                node.set_labels_for_constraints(constraints)
                self._state.mark_spawning_node_state(name, node.state)
            elif elapsed > self._conf.spawn_wait_time:
                log.warning("spawning node '%s' state is '%s' after %s seconds", name, node.state, elapsed)

    def _clean_services(self):
        cleaned_services = self._docker_interface.services_clean()
        if cleaned_services:
            self._state.clean_services(cleaned_services)
            log.info("cleaned services: %s", ', '.join([x.id for x in cleaned_services]))

    @staticmethod
    def _env_str(envs, service):
        if envs.get(service.id):
            return ' [' + ', '.join(envs.get(service.id, [])) + ']'
        return ''

    def _log_state(self, now=False):
        if not now and not (self._last_log < (time.time() - self._log_interval)):
            return
        services = list(self._docker_interface.services())
        nodes = list(self._docker_interface.nodes())
        terminal = [s for s in services if s.terminal]
        node_task_ids = [t.id for nt in [n.tasks for n in nodes] for t in nt]
        envs = {}
        for service in services:
            envs[service.id] = ['%s=%s' % (k, service.env.get(k, 'unset')) for k in self._conf.log_environment_variables]
        log.info('%s nodes, %s services (%s terminal)', len(nodes), len(services), len(terminal))
        if terminal:
            service_strs = ['%s (state: %s)' % (s.name, s.state) for s in terminal]
            log.info('terminal services: %s', ', '.join(service_strs) or 'none')
        for service in services:
            unassigned_tasks = [t for t in service.tasks if t.id not in node_task_ids]
            if service not in terminal and unassigned_tasks:
                task = unassigned_tasks[0]
                log.info('service %s (%s)%s is not assigned to a node; state: %s %s', service.name, service.id,
                         self._env_str(envs, service), service.state, task.current_state_time)
        for node in nodes:
            log.info('node %s (%s) state: %s, %s tasks (%s terminal)', node.name, node.id, node.state,
                     len(node.tasks), len([t for t in node.tasks if t.terminal]))
            for task in node.tasks:
                if not task.service:
                    log.warning('node %s (%s) task %s (%s) has no service! state: %s %s', node.name, node.id,
                                task.slot, task.id, task.state, task.current_state_time)
                else:
                    log.info('node %s (%s) service %s (%s) task %s (%s)%s state: %s %s', node.name, node.id,
                             task.service.name, task.service.id, task.slot, task.id,
                             self._env_str(envs, task.service), task.state, task.current_state_time)
        self._last_log = time.time()

    def _terminate_if_idle(self):
        if not self._conf.terminate_when_idle:
            return
        for node in self._docker_interface.nodes():
            if node.task_count > 0:
                return  # nodes are running a galaxy service
        # no tasks running, check that all nodes are destroyed that are going to be destroyed
        waiting = self._docker_interface.services_waiting_by_constraints()
        active = self._docker_interface.nodes_active_by_constraints()
        for constraints, nodes in active.items():
            services = waiting.get(constraints, [])
            needed, total = self._state.slots_delta(constraints, services, nodes)
            if needed > 0:
                return  # services are waiting
            if needed < 0:
                extra_slots = max(
                    self._state.get_limit(constraints, 'slots_min_limit'),
                    self._state.get_limit(constraints, 'slots_min_spare')
                )
                if total + needed != extra_slots:
                    return  # otherwise, nodes remaining are for configured minimums
        # FIXME: there's a race condition here
        log.info('nothing to manage, shutting down')
        sys.exit(0)

    # other methods

    def _get_spawn_property(self, constraints, constraint_name, services):
        if services:
            # this isn't very nice
            if constraint_name == IMAGE_CONSTRAINT:
                return services[0].image
            elif constraint_name == CPUS_CONSTRAINT:
                return services[0].cpus
        for constraint in constraints:
            if constraint.name == constraint_name:
                return constraint.value
        return None

    def _spawn_nodes(self, constraints, services, slots_needed):
        service_ids = [x.id for x in services]
        if service_ids:
            log.info("requesting node(s) for services needing %s slots with constraints [%s]: %s",
                     slots_needed, constraints, ', '.join(service_ids))
        else:
            log.info("requesting node(s) for %s slots (due to minimum limits with constraints [%s]",
                     slots_needed, constraints)
        command = self._conf.spawn_command.format(
            service_ids=','.join(service_ids),
            service_count=len(services),
            image=self._get_spawn_property(constraints, IMAGE_CONSTRAINT, services) or '',
            cpus=self._get_spawn_property(constraints, CPUS_CONSTRAINT, services) or '',
            slots=slots_needed,
        )
        rc, output = self._run_command(command, returncodes=(0, 2))
        if rc == 2:
            log.info('spawn_command indicated that spawning should be retried: %s', output)
        elif not output:
            log.warning('spawn_command returned no new nodes, cannot manage nodes')
            self._state.mark_services_handled(services)
        else:
            log.info("node allocator will spawn: %s", output)
            self._state.nodes_requested(constraints, output.split())
            self._state.mark_services_handled(services)

    def _destroy_nodes(self, constraints, nodes, slots_needed):
        # nodes here is active nodes only, should be fine
        destroy_nodes = []
        destroyed_slots = 0
        for node in nodes:
            node_slots = node.cpus / self._cpus
            if self._node_ready_for_destruction(node) and (destroyed_slots + node_slots) <= abs(slots_needed):
                node.drain()
                destroy_nodes.append(node)
                destroyed_slots += node_slots
        if destroy_nodes:
            command = self._conf.destroy_command.format(
                nodes=' '.join([x.name for x in destroy_nodes]))
            destroyed_nodes = self._run_command(command)
            if not destroyed_nodes:
                log.warning('destroy_command returned no destroyed nodes')
            else:
                log.info("destroyed nodes: %s", destroyed_nodes)

    def _node_ready_for_destruction(self, node):
        ready = False
        if node.destroyable():
            if self._state.mark_node_idle(node.name):
                log.debug("node '%s' is now idle", node.name)
            ready = self._state.is_destruction_time(node)
        elif self._state.clear_node_idle(node.name):
            log.debug("node '%s' is no longer idle", node.name)
        return ready


class SwarmState(object):

    def __init__(self, conf, interface_conf):
        self._conf = conf
        self._cpus = interface_conf.cpus   # this is effectively the slot size
        self._service_create_image_constraint = interface_conf.service_create_image_constraint
        self._service_create_cpus_constraint = interface_conf.service_create_cpus_constraint
        self._handled_services = set()
        self._waiting_since = {}
        self._spawning_nodes = {}
        self._surplus_nodes = {}
        self._limits = {}
        for limit in conf.limits:
            constraints = DockerServiceConstraints.from_constraint_string_list(limit.get('constraints', []))
            self._limits[constraints] = self._make_limit_dict(limit)

    def _make_limit_dict(self, limit):
        return {
            'slots_min_limit': limit.get('slots_min_limit', self._conf.slots_min_limit),
            'slots_max_limit': limit.get('slots_max_limit', self._conf.slots_max_limit),
            'slots_min_spare': limit.get('slots_min_spare', self._conf.slots_min_spare),
            'node_idle_limit': limit.get('node_idle_limit', self._conf.node_idle_limit),
        }

    def slots_needed(self, waiting_services, active_nodes):
        """Given a list of services waiting of each constraint set, and active nodes of each constraint set, return the
        number of slots needed of each constraint set if the maximum wait thresholds have been reached, constrained by
        the configured limits.
        """
        rval = {}
        services_constraints = set(waiting_services.keys())
        nodes_constraints = set(active_nodes.keys())
        limits_constraints = set(self._limits.keys())
        all_constraints = services_constraints.union(nodes_constraints).union(limits_constraints)
        if not all_constraints and (self._conf.slots_min_spare or self._conf.slots_min_limit):
            if self._service_create_image_constraint or self._service_create_cpus_constraint:
                raise Exception("Global 'slots_min_limit' and/or 'slots_min_spare' are set and "
                    "'service_create_image_constraint' and/or 'service_create_cpus_constraint' are set but "
                    "constraint-specific limits are unset, minimum nodes cannot be started since the constraints are not "
                    "known until service creation time. Either disable 'service_create_*_constraint' or create "
                    "constraint-specific limits in the 'limits' section of 'manager_conf' in containers_conf.yml")
            all_constraints.add(DockerServiceConstraints.from_constraint_string_list([]))
        for constraints in all_constraints:
            services = waiting_services.get(constraints, [])
            nodes = active_nodes.get(constraints, [])
            # filter out any services that have already been handled
            services = [s for s in services if s not in self._handled_services]
            # calculate slots needed
            slots_needed, total_slots = self.slots_delta(constraints, services, nodes)
            # set or clear wait time
            if services and constraints not in self._waiting_since:
                self._waiting_since[constraints] = time.time()
            elif not services and constraints in self._waiting_since:
                del self._waiting_since[constraints]
            rval[constraints] = {
                'services': services,
                'nodes': nodes,
                'slots_needed': slots_needed,
            }
        return rval

    def slots_delta(self, constraints, services, nodes):
        total = 0
        used = 0
        if not self._cpus:
            # there are no cpu constraints, so no calculation can be done
            return 0, 0
        for node in nodes:
            used += sum([t.cpus for t in node.non_terminal_tasks]) / self._cpus
            total += node.cpus / self._cpus
        # need at least this many slots
        needed = used + self.get_limit(constraints, 'slots_min_spare')
        if (len(services) > self._conf.service_wait_count_limit and
                time.time() - self._waiting_since.get(constraints, time.time()) > self._conf.service_wait_time_limit):
            # add slots for waiting services that have exceeded limits
            needed += sum([s.cpus for s in services]) / self._cpus
        # subtract slots for spawning nodes
        needed -= sum([n.get('slots', 0) for n in self._spawning_nodes.get(constraints, {})])
        # ensure no less than slots_min_limit slots will exist (free or used)
        needed = max(needed, self.get_limit(constraints, 'slots_min_limit'))
        # ensure no more than slots_max_limit slots will exist
        needed = min(needed, self.get_limit(constraints, 'slots_max_limit'))
        # need to add/remove this many slots
        return int(needed - total), total

    def get_limit(self, constraints, limit):
        limits = self._limits.get(constraints, {})
        return limits.get(limit, self._conf[limit])

    def spawning_nodes(self):
        now = time.time()
        for constraints in self._spawning_nodes.keys():
            for name, node in self._spawning_nodes[constraints].items():
                yval = {
                    'name': name,
                    'elapsed': now - node['time_requested'],
                    'constraints': constraints,
                }
                yval.update(node)
                yield yval

    def nodes_requested(self, constraints, nodes):
        if constraints not in self._spawning_nodes:
            self._spawning_nodes[constraints] = {}
        for node in nodes:
            name = node.split(':')[0]
            try:
                slots = int(node.split(':')[1])
            except IndexError:
                slots = int(1 / self._cpus)
            self._spawning_nodes[constraints][name] = {
                'state': 'requested',
                'time_requested': time.time(),
                'slots': slots,
            }

    def mark_services_handled(self, services):
        self._handled_services.update(services)

    def mark_spawning_node_ready(self, node_name):
        self._delete_spawning_node(node_name)

    def mark_spawning_node_timeout(self, node_name):
        self._delete_spawning_node(node_name)

    def _delete_spawning_node(self, node_name):
        for constraints in self._spawning_nodes.keys():
            if node_name in self._spawning_nodes[constraints]:
                del self._spawning_nodes[constraints][node_name]

    def mark_spawning_node_state(self, node_name, state):
        for constraints in self._spawning_nodes.keys():
            if node_name in self._spawning_nodes[constraints]:
                self._spawning_nodes[constraints][node_name]['state'] = state

    def is_destruction_time(self, node):
        now = time.time()
        limit = self.get_limit(node.labels_as_constraints, 'node_idle_limit')
        return now - self._surplus_nodes.get(node.name, now) > limit

    def mark_node_idle(self, node_name):
        if node_name not in self._surplus_nodes:
            self._surplus_nodes[node_name] = time.time()
            return True
        return False

    def clear_node_idle(self, node_name):
        if node_name in self._surplus_nodes:
            del self._surplus_nodes[node_name]
            return True
        return False

    def clean_services(self, services):
        self._handled_services.difference_update(services)


def main():
    args = _arg_parser().parse_args()
    _run_swarm_manager(args)


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("-c", "--containers-config-file", default=None)
    parser.add_argument("-f", "--foreground", action="store_true", default=False)
    parser.add_argument("-d", "--debug", action="store_true", default=False)
    parser.add_argument("-s", "--swarm", default="_default_",
                        help='Swarm name in containers config to manage')
    return parser


def _run_swarm_manager(args):
    containers_config_file = _containers_config_file(args)
    containers_conf = parse_containers_config(containers_config_file)
    container_conf = _container_conf(containers_conf, args.swarm)
    swarm_manager_conf = _swarm_manager_conf(container_conf)
    _configure_logging(args, swarm_manager_conf)
    docker_interface = build_container_interfaces(containers_config_file, containers_conf=containers_conf)[args.swarm]
    pidfile = _swarm_manager_pidfile(swarm_manager_conf)

    if not args.foreground:
        _swarm_manager_daemon(pidfile, swarm_manager_conf['log_file'], swarm_manager_conf, docker_interface)
    else:
        if swarm_manager_conf['terminate_when_idle']:
            log.info('running in the foreground, disabling automatic swarm manager termination')
            swarm_manager_conf['terminate_when_idle'] = False
        else:
            log.info("running in the foreground")
        try:
            pidfile.acquire()
        except lockfile.AlreadyLocked:
            pid = pidfile.read_pid()
            try:
                os.kill(pid, 0)
                log.warning("swarm manager is already running in pid %s", pid)
                return
            except OSError:
                log.warning("removing stale lockfile: %s", pidfile.path)
                pidfile.break_lock()
                pidfile.acquire()
        try:
            _swarm_manager(swarm_manager_conf, docker_interface)
        finally:
            pidfile.release()


def _containers_config_file(args):
    containers_config_file = args.containers_config_file
    if not containers_config_file:
        for path in ('./config', '.'):
            testf = os.path.join(path, 'containers_conf.yml')
            if os.path.exists(testf):
                containers_config_file = testf
    assert containers_config_file, \
        "containers_conf.yml cannot be found, please set with '-c' or '--containers-config-file'"
    return containers_config_file


def _container_conf(containers_conf, swarm):
    assert swarm in containers_conf, \
        "invalid container configuration name: %s" % swarm
    assert containers_conf[swarm]['type'] == 'docker_swarm', \
        "'%s' container configuration is not 'docker_swarm' type" % swarm
    assert containers_conf[swarm].get('managed', True), \
        "'%s' swarm is not managed" % swarm
    return containers_conf[swarm]


def _swarm_manager_conf(new_conf):
    conf = ContainerInterfaceConfig()
    conf.update(SWARM_MANAGER_CONF_DEFAULTS)
    conf.update(new_conf.get('manager_conf', {}))
    xdg_env = _load_xdg_environment()
    for opt in ('pid_file', 'log_file'):
        conf[opt] = conf[opt].format(xdg_data_home=xdg_env['data_home'])
    return conf


def _configure_logging(args, conf):
    global log
    if args and args.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.getLevelName(conf.get('log_level', 'INFO').upper())
        assert int(log_level), 'invalid log level: %s' % conf['log_level']
    log = logging.getLogger(__name__)
    gxlog = logging.getLogger('galaxy')
    log.setLevel(log_level)
    gxlog.setLevel(log_level)
    log_format = conf.get('log_format', '%(name)s %(levelname)s %(asctime)s %(message)s')
    formatter = logging.Formatter(log_format)
    # file logging is handled by daemon
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    log.addHandler(handler)
    gxlog.addHandler(handler)


def _load_xdg_environment():
    return dict(
        data_home=os.path.expanduser(os.environ.get('XDG_DATA_HOME', '~/.local/share')),
    )


def _swarm_manager_pidfile(conf):
    try:
        os.makedirs(os.path.dirname(conf['pid_file']))
    except (IOError, OSError) as exc:
        if exc.errno != errno.EEXIST:
            raise
    return daemon.pidfile.PIDLockFile(conf['pid_file'])


def _swarm_manager_daemon(pidfile, logfile, swarm_manager_conf, docker_interface):
    log.info("daemonizing, logs will be written to '%s'", logfile)
    with open(logfile, 'a') as logfh:
        try:
            with daemon.DaemonContext(
                pidfile=pidfile,
                stdout=logfh,
                stderr=logfh,
            ):
                _swarm_manager(swarm_manager_conf, docker_interface)
        except lockfile.AlreadyLocked:
            log.debug("attempt to daemonize with swarm manager already running ignored")


def _swarm_manager(conf, docker_interface):
    swarm_manager = SwarmManager(conf, docker_interface)
    while True:
        try:
            log.info("swarm manager loaded, running...")
            swarm_manager.run()
        except Exception:
            log.exception("exception raised to run loop:")
            log.error("restarting due to fatal error")


if __name__ == '__main__':
    __name__ = 'swarm_manager'
    main()
