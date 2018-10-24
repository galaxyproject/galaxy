#!/usr/bin/env python
"""
Downloads files to temp locations.  This script is invoked by the Transfer
Manager (galaxy.jobs.transfer_manager) and should not normally be invoked by
hand.

This is deprecated - it only works with older ini configurations of Galaxy.
"""
import json
import logging
import optparse
import os
import random
import sys
import tempfile
import threading
import time

try:
    import pexpect
except ImportError:
    pexpect = None

from daemon import DaemonContext
from six.moves import (
    configparser,
    socketserver
)
from six.moves.urllib.error import URLError
from six.moves.urllib.request import urlopen
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import scoped_session, sessionmaker

galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(1, os.path.join(galaxy_root, 'lib'))

import galaxy.model
from galaxy.util import bunch
from galaxy.util.json import jsonrpc_response, validate_jsonrpc_request

PEXPECT_IMPORT_MESSAGE = ('The Python pexpect package is required to use this '
                          'feature, please install it')

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
log.addHandler(handler)

debug = False
slow = False


class ArgHandler(object):
    """
    Collect command line flags.
    """
    def __init__(self):
        self.parser = optparse.OptionParser()
        self.parser.add_option('-c', '--config', dest='config', help='Path to Galaxy config file (config/galaxy.ini)',
                               default=os.path.abspath(os.path.join(galaxy_root, 'config/galaxy.ini')))
        self.parser.add_option('-d', '--debug', action='store_true', dest='debug', help="Debug (don't detach)")
        self.parser.add_option('-s', '--slow', action='store_true', dest='slow', help="Transfer slowly (for debugging)")
        self.opts = None

    def parse(self):
        self.opts, args = self.parser.parse_args()
        if len(args) != 1:
            log.error('usage: transfer.py <transfer job id>')
            sys.exit(1)
        try:
            self.transfer_job_id = int(args[0])
        except TypeError:
            log.error('The provided transfer job ID is not an integer: %s' % args[0])
            sys.exit(1)
        if self.opts.debug:
            global debug
            debug = True
            log.setLevel(logging.DEBUG)
        if self.opts.slow:
            global slow
            slow = True


class GalaxyApp(object):
    """
    A shell Galaxy App to provide access to the Galaxy configuration and
    model/database.
    """
    def __init__(self, config_file):
        self.config = configparser.ConfigParser(dict(database_file='database/universe.sqlite',
                                                     file_path='database/files',
                                                     transfer_worker_port_range='12275-12675',
                                                     transfer_worker_log=None))
        self.config.read(config_file)
        self.model = bunch.Bunch()
        self.connect_database()

    def connect_database(self):
        # Avoid loading the entire model since doing so is exceptionally slow
        default_dburl = 'sqlite:///%s?isolation_level=IMMEDIATE' % self.config.get('app:main', 'database_file')
        try:
            dburl = self.config.get('app:main', 'database_connection')
        except configparser.NoOptionError:
            dburl = default_dburl
        engine = create_engine(dburl)
        metadata = MetaData(engine)
        self.sa_session = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=True))
        self.model.TransferJob = galaxy.model.TransferJob
        self.model.TransferJob.table = Table("transfer_job", metadata, autoload=True)

    def get_transfer_job(self, id):
        return self.sa_session.query(self.model.TransferJob).get(int(id))


class ListenerServer(socketserver.ThreadingTCPServer):
    """
    The listener will accept state requests and new transfers for as long as
    the manager is running.
    """
    def __init__(self, port_range, RequestHandlerClass, app, transfer_job, state_result):
        self.state_result = state_result
        # Try random ports until a free one is found
        while True:
            random_port = random.choice(port_range)
            try:
                super(ListenerServer, self).__init__(('localhost', random_port), RequestHandlerClass)
                log.info('Listening on port %s' % random_port)
                break
            except Exception as e:
                log.warning('Tried binding port %s: %s' % (random_port, str(e)))
        transfer_job.socket = random_port
        app.sa_session.add(transfer_job)
        app.sa_session.flush()


class ListenerRequestHandler(socketserver.BaseRequestHandler):
    """
    Handle state or transfer requests received on the socket.
    """
    def handle(self):
        request = self.request.recv(8192)
        response = {}
        valid, request, response = validate_jsonrpc_request(request, ('get_state', ), ())
        if valid:
            self.request.send(json.dumps(jsonrpc_response(request=request, result=self.server.state_result.result)))
        else:
            error_msg = 'Unable to serve request: %s' % response['error']['message']
            if 'data' in response['error']:
                error_msg += ': %s' % response['error']['data']
            log.error(error_msg)
            log.debug('Original request was: %s' % request)


class StateResult(object):
    """
    A mutable container for the 'result' portion of JSON-RPC responses to state requests.
    """
    def __init__(self, result=None):
        self.result = result


