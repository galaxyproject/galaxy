"""
Docker Swarm mode management
"""
import argparse
import errno
import json
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
    daemon = None
import yaml

try:
    import galaxy   # noqa: F401 this is a test import
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        os.pardir)))

from galaxy.config import (
    configure_logging,
    find_path,
    find_root,
)
from galaxy.util.properties import find_config_file, load_app_properties


DESCRIPTION = "Daemon to manage a Docker Swarm (running in Docker Swarm mode)."
SWARM_MANAGER_CONF_DEFAULTS = {
    'pid_file': '{xdg_data_home}/galaxy_swarm_manager.pid',
    'log_file': '{xdg_data_home}/galaxy_swarm_manager.log',
    'command': 'docker {docker_args}',
    'service_prefix': 'galaxy_gie_',
    'max_waiting_services': 0,
    'max_wait_time': 5,
    'max_node_counts': {},  # max number of nodes per class to spawn
    'max_node_idle_time': 120,
    'node_prefix': None,
    'spawn_wait_time': 30,
    'spawn_command': '/bin/true',
    'destroy_command': '/bin/true',
    'command_failure_command': '/bin/true',
    'command_retries': 0,
    'command_retry_wait': 10,
    'terminate_when_idle': True,
}
OK_NODE_STATE = 'ready-active'
NODE_CPU_CLASS_LABEL = '_galaxy_cpu_class'
log = lambda *x: None   # noqa: E731


# TODO: pass around instances or at least namedtuples rather than these
# arbitrary dictionaries


