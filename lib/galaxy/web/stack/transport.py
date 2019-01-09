"""Web application stack operations
"""
from __future__ import absolute_import

import logging
import threading

from galaxy.util import unicodify

try:
    import uwsgi
except ImportError:
    uwsgi = None


log = logging.getLogger(__name__)


class ApplicationStackTransport(object):
    SHUTDOWN_MSG = '__SHUTDOWN__'

    def __init__(self, app, stack, dispatcher=None):
        """ Pre-fork initialization.
        """
        self.app = app
        self.stack = stack
        self.can_run = False
        self.running = False
        self.dispatcher = dispatcher
        self.dispatcher_thread = None

    def init_late_prefork(self):
        pass

    def _dispatch_messages(self):
        pass

    def start_if_needed(self):
        # Don't unnecessarily start a thread that we don't need.
        if self.can_run and not self.running and not self.dispatcher_thread and self.dispatcher and self.dispatcher.handler_count:
            self.running = True
            self.dispatcher_thread = threading.Thread(name=self.__class__.__name__ + ".dispatcher_thread", target=self._dispatch_messages)
            self.dispatcher_thread.start()
            log.info('%s dispatcher started', self.__class__.__name__)

    def stop_if_unneeded(self):
        if self.can_run and self.running and self.dispatcher_thread and self.dispatcher and not self.dispatcher.handler_count:
            self.running = False
            self.dispatcher_thread.join()
            self.dispatcher_thread = None
            log.info('%s dispatcher stopped', self.__class__.__name__)

    def start(self):
        """ Post-fork initialization.
        """
        self.can_run = True
        self.start_if_needed()

    def send_message(self, msg, dest):
        pass

    def shutdown(self):
        self.running = False
        if self.dispatcher_thread:
            log.info('Joining application stack transport dispatcher thread')
            self.dispatcher_thread.join()
            self.dispatcher_thread = None


class UWSGIFarmMessageTransport(ApplicationStackTransport):
    """ Communication via uWSGI Mule Farm messages. Communication is unidirectional (workers -> mules).
    """
    # Define any static lock names here, additional locks will be appended for each configured farm's message handler
    _locks = []

    def init_late_prefork(self):
        num = int(uwsgi.opt.get('locks', 0)) + 1
        need = len(self.stack._lock_farms)
        if num < need:
            raise RuntimeError('Need %i uWSGI locks but only %i exist(s): Set `locks = %i` in uWSGI configuration' % (need, num, need - 1))
        self._locks.extend(['RECV_MSG_FARM_' + x for x in sorted(self.stack._lock_farms)])
        # this would be nice, but in my 2.0.15 uWSGI, the uwsgi module has no set_option function, and I don't know if it'd work even if the function existed as documented
        # if len(self.lock_map) > 1:
        #     uwsgi.set_option('locks', len(self.lock_map))
        #     log.debug('Created %s uWSGI locks' % len(self.lock_map))

    def __init__(self, app, stack, dispatcher=None):
        super(UWSGIFarmMessageTransport, self).__init__(app, stack, dispatcher=dispatcher)

    def __lock(self, name_or_id):
        try:
            uwsgi.lock(name_or_id)
        except TypeError:
            uwsgi.lock(self._locks.index(name_or_id))

    def __unlock(self, name_or_id):
        try:
            uwsgi.unlock(name_or_id)
        except TypeError:
            uwsgi.unlock(self._locks.index(name_or_id))

    def _farm_recv_msg_lock_num(self):
        return self._locks.index('RECV_MSG_FARM_' + self.stack._farm_name)

    def _dispatch_messages(self):
        # this could be moved to the base class if locking was abstracted and a get_message method was added
        log.info('Application stack message dispatcher thread starting up')
        # we are going to do this a lot, so cache the lock number
        lock = self._farm_recv_msg_lock_num()
        while self.running:
            msg = None
            self.__lock(lock)
            try:
                log.debug('Acquired message lock, waiting for new message')
                msg = unicodify(uwsgi.farm_get_msg())
                log.debug('Received message: %s', msg)
                if msg == self.SHUTDOWN_MSG:
                    self.running = False
                else:
                    self.dispatcher.dispatch(msg)
            except Exception:
                log.exception('Exception in mule message handling')
            finally:
                self.__unlock(lock)
                log.debug('Released lock')
        log.info('Application stack message dispatcher thread exiting')

    # TODO: start_if_needed would be called on a web worker by the stack's register_message_handler function if a
    # function were registered in a web handler, that should probably be prevented.

    def start(self):
        """ Post-fork initialization.

        This is mainly done here for the future possibility that we'll be able to run mules post-fork without exec()ing. In a programmed mule it could be done at __init__ time.
        """
        if self.stack._is_mule:
            if not uwsgi.in_farm():
                raise RuntimeError('Mule %s is not in a farm! Set `farm = <pool_name>:%s` in uWSGI configuration'
                                   % (uwsgi.mule_id(),
                                      ','.join(map(str, range(1, len([x for x in self.stack._configured_mules if x.endswith('galaxy/main.py')]) + 1)))))
            elif len(self.stack._farms) > 1:
                raise RuntimeError('Mule %s is in multiple farms! This configuration is not supported due to locking issues' % uwsgi.mule_id())
            # only mules receive messages so don't bother starting the dispatcher if we're not a mule (although
            # currently it doesn't have any registered handlers and so wouldn't start anyway)
            super(UWSGIFarmMessageTransport, self).start()

    def shutdown(self):
        if self.stack._is_mule:
            super(UWSGIFarmMessageTransport, self).shutdown()

    def send_message(self, msg, dest):
        log.debug('Sending message to farm %s: %s', dest, msg)
        uwsgi.farm_msg(dest, msg)