def transfer(app, transfer_job_id):
    transfer_job = app.get_transfer_job(transfer_job_id)
    if transfer_job is None:
        log.error('Invalid transfer job ID: %s' % transfer_job_id)
        return False
    port_range = app.config.get('app:main', 'transfer_worker_port_range')
    try:
        port_range = [int(p) for p in port_range.split('-')]
    except Exception as e:
        log.error('Invalid port range set in transfer_worker_port_range: %s: %s' % (port_range, str(e)))
        return False
    protocol = transfer_job.params['protocol']
    if protocol not in ('http', 'https', 'scp'):
        log.error('Unsupported protocol: %s' % protocol)
        return False
    state_result = StateResult(result=dict(state=transfer_job.states.RUNNING, info='Transfer process starting up.'))
    listener_server = ListenerServer(range(port_range[0], port_range[1] + 1), ListenerRequestHandler, app, transfer_job, state_result)
    # daemonize here (if desired)
    if not debug:
        daemon_context = DaemonContext(files_preserve=[listener_server.fileno()], working_directory=os.getcwd())
        daemon_context.open()
        # If this fails, it'll never be detected.  Hopefully it won't fail since it succeeded once.
        app.connect_database()  # daemon closed the database fd
        transfer_job = app.get_transfer_job(transfer_job_id)
    listener_thread = threading.Thread(target=listener_server.serve_forever)
    listener_thread.setDaemon(True)
    listener_thread.start()
    # Store this process' pid so unhandled deaths can be handled by the restarter
    transfer_job.pid = os.getpid()
    app.sa_session.add(transfer_job)
    app.sa_session.flush()
    terminal_state = None
    if protocol in ['http', 'https']:
        for transfer_result_dict in http_transfer(transfer_job):
            state_result.result = transfer_result_dict
            if transfer_result_dict['state'] in transfer_job.terminal_states:
                terminal_state = transfer_result_dict
    elif protocol in ['scp']:
        # Transfer the file using scp
        transfer_result_dict = scp_transfer(transfer_job)
        # Handle the state of the transfer
        state = transfer_result_dict['state']
        state_result.result = transfer_result_dict
        if state in transfer_job.terminal_states:
            terminal_state = transfer_result_dict
    if terminal_state is not None:
        transfer_job.state = terminal_state['state']
        for name in ['info', 'path']:
            if name in terminal_state:
                transfer_job.__setattr__(name, terminal_state[name])
    else:
        transfer_job.state = transfer_job.states.ERROR
        transfer_job.info = 'Unknown error encountered by transfer worker.'
    app.sa_session.add(transfer_job)
    app.sa_session.flush()
    return True


def http_transfer(transfer_job):
    """Plugin" for handling http(s) transfers."""
    url = transfer_job.params['url']
    assert url.startswith('http://') or url.startswith('https://')
    try:
        f = urlopen(url)
    except URLError as e:
        yield dict(state=transfer_job.states.ERROR, info='Unable to open URL: %s' % str(e))
        return
    size = f.info().getheader('Content-Length')
    if size is not None:
        size = int(size)
    chunksize = 1024 * 1024
    if slow:
        chunksize = 1024
    read = 0
    last = 0
    try:
        fh, fn = tempfile.mkstemp()
    except Exception as e:
        yield dict(state=transfer_job.states.ERROR, info='Unable to create temporary file for transfer: %s' % str(e))
        return
    log.debug('Writing %s to %s, size is %s' % (url, fn, size or 'unknown'))
    try:
        while True:
            chunk = f.read(chunksize)
            if not chunk:
                break
            os.write(fh, chunk)
            read += chunksize
            if size is not None and read < size:
                percent = int(float(read) / size * 100)
                if percent != last:
                    yield dict(state=transfer_job.states.PROGRESS, read=read, percent='%s' % percent)
                    last = percent
            elif size is None:
                yield dict(state=transfer_job.states.PROGRESS, read=read)
            if slow:
                time.sleep(1)
        os.close(fh)
        yield dict(state=transfer_job.states.DONE, path=fn)
    except Exception as e:
        yield dict(state=transfer_job.states.ERROR, info='Error during file transfer: %s' % str(e))
        return
    return


def scp_transfer(transfer_job):
    """Plugin" for handling scp transfers using pexpect"""
    def print_ticks(d):
        pass
    host = transfer_job.params['host']
    user_name = transfer_job.params['user_name']
    password = transfer_job.params['password']
    file_path = transfer_job.params['file_path']
    if pexpect is None:
        return dict(state=transfer_job.states.ERROR, info=PEXPECT_IMPORT_MESSAGE)
    try:
        fh, fn = tempfile.mkstemp()
    except Exception as e:
        return dict(state=transfer_job.states.ERROR, info='Unable to create temporary file for transfer: %s' % str(e))
    try:
        # TODO: add the ability to determine progress of the copy here like we do in the http_transfer above.
        cmd = "scp %s@%s:'%s' '%s'" % (user_name,
                                       host,
                                       file_path.replace(' ', r'\ '),
                                       fn)
        pexpect.run(cmd, events={'.ssword:*': password + '\r\n',
                                 pexpect.TIMEOUT: print_ticks},
                    timeout=10)
        return dict(state=transfer_job.states.DONE, path=fn)
    except Exception as e:
        return dict(state=transfer_job.states.ERROR, info='Error during file transfer: %s' % str(e))


if __name__ == '__main__':
    arg_handler = ArgHandler()
    arg_handler.parse()
    app = GalaxyApp(arg_handler.opts.config)

    log.debug('Initiating transfer...')
    if transfer(app, arg_handler.transfer_job_id):
        log.debug('Finished')
    else:
        log.error('Error in transfer process...')
        sys.exit(1)
    sys.exit(0)