class DockerInterface(object):

    def __init__(self, swarm_manager_conf):
        self.swarm_manager_conf = swarm_manager_conf
        self.command = swarm_manager_conf['command']
        self.service_prefix = swarm_manager_conf['service_prefix']

    def _run_docker(self, docker_args):
        raw_cmd = self.command.format(docker_args=docker_args)
        p = subprocess.Popen(raw_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, shell=True)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            log.error("%s\n%s" % (stdout, stderr))
            return None
        else:
            return stdout

    def _parse_docker_column_output(self, output):
        """Many docker commands do not provide an option to format the output
        or output in a machine-readily-parseable format (e.g. json). In order
        to deal with such output and hopefully stay compatible with future
        column order changes, key returned rows based on column headers.

        An assumption is made that a single space in the header row does not
        separate columns - column names can have spaces in them, and columns
        are separated by at least 2 spaces. This seems to be true as of Docker
        1.13.1.
        """
        parsed = []
        output = output.splitlines()
        header = output[0]
        colstarts = [0]
        colidx = 0
        spacect = 0
        if not output:
            return parsed
        for i, c in enumerate(header):
            if c != ' ' and spacect > 1:
                colidx += 1
                colstarts.append(i)
                spacect = 0
            elif c == ' ':
                spacect += 1
        colstarts.append(None)
        colheadings = []
        for i in range(0, len(colstarts) - 1):
            colheadings.append(header[colstarts[i]:colstarts[i + 1]].strip())
        for line in output[1:]:
            row = {}
            for i, key in enumerate(colheadings):
                row[key] = line[colstarts[i]:colstarts[i + 1]].strip()
            parsed.append(row)
        return parsed

    def _service_inspect(self, service_id):
        return self._run_docker(docker_args='service inspect {service_id}'.format(service_id=service_id))

    def _get_reserved_cpu_count(self, service_id=None, inspect_output=None):
        assert service_id or inspect_output, "Either `service_id` or `inspect_output` is required"
        if not inspect_output:
            inspect_output = self._service_inspect(service_id)
        try:
            return json.loads(inspect_output)[0]['Spec']['Resources']['Reservations']['NanoCPUs'] / 1000000000
        except KeyError:
            return 1

    def _node_inspect(self, node_name):
        return self._run_docker(docker_args='node inspect {node_name}'.format(node_name=node_name))

    def _get_node_cpu_class(self, node_name=None, inspect_output=None):
        assert node_name or inspect_output, "Either `node_name` or `inspect_output` is required"
        if not inspect_output:
            inspect_output = self._node_inspect(node_name)
        try:
            return json.loads(inspect_output)[0]['Spec']['Labels'][NODE_CPU_CLASS_LABEL]
        except KeyError:
            return None

    def waiting_services_by_cpu_class(self):
        rval = {}
        service_ids = self._services_in_state('Running', 'Pending')
        for service_id in service_ids:
            cpu_class = self._get_reserved_cpu_count(service_id=service_id)
            if cpu_class not in rval:
                rval[cpu_class] = []
            rval[cpu_class].append(service_id)
        return rval

    def active_nodes_by_cpu_class(self):
        rval = {}
        ls_output = self._run_docker(docker_args='node ls')
        for node in self._parse_docker_column_output(ls_output):
            cpu_class = self._get_node_cpu_class(node_name=node['HOSTNAME'])
            if cpu_class:
                cpu_class = int(cpu_class)
                rval[cpu_class] = rval.get(cpu_class, 0) + 1
        return rval

    def completed_services(self):
        return self._services_in_state('Shutdown', 'Complete')

    def _services_in_state(self, desired, current):
        service_ids = []
        for service_detail in self._service_details():
            if service_detail['DESIRED STATE'] == desired and service_detail['CURRENT STATE'].startswith(current):
                service_ids.append(service_detail['ID'])
        return service_ids

    def _service_details(self):
        ls_output = self._run_docker(docker_args='service ls')
        for service in self._parse_docker_column_output(ls_output):
            if not service['NAME'].startswith(self.service_prefix):
                continue
            ps_output = self._run_docker(docker_args='service ps --no-trunc {service_id}'.format(
                service_id=service['ID']))
            service_details = self._parse_docker_column_output(ps_output)[0]
            for col in ('ID', 'NAME'):
                service_details['PROCESS ' + col] = service_details[col]
                service_details[col] = service[col]
            yield service_details

    def clean_services(self):
        cleaned_services = []
        services = self.completed_services()
        if services:
            cleaned_services = self._run_docker(docker_args='service rm {service_ids}'.format(
                service_ids=' '.join(services))).splitlines()
        return cleaned_services

    def node_states(self):
        nodes = {}
        ls_output = self._run_docker(docker_args='node ls')
        for node in self._parse_docker_column_output(ls_output):
            nodes[node['HOSTNAME']] = {
                'state': ('%s-%s' % (node['STATUS'], node['AVAILABILITY'])).lower(),
                'manager': True if node['MANAGER STATUS'] else False,
            }
        return nodes

    def node_job_count(self, node_name):
        ps_output = self._run_docker(docker_args='node ps --no-trunc {node_name}'.format(
            node_name=node_name))
        jobs = filter(lambda x: x['NAME'].startswith(self.service_prefix), self._parse_docker_column_output(ps_output))
        return len(jobs)

    def ensure_node_cpu_class(self, node, cpu_class):
        cur_cpu_class = self._get_node_cpu_class(node_name=node)
        if str(cpu_class) != cur_cpu_class:
            log.info("setting node '%s' cpu class from '%s' to '%s'", node, cur_cpu_class, cpu_class)
            self._run_docker(docker_args='node update --label-add {label_name}={label_val} {node}'.format(
                label_name=NODE_CPU_CLASS_LABEL,
                label_val=cpu_class,
                node=node))
        else:
            log.debug("node '%s' cpu class is '%s'", node, cur_cpu_class)

    def node_cpu_class(self, node):
        return self._get_node_cpu_class(node_name=node)


