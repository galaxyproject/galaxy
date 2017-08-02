"""Web application stack operations
"""
from __future__ import absolute_import

import logging
import threading

try:
    import uwsgi
except ImportError:
    uwsgi = None

from six import string_types


log = logging.getLogger(__name__)


class ApplicationStackTransport(object):
    def __init_dispatcher_thread(self):
        self.dispatcher_thread = threading.Thread(name=self.__class__.__name__ + ".dispatcher_thread", target=self._dispatch_messages)
        self.dispatcher_thread.daemon = True

    def __init__(self, app, dispatcher=None):
        """ Pre-fork initialization.
        """
        self.app = app
        self.can_run = False
        self.running = False
        self.dispatcher = dispatcher
        self.dispatcher_thread = None
        self.__init_dispatcher_thread()

    def _dispatch_messages(self):
        pass

    def start_if_needed(self):
        # Don't unnecessarily start a thread that we don't need.
        log.debug('######## start_if_needed called')
        log.debug('######## %s' % self.can_run)
        log.debug('######## %s' % self.running)
        log.debug('######## %s' % self.dispatcher_thread.is_alive())
        log.debug('######## %s' % self.dispatcher)
        log.debug('######## %s' % self.dispatcher.handler_count)
        import traceback
        traceback.print_stack()
        # FIXME: can_run is False here in the mule, but start() was called way back when the app was loaded and it was True then, what's going on here?
        if self.can_run and not self.running and not self.dispatcher_thread.is_alive() and self.dispatcher and self.dispatcher.handler_count:
            self.running = True
            self.dispatcher_thread.start()
            log.debug('######## Web stack IPC message dispatcher thread started')

    def stop_if_unneeded(self):
        if self.can_run and self.running and self.dispatcher_thread.is_alive() and self.dispatcher and not self.dispatcher.handler_count:
            self.running = False
            self.dispatcher_thread.join()
            self.__init_dispatcher_thread()

    def start(self):
        """ Post-fork initialization.
        """
        self.can_run = True
        log.debug('######## start called')
        self.start_if_needed()

    def send_message(self, msg, dest):
        pass

    def shutdown(self):
        self.running = False
        self.dispatcher_thread.join()


class UWSGIFarmMessageTransport(ApplicationStackTransport):
    shutdown_msg = '__SHUTDOWN__'
    # Define any static lock names here, additional locks will be appended for each configured farm's message handler
    _locks = []

    def __initialize_locks(self):
        num = int(uwsgi.opt.get('locks', 0)) + 1
        farms = self._farms.keys()
        need = len(farms)
        #need = len(filter(lambda x: x.startswith('LOCK_'), dir(self)))
        if num < need:
            raise RuntimeError('Need %i uWSGI locks but only %i exist(s): Set `locks = %i` in uWSGI configuration' % (need, num, need - 1))
            sys.exit(1)
        self._locks.extend(map(lambda x: 'RECV_MSG_FARM_' + x, farms))
        # This would be nice, but in my 2.0.15 uWSGI, the uwsgi module has no set_option function. And I don't know if it'd work.
        #if len(self.lock_map) > 1:
        #    uwsgi.set_option('locks', len(self.lock_map))
        #    log.debug('Created %s uWSGI locks' % len(self.lock_map))

    def __init__(self, app, dispatcher=None):
        super(UWSGIFarmMessageTransport, self).__init__(app, dispatcher=dispatcher)
        self._farms_dict = None
        self._mules_list = None
        self.__initialize_locks()

    @property
    def _farms(self):
        if self._farms_dict is None:
            self._farms_dict = {}
            farms = uwsgi.opt.get('farm', [])
            farms = [farms] if isinstance(farms, string_types) else farms
            for farm in farms:
                name, mules = farm.split(':', 1)
                self._farms_dict[name] = [int(m) for m in mules.split(',')]
        return self._farms_dict

    @property
    def _mules(self):
        if self._mules_list is None:
            self._mules_list = []
            mules = uwsgi.opt.get('mule', [])
            self._mules_list = [mules] if isinstance(mules, string_types) else mules
        return self._mules_list

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
        return self._locks.index('RECV_MSG_FARM_' + self._farm_name)

    def _dispatch_messages(self):
        # We are going to do this a lot, so cache the lock number
        lock = self._farm_recv_msg_lock_num()
        while self.running:
            msg = None
            self.__lock(lock)
            try:
                log.debug('######## Mule %s acquired message receive lock, waiting for new message', uwsgi.mule_id())
                msg = uwsgi.farm_get_msg()
                if msg == self.shutdown_msg:
                    # all you need to do is pass here, self.running should already be set False by the signal handler calling the shutdown method defined in the superclass
                    log.debug('######## SHUTTING DOWN %s', uwsgi.mule_id())
                log.debug('######## Mule %s received message: %s', uwsgi.mule_id(), msg)
            except:
                log.exception( "Exception in mule message handling" )
            finally:
                self.__unlock(lock)
            if msg:
                self.dispatcher.dispatch(msg)
        log.info('######## Mule %s message handler shutting down', uwsgi.mule_id())

    def start(self):
        """ Post-fork initialization.
        """
        if uwsgi.mule_id() == 0:
            # this is the main process
            return
        if not uwsgi.in_farm():
            raise RuntimeError('Mule %s is not in a farm! Set `farm = %s:%s` in uWSGI configuration'
                               % (uwsgi.mule_id(),
                                  self.app.config.job_handler_pool_name,
                                  ','.join(map(str, range(1, len(filter(lambda x: x.endswith('galaxy/main.py'), self._mules)) + 1)))))
        super(UWSGIFarmMessageTransport, self).start()
        log.info('######## Mule started, mule id: %s, farm name: %s, server name: %s', uwsgi.mule_id(), self._farm_name, self.app.config.server_name)

    @property
    def _farm_name(self):
        for name, mules in self._farms.items():
            if uwsgi.mule_id() in mules:
                return name
        return None

    def send_message(self, msg, dest):
        log.debug('######## Sending message to farm %s: %s', dest, msg)
        uwsgi.farm_msg(dest, msg)
        log.debug('######## Message sent')