class SwarmManager(object):

    def __init__(self, conf):
        self.conf = conf
        self.docker_interface = DockerInterface(conf)
        self.state = SwarmState(conf)
        self.spawn_wait_time = conf['spawn_wait_time']
        self.spawn_command = conf['spawn_command']
        self.destroy_command = conf['destroy_command']
        self.command_retries = conf['command_retries']
        self.command_retry_wait = conf['command_retry_wait']
        self.node_prefix = conf['node_prefix']
        self.terminate_when_idle = conf['terminate_when_idle']

    def run(self):
        while True:
            node_states = None
            self._spawn_if_waiting()
            self._check_for_new_nodes(node_states=node_states)
            self._destroy_if_surplus(node_states=node_states)
            self._clean_services()
            self._terminate_if_idle()
            time.sleep(1)

    def _run_command(self, command, command_retries=None, **kwargs):
        stdout = None
        attempt = 0
        if not command_retries:
            command_retries = self.command_retries
        raw_cmd = command.format(**kwargs)
        log.debug('running command: %s', raw_cmd)
        while not stdout and attempt < command_retries + 1:
            attempt += 1
            p = subprocess.Popen(raw_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, shell=True)
            stdout, stderr = p.communicate()
            if p.returncode != 0:
                msg = "error running '%s'" % raw_cmd
                if attempt < command_retries + 1:
                    msg += ', waiting %s seconds' % self.command_retry_wait
                    time.sleep(self.command_retry_wait)
                    log.warning(msg + "\nstdout: %s\nstderr: %s\n", stdout, stderr)
                else:
                    msg += ' (final attempt)'
                    log.error(msg + "\nstdout: %s\nstderr: %s\n", stdout, stderr)
                    self._run_command(self.conf['command_failure_command'].format(failed_command=raw_cmd), command_retries=0)
                stdout = None
            else:
                stdout = stdout.strip()
        return stdout

    def _spawn_if_waiting(self):
        waiting = self.docker_interface.waiting_services_by_cpu_class()
        active = self.docker_interface.active_nodes_by_cpu_class()
        cpus_needed = self.state.need_nodes(waiting, active)
        for cpu_class in cpus_needed.keys():
            log.info("requesting node(s) for services requesting %d CPUs total (%d CPUs each): %s", cpus_needed[cpu_class], cpu_class, ' '.join(waiting[cpu_class]))
            command = '{spawn_command}'.format(spawn_command=self.spawn_command).format(
                cpu_class=cpu_class,
                cpus_needed=cpus_needed[cpu_class])
            new_nodes = self._run_command(command)
            if not new_nodes:
                log.warning('spawn_command returned no new nodes, cannot manage nodes')
            else:
                log.info("node allocator will spawn: %s", new_nodes)
                self.state.nodes_requested(cpu_class, new_nodes.split(), waiting[cpu_class])
            self.state.mark_services_handled(waiting[cpu_class])

    def _check_for_new_nodes(self, node_states=None):
        for node_name, elapsed, cpu_class, node in self.state.spawning_nodes():
            if not node_states:
                node_states = self.docker_interface.node_states()
            if node_name not in node_states:
                if elapsed > self.spawn_wait_time:
                    log.warning("spawning node '%s' not found in `docker node ls` and spawn_wait_time exceeded! %d seconds have elapsed", node_name, elapsed)
                    self._run_command(self.conf['command_failure_command'].format(failed_command='wait_for_spawning_node %s' % node_name), command_retries=0)
                    self.mark_spawning_node_timeout(node_name)
            elif node_states[node_name]['state'] == OK_NODE_STATE:
                self.docker_interface.ensure_node_cpu_class(node_name, cpu_class)
                self.state.mark_spawning_node_ready(node_name)
                log.info("spawning node '%s' is ready!", node_name)
            elif node_states[node_name]['state'] != node['state']:
                log.info("spawning node '%s' state changed from '%s' to '%s'", node_name, node['state'], node_states[node_name]['state'])
                self.docker_interface.ensure_node_cpu_class(node_name, cpu_class)
                self.state.mark_spawning_node_state(node_name, node_states[node_name]['state'])
            elif elapsed > self.spawn_wait_time:
                log.warning("spawning node '%s' state is '%s' after %s seconds", node_name, node_states[node_name]['state'], elapsed)

    def _destroy_if_surplus(self, node_states=None):
        destroy_nodes = []
        if not node_states:
            node_states = self.docker_interface.node_states()
        for node_name, node_state in node_states.items():
            if self._node_ready_for_destruction(node_name, node_state):
                destroy_nodes.append(node_name)
        if destroy_nodes:
            command = '{destroy_command}'.format(destroy_command=self.destroy_command).format(
                nodes=' '.join(destroy_nodes))
            destroyed_nodes = self._run_command(command)
            if not destroyed_nodes:
                log.warning('destroy_command returned no destroyed nodes')
            else:
                log.info("destroyed nodes: %s", destroyed_nodes)

    def _node_is_managed(self, node_name, node_state):
        return (not self.node_prefix or node_name.startswith(self.node_prefix)) and not node_state['manager']

    def _node_ready_for_destruction(self, node_name, node_state):
        ready = False
        if (self._node_is_managed(node_name, node_state) and
                node_state['state'] == 'ready-active'):
            if self.docker_interface.node_job_count(node_name) == 0:
                self.state.mark_node_idle(node_name)
                ready = self.state.is_destruction_time(node_name)
            else:
                self.state.clear_node_idle(node_name)
        return ready

    def _clean_services(self):
        cleaned_services = self.docker_interface.clean_services()
        if cleaned_services:
            self.state.clean_services(cleaned_services)
            log.info("cleaned services: %s", ', '.join(cleaned_services))

    def _terminate_if_idle(self):
        if not self.terminate_when_idle:
            return
        node_states = self.docker_interface.node_states()
        for node_name, node_state in node_states.items():
            if self._node_is_managed(node_name, node_state):
                return  # nonterminated managed nodes remain
            elif self.docker_interface.node_job_count(node_name) > 0:
                return  # unmanaged nodes are running a galaxy service
        # FIXME: there's a race condition here
        if self.docker_interface.waiting_services_by_cpu_class():
            return      # waiting jobs remain
        log.info('nothing to manage, shutting down')
        sys.exit(0)


class SwarmState(object):

    def __init__(self, conf):
        self._handled_services = set()
        self._waiting_since = {}
        self._spawning_nodes = {}
        self._surplus_nodes = {}
        self.max_waiting_services = conf['max_waiting_services']
        self.max_wait_time = conf['max_wait_time']
        self.max_node_idle_time = conf['max_node_idle_time']
        self.max_node_counts = conf['max_node_counts']

    def need_nodes(self, waiting_services, active_nodes):
        rval = {}
        need_cpus = self._needed_cpu_counts(waiting_services)
        spawning_cpus = self._spawning_cpu_counts()
        for cpu_class in need_cpus.keys():
            cpus_needed = need_cpus[cpu_class] - spawning_cpus.get(cpu_class, 0)
            if cpus_needed > 0 and active_nodes.get(cpu_class, 0) < self.max_node_counts.get(cpu_class, sys.maxint):
                rval[cpu_class] = cpus_needed
        return rval

    def _needed_cpu_counts(self, waiting_services):
        """Given a count of services waiting of each cpu class, return the
        count of nodes needed of each node type if the maximum wait times and
        waiting service count thresholds have been reached.
        """
        rval = {}
        new_waiting_since = {}
        for cpu_class in waiting_services.keys():
            new_waiting_since[cpu_class] = self._waiting_since.get(cpu_class, time.time())
            # filter out any services that have already been handled
            unhandled_waiting_services = [ s for s in waiting_services[cpu_class] if s not in self._handled_services ]
            if (len(unhandled_waiting_services) > self.max_waiting_services and
                    time.time() - new_waiting_since[cpu_class] > self.max_wait_time):
                # need waiting[cpu_class] nodes of this class
                rval[cpu_class] = len(unhandled_waiting_services)
        # drop any cpu_classes from waiting_since that are no longer waiting
        self._waiting_since = new_waiting_since
        return rval

    def spawning_nodes(self):
        now = time.time()
        for cpu_class in self._spawning_nodes.keys():
            for node_name in self._spawning_nodes[cpu_class].keys():
                node = self._spawning_nodes[cpu_class][node_name]
                yield (node_name, now - node['time_requested'], cpu_class, node)

    def _spawning_cpu_counts(self):
        rval = {}
        for cpu_class in self._spawning_nodes.keys():
            rval[cpu_class] = sum([ v['cpu_count'] for k, v in self._spawning_nodes[cpu_class].items() ])
        return rval

    def nodes_requested(self, cpu_class, nodes, services):
        if cpu_class not in self._spawning_nodes:
            self._spawning_nodes[cpu_class] = {}
        for node in nodes:
            node_name = node.split(':')[0]
            try:
                cpu_count = node.split(':')[1]
            except IndexError:
                cpu_count = cpu_class
            self._spawning_nodes[cpu_class][node_name] = {
                'state': 'requested',
                'cpu_count': cpu_count,
                'time_requested': time.time(),
            }

    def mark_services_handled(self, services):
        self._handled_services.update(services)

    def mark_spawning_node_ready(self, node_name):
        self._delete_spawning_node(node_name)

    def mark_spawning_node_timeout(self, node_name):
        self._delete_spawning_node(node_name)

    def _delete_spawning_node(self, node_name):
        for cpu_class in self._spawning_nodes.keys():
            if node_name in self._spawning_nodes[cpu_class]:
                del self._spawning_nodes[cpu_class][node_name]

    def mark_spawning_node_state(self, node_name, state):
        for cpu_class in self._spawning_nodes.keys():
            if node_name in self._spawning_nodes[cpu_class]:
                self._spawning_nodes[cpu_class][node_name]['state'] = state

    def is_destruction_time(self, node_name):
        now = time.time()
        return now - self._surplus_nodes.get(node_name, now) > self.max_node_idle_time

    def mark_node_idle(self, node_name):
        if node_name not in self._surplus_nodes:
            self._surplus_nodes[node_name] = time.time()

    def clear_node_idle(self, node_name):
        if node_name in self._surplus_nodes:
            del self._surplus_nodes[node_name]

    def clean_services(self, services):
        self._handled_services.difference_update(services)


def main(argv=None, fork=False):
    if not daemon:
        log.warning('The daemon module is required to use the swarm manager, install it with `pip install python-daemon`')
        return
    if argv is None:
        argv = sys.argv[1:]
    if fork:
        p = subprocess.Popen([sys.executable, __file__] + argv)
        p.wait()
    else:
        args = _arg_parser().parse_args(argv)
        kwargs = _app_properties(args)
        _run_swarm_manager(kwargs, args)


def _app_properties(args):
    galaxy_config_file = find_config_file("config/galaxy.ini", "universe_wsgi.ini", args.galaxy_config_file)
    app_properties = load_app_properties(ini_file=galaxy_config_file)
    return app_properties


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("-c", "--galaxy-config-file", default=None)
    return parser


def _run_swarm_manager(kwargs, args):
    configure_logging(kwargs)
    global log
    log = logging.getLogger(__name__)

    root = find_root(kwargs)
    swarm_manager_config_file = find_path(kwargs, "swarm_manager_config_file", root)
    swarm_manager_conf = _parse_swarm_manager_conf(swarm_manager_config_file)
    try:
        os.makedirs(os.path.dirname(swarm_manager_conf['pid_file']))
    except (IOError, OSError) as exc:
        if exc.errno != errno.EEXIST:
            raise
    log.debug("daemonizing, logs will be written to '%s'", swarm_manager_conf['log_file'])
    pidfile = daemon.pidfile.PIDLockFile(swarm_manager_conf['pid_file'])
    with open(swarm_manager_conf['log_file'], 'a') as logfh:
        try:
            with daemon.DaemonContext(
                pidfile=pidfile,
                stdout=logfh,
                stderr=logfh,
            ):
                _swarm_manager(swarm_manager_conf)
        except lockfile.AlreadyLocked:
            log.debug("attempt to daemonize with swarm manager already running ignored")


def _load_xdg_environment():
    return dict(
        data_home=os.path.expanduser(os.environ.get('XDG_DATA_HOME', '~/.local/share')),
    )


def _parse_swarm_manager_conf(swarm_manager_config_file):
    conf = SWARM_MANAGER_CONF_DEFAULTS.copy()
    xdg_env = _load_xdg_environment()
    try:
        with open(swarm_manager_config_file) as fh:
            conf.update(yaml.load(fh))
    except (OSError, IOError) as exc:
        if exc.errno == errno.ENOENT:
            log.warning("config file '%s' does not exist, running with default config", swarm_manager_config_file)
        else:
            raise
    for opt in ('pid_file', 'log_file'):
        conf[opt] = conf[opt].format(xdg_data_home=xdg_env['data_home'])
    return conf


def _swarm_manager(conf):
    swarm_manager = SwarmManager(conf)
    log.debug("swarm manager loaded, running...")
    swarm_manager.run()


if __name__ == '__main__':
    __name__ = 'swarm_manager'
    main()
